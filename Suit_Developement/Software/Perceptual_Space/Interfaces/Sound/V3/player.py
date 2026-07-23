# =================================================
# PLAYER
#
# MIDI output engine. A class with explicit
# initialization: importing this module has no side
# effects (the previous version opened the MIDI
# device and bound UI callbacks at import time).
# =================================================

import time

import pygame.midi

import config


CC_ALL_NOTES_OFF = 123


class MidiUnavailableError(RuntimeError):
    """
    Raised when no usable MIDI output device exists.
    Carries a human-readable device listing.
    """


def _list_devices():
    lines = []

    for device_id in range(pygame.midi.get_count()):
        info = pygame.midi.get_device_info(device_id)
        _, name, is_input, is_output, _ = info

        kind = "output" if is_output else \
               "input" if is_input else "?"

        lines.append(
            f"  [{device_id}] {name.decode(errors='replace')}"
            f" ({kind})"
        )

    return "\n".join(lines) if lines else "  (none)"


class MidiEngine:
    """
    Owns the pygame.midi output and all channel state:
    active notes, CC dedup/deadband and pending drum
    note-offs (scheduled, never slept on: the previous
    time.sleep(0.02) per drum hit stalled the whole
    control loop).
    """

    def __init__(self, device_id=config.MIDI_DEVICE_ID):
        pygame.midi.init()

        if device_id is None:
            device_id = pygame.midi.get_default_output_id()

        if device_id < 0:
            raise MidiUnavailableError(
                "No MIDI output device found.\n"
                "Available devices:\n" + _list_devices()
            )

        info = pygame.midi.get_device_info(device_id)

        if info is None or not info[3]:
            raise MidiUnavailableError(
                f"MIDI device {device_id} is not an output.\n"
                "Available devices:\n" + _list_devices()
            )

        self._out = pygame.midi.Output(device_id)

        print(
            f"MIDI output: [{device_id}] "
            f"{info[1].decode(errors='replace')}"
        )

        # Per-channel state.
        self._active_note = {}      # channel -> midi note
        self._cc_values = {}        # (channel, cc) -> value
        self._pending_offs = []     # (due_monotonic, note, ch)


# --------------------- Notes ----------------------


    def play_note(self, channel, note,
                  velocity=config.NOTE_VELOCITY):
        """
        Make `note` the sounding note of this channel.
        No-op when the note is unchanged.
        """

        current = self._active_note.get(channel)

        if note == current:
            return

        if current is not None:
            self._out.note_off(current, 0, channel)

        self._out.note_on(note, velocity, channel)
        self._active_note[channel] = note

    def stop_note(self, channel):
        current = self._active_note.pop(channel, None)

        if current is not None:
            self._out.note_off(current, 0, channel)


# ------------------ Instruments -------------------


    def set_instrument(self, channel, program):
        """
        Program change. The active note is stopped first so
        no note keeps ringing with an ambiguous timbre.
        """

        self.stop_note(channel)
        self._out.set_instrument(program, channel)


# ----------------- Control change ------------------


    def set_cc(self, channel, cc, value):
        """
        Send a CC with deduplication and a small deadband:
        quantization jitter of +-1 step at rest is not
        transmitted, endpoints always are.

        Returns the value actually in effect.
        """

        value = max(0, min(127, int(value)))
        key = (channel, cc)
        current = self._cc_values.get(key)

        if current is not None:
            if value == current:
                return current

            small = abs(value - current) < config.CC_MIN_DELTA
            at_edge = value in (0, 127)

            if small and not at_edge:
                return current

        self._cc_values[key] = value
        self._out.write_short(0xB0 + channel, cc, value)

        return value

    def get_cc(self, channel, cc):
        return self._cc_values.get((channel, cc), -1)


# --------------------- Drums -----------------------


    def play_drum(self, note, velocity):
        """
        Trigger a percussion note; its note-off is scheduled
        and sent later by process(), never slept on.
        """

        self._out.note_on(note, velocity, config.DRUM_CHANNEL)

        self._pending_offs.append(
            (time.monotonic() + config.DRUM_GATE_S, note)
        )

    def process(self):
        """
        Send due drum note-offs. Call once per tick.
        """

        if not self._pending_offs:
            return

        now = time.monotonic()
        remaining = []

        for due, note in self._pending_offs:
            if now >= due:
                self._out.note_off(note, 0, config.DRUM_CHANNEL)
            else:
                remaining.append((due, note))

        self._pending_offs = remaining


# --------------------- Safety ----------------------


    def silence(self):
        """
        Stop every sounding voice (melodic notes, pending
        drum offs, CC All Notes Off on all used channels).
        """

        for channel in list(self._active_note.keys()):
            self.stop_note(channel)

        for _, note in self._pending_offs:
            self._out.note_off(note, 0, config.DRUM_CHANNEL)

        self._pending_offs.clear()

        for channel in (
            config.LEFT_CHANNEL,
            config.RIGHT_CHANNEL,
            config.DRUM_CHANNEL,
        ):
            self._out.write_short(
                0xB0 + channel, CC_ALL_NOTES_OFF, 0
            )


# --------------------- Cleanup ---------------------


    def close(self):
        try:
            self.silence()
        except Exception:
            pass

        try:
            self._out.close()
        except Exception:
            pass

        pygame.midi.quit()
