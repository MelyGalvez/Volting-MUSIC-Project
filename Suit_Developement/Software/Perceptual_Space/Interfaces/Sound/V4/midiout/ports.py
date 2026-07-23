# =================================================
# MIDI PORTS
#
# Byte-level output backends behind one tiny
# interface (send / reset / close / name), selected
# at runtime:
#
#   WinMMPort  - Windows Multimedia (winmm.dll) via
#                ctypes. Zero dependencies, sub-ms
#                writes, present on every Windows
#                install (Microsoft GS Wavetable
#                Synth is always available).
#   PygamePort - pygame.midi, used on non-Windows
#                platforms or when forced in config.
#
# Only this module knows transport details; the rest
# of the application speaks (status, data1, data2).
# =================================================

import sys


class MidiPortError(RuntimeError):
    """
    Raised when no usable MIDI output can be opened.
    Carries a human-readable device listing so the fix
    (plug device / change config.MIDI_DEVICE) is obvious.
    """


# --------------------- WinMM ----------------------


class WinMMPort:
    """
    Windows Multimedia MIDI output. midiOutShortMsg is a
    direct kernel-mixer call measured in microseconds —
    the lowest-latency path available without drivers.
    """

    MIDI_MAPPER = 0xFFFFFFFF     # "system default device"

    def __init__(self, device_id=None):
        import ctypes
        import ctypes.wintypes as wintypes

        self._winmm = ctypes.windll.winmm
        self._handle = wintypes.HANDLE()

        if device_id is None:
            device_id = self.MIDI_MAPPER

        result = self._winmm.midiOutOpen(
            ctypes.byref(self._handle),
            ctypes.c_uint(device_id & 0xFFFFFFFF),
            0, 0, 0,
        )

        if result != 0:     # MMSYSERR_NOERROR
            raise MidiPortError(
                f"midiOutOpen failed (error {result}) for "
                f"device {device_id}.\nAvailable devices:\n"
                + describe_devices()
            )

        if device_id == self.MIDI_MAPPER:
            self.name = "Windows default (MIDI mapper)"
        else:
            names = dict(WinMMPort.devices())
            self.name = names.get(device_id, f"device {device_id}")

    @staticmethod
    def devices():
        """[(device_id, name), ...] of all outputs."""
        import ctypes

        class MIDIOUTCAPSW(ctypes.Structure):
            _fields_ = [
                ("wMid", ctypes.c_ushort),
                ("wPid", ctypes.c_ushort),
                ("vDriverVersion", ctypes.c_uint),
                ("szPname", ctypes.c_wchar * 32),
                ("wTechnology", ctypes.c_ushort),
                ("wVoices", ctypes.c_ushort),
                ("wNotes", ctypes.c_ushort),
                ("wChannelMask", ctypes.c_ushort),
                ("dwSupport", ctypes.c_uint),
            ]

        winmm = ctypes.windll.winmm
        found = []

        for device_id in range(winmm.midiOutGetNumDevs()):
            caps = MIDIOUTCAPSW()
            if winmm.midiOutGetDevCapsW(
                device_id, ctypes.byref(caps),
                ctypes.sizeof(caps),
            ) == 0:
                found.append((device_id, caps.szPname))

        return found

    def send(self, status, data1=0, data2=0):
        self._winmm.midiOutShortMsg(
            self._handle,
            (status & 0xFF) | ((data1 & 0x7F) << 8)
            | ((data2 & 0x7F) << 16),
        )

    def reset(self):
        # midiOutReset turns off every sounding note at the
        # driver level — the hardest panic available.
        self._winmm.midiOutReset(self._handle)

    def close(self):
        try:
            self._winmm.midiOutReset(self._handle)
        finally:
            self._winmm.midiOutClose(self._handle)


# --------------------- pygame ----------------------


class PygamePort:
    """
    pygame.midi output for non-Windows platforms. Imported
    lazily so pygame is only required where it is used.
    """

    def __init__(self, device_id=None):
        try:
            import pygame.midi
        except ImportError as exc:
            raise MidiPortError(
                "pygame is not installed (required for MIDI "
                "output on this platform): pip install pygame"
            ) from exc

        pygame.midi.init()
        self._midi = pygame.midi

        if device_id is None:
            device_id = pygame.midi.get_default_output_id()

        if device_id < 0:
            raise MidiPortError(
                "No MIDI output device found.\nAvailable "
                "devices:\n" + describe_devices()
            )

        info = pygame.midi.get_device_info(device_id)
        if info is None or not info[3]:
            raise MidiPortError(
                f"MIDI device {device_id} is not an output.\n"
                "Available devices:\n" + describe_devices()
            )

        self._out = pygame.midi.Output(device_id)
        self.name = info[1].decode(errors="replace")

    @staticmethod
    def devices():
        try:
            import pygame.midi
        except ImportError:
            return []

        pygame.midi.init()
        found = []

        for device_id in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(device_id)
            if info and info[3]:
                found.append(
                    (device_id, info[1].decode(errors="replace"))
                )

        return found

    def send(self, status, data1=0, data2=0):
        self._out.write_short(status, data1, data2)

    def reset(self):
        pass                     # no driver-level reset in pygame

    def close(self):
        try:
            self._out.close()
        finally:
            self._midi.quit()


# ------------------- Selection ---------------------


def _backend_class(backend):
    if backend == "winmm":
        return WinMMPort
    if backend == "pygame":
        return PygamePort
    if backend == "auto":
        return WinMMPort if sys.platform == "win32" else PygamePort

    raise MidiPortError(f"Unknown MIDI backend: {backend!r}")


def list_backends(backend="auto"):
    """[(device_id, name), ...] for the selected backend."""
    return _backend_class(backend).devices()


def describe_devices(backend="auto"):
    devices = list_backends(backend)
    if not devices:
        return "  (none)"
    return "\n".join(f"  [{i}] {name}" for i, name in devices)


def open_port(backend="auto", device=None):
    """
    Open a MIDI output port.

    device: None (system default), an int device id, or a
    string matched case-insensitively against device names
    (first match wins) — e.g. "loopMIDI" to reach a DAW.
    """

    cls = _backend_class(backend)

    if isinstance(device, str):
        wanted = device.lower()
        for device_id, name in cls.devices():
            if wanted in name.lower():
                return cls(device_id)

        raise MidiPortError(
            f"No MIDI output matches {device!r}.\n"
            "Available devices:\n" + describe_devices(backend)
        )

    return cls(device)
