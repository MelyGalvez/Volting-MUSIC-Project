# =================================================
# MIDI OUT TESTS
#
# Wire encoding of every channel message the engine
# emits, plus the panic sequence — verified against
# a fake byte-level port.
# =================================================

from midiout import MidiOut


class FakePort:
    name = "fake"

    def __init__(self):
        self.sent = []
        self.resets = 0
        self.closed = False

    def send(self, status, data1=0, data2=0):
        self.sent.append((status, data1, data2))

    def reset(self):
        self.resets += 1

    def close(self):
        self.closed = True


def make():
    port = FakePort()
    return MidiOut(port), port


def test_note_messages():
    midi, port = make()

    midi.note_on(2, 60, 100)
    midi.note_off(2, 60)

    assert port.sent == [
        (0x92, 60, 100),
        (0x82, 60, 0),
    ]


def test_control_and_program():
    midi, port = make()

    midi.control(0, 64, 127)
    midi.program(9, 25)

    assert port.sent == [
        (0xB0, 64, 127),
        (0xC9, 25, 0),
    ]


def test_pitchwheel_encoding():
    midi, port = make()

    midi.pitchwheel(0, 8192)          # center
    midi.pitchwheel(1, 0)             # full down
    midi.pitchwheel(2, 16383)         # full up
    midi.pitchwheel(3, 99999)         # clamped

    assert port.sent == [
        (0xE0, 0x00, 0x40),
        (0xE1, 0x00, 0x00),
        (0xE2, 0x7F, 0x7F),
        (0xE3, 0x7F, 0x7F),
    ]


def test_touch_messages():
    midi, port = make()

    midi.aftertouch(4, 88)
    midi.polytouch(5, 60, 77)

    assert port.sent == [
        (0xD4, 88, 0),
        (0xA5, 60, 77),
    ]


def test_panic_covers_all_channels_and_resets():
    midi, port = make()

    midi.panic()

    assert len(port.sent) == 32           # 2 CCs x 16 channels
    assert port.resets == 1

    statuses = {m[0] for m in port.sent}
    assert statuses == {0xB0 | ch for ch in range(16)}

    controllers = {m[1] for m in port.sent}
    assert controllers == {120, 123}      # sound off + notes off


def test_close_panics_then_closes():
    midi, port = make()

    midi.close()

    assert port.closed
    assert port.resets >= 1
