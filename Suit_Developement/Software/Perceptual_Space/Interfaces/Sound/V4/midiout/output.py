# =================================================
# MIDI OUT
#
# Musical wrapper over a byte-level port: channel
# messages by name, a lock so any thread can emit
# safely, and a full panic. No musical *state* lives
# here — the navigation engine's ledger is the single
# source of truth for what is sounding.
# =================================================

import threading


# Channel voice message status nibbles.
_NOTE_OFF = 0x80
_NOTE_ON = 0x90
_POLYTOUCH = 0xA0
_CONTROL = 0xB0
_PROGRAM = 0xC0
_AFTERTOUCH = 0xD0
_PITCHWHEEL = 0xE0

CC_ALL_SOUND_OFF = 120
CC_RESET_CONTROLLERS = 121
CC_ALL_NOTES_OFF = 123


class MidiOut:

    def __init__(self, port):
        self._port = port
        self._lock = threading.Lock()

    @property
    def name(self):
        return self._port.name


# ------------------- Messages ---------------------


    def note_on(self, channel, key, velocity):
        with self._lock:
            self._port.send(
                _NOTE_ON | (channel & 0x0F), key, velocity
            )

    def note_off(self, channel, key):
        with self._lock:
            self._port.send(
                _NOTE_OFF | (channel & 0x0F), key, 0
            )

    def control(self, channel, controller, value):
        with self._lock:
            self._port.send(
                _CONTROL | (channel & 0x0F), controller, value
            )

    def program(self, channel, program):
        with self._lock:
            self._port.send(
                _PROGRAM | (channel & 0x0F), program, 0
            )

    def pitchwheel(self, channel, value14):
        """value14: 0..16383, 8192 = center."""
        value14 = max(0, min(16383, int(value14)))
        with self._lock:
            self._port.send(
                _PITCHWHEEL | (channel & 0x0F),
                value14 & 0x7F,
                (value14 >> 7) & 0x7F,
            )

    def aftertouch(self, channel, pressure):
        with self._lock:
            self._port.send(
                _AFTERTOUCH | (channel & 0x0F), pressure, 0
            )

    def polytouch(self, channel, key, pressure):
        with self._lock:
            self._port.send(
                _POLYTOUCH | (channel & 0x0F), key, pressure
            )


# -------------------- Safety -----------------------


    def panic(self):
        """
        All Sound Off + All Notes Off on all 16 channels,
        then the port's own reset. Covers notes a synth
        might hold through sustain pedals or effects tails.
        """

        with self._lock:
            for channel in range(16):
                status = _CONTROL | channel
                self._port.send(status, CC_ALL_SOUND_OFF, 0)
                self._port.send(status, CC_ALL_NOTES_OFF, 0)

            self._port.reset()


# -------------------- Cleanup -----------------------


    def close(self):
        try:
            self.panic()
        except Exception:
            pass

        try:
            self._port.close()
        except Exception:
            pass
