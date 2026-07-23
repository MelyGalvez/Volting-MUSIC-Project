# =================================================
# TEST HELPERS
#
# Shared fixtures: a MIDI file builder (absolute
# ticks in, standard file out), a recording fake of
# the MidiOut interface, suit packet builders, and
# hand-built Score factories for engine tests.
# =================================================

import mido

from score.model import ControlEvent, Note, Score, Step


# ---------------- MIDI file builder -----------------


def write_midi(path, tracks, ticks_per_beat=480, file_type=1):
    """
    tracks: list of tracks, each a list of
    (absolute_tick, mido.Message-or-MetaMessage).
    Events are stably sorted per track and converted to
    delta times.
    """

    midi = mido.MidiFile(type=file_type, ticks_per_beat=ticks_per_beat)

    for events in tracks:
        track = mido.MidiTrack()
        previous = 0

        for tick, message in sorted(
            events, key=lambda e: e[0]
        ):
            message = message.copy(time=tick - previous)
            previous = tick
            track.append(message)

        midi.tracks.append(track)

    midi.save(str(path))
    return str(path)


def on(note, tick, velocity=64, channel=0):
    return (tick, mido.Message(
        "note_on", note=note, velocity=velocity, channel=channel
    ))


def off(note, tick, channel=0):
    return (tick, mido.Message(
        "note_off", note=note, velocity=0, channel=channel
    ))


# ---------------- Recording MIDI out ----------------


class FakeMidi:
    """
    Records every call the engine makes, in order, as
    plain tuples — the complete observable output of the
    navigation engine.
    """

    def __init__(self):
        self.sent = []

    def note_on(self, channel, key, velocity):
        self.sent.append(("on", channel, key, velocity))

    def note_off(self, channel, key):
        self.sent.append(("off", channel, key))

    def control(self, channel, controller, value):
        self.sent.append(("control", channel, controller, value))

    def program(self, channel, program):
        self.sent.append(("program", channel, program))

    def pitchwheel(self, channel, value14):
        self.sent.append(("pitchwheel", channel, value14))

    def aftertouch(self, channel, pressure):
        self.sent.append(("aftertouch", channel, pressure))

    def polytouch(self, channel, key, pressure):
        self.sent.append(("polytouch", channel, key, pressure))

    def panic(self):
        self.sent.append(("panic",))

    # -- assertions ----------------------------------

    def of_kind(self, kind):
        return [m for m in self.sent if m[0] == kind]

    def balanced(self):
        """Every note-on has a matching later note-off."""
        open_slots = set()

        for message in self.sent:
            if message[0] == "on":
                slot = (message[1], message[2])
                if slot in open_slots:
                    return False       # double-on without off
                open_slots.add(slot)
            elif message[0] == "off":
                open_slots.discard((message[1], message[2]))

        return not open_slots


# ----------------- Score factories ------------------


def make_note(key, start_tick, end_tick, *, velocity=64,
              channel=0, track=0, tick_s=0.001):
    """A Note whose seconds mirror its ticks (tick_s each)."""
    return Note(
        key=key, velocity=velocity, channel=channel,
        track=track,
        start_tick=start_tick, end_tick=end_tick,
        start_s=start_tick * tick_s, end_s=end_tick * tick_s,
    )


def make_score(step_notes, *, setup=(), tail=(),
               step_controls=None, tick_s=0.001):
    """
    step_notes: list of lists of Notes; each inner list is
    one step (its tick = min start_tick of its notes).
    """

    steps = []

    for index, notes in enumerate(step_notes):
        tick = min(n.start_tick for n in notes)
        controls = tuple(
            step_controls.get(index, ())
        ) if step_controls else ()

        steps.append(Step(
            index=index,
            tick=tick,
            time_s=tick * tick_s,
            notes=tuple(notes),
            controls=controls,
        ))

    channels = frozenset(
        n.channel for step in steps for n in step.notes
    )

    return Score(
        name="test",
        source_path="<memory>",
        ticks_per_beat=480,
        steps=tuple(steps),
        setup=tuple(setup),
        tail_controls=tuple(tail),
        duration_s=max(
            n.end_s for s in steps for n in s.notes
        ),
        channels=channels,
    )


def control(kind, channel, data1, data2=0, tick=0):
    return ControlEvent(
        kind=kind, channel=channel, data1=data1, data2=data2,
        tick=tick, time_s=tick * 0.001,
    )


# ----------------- Suit packet builder ----------------


def packet(ts, *, seq=None, system="ready", imus=None,
           piezo=None):
    """
    imus: dict body -> dict of fields (ok defaults True).
    piezo: dict side -> dict(hits=, hit_peak=).
    """

    imu_data = []
    for body, fields in (imus or {}).items():
        imu = {"body": body, "ok": True, "cal": True}
        imu.update(fields)
        imu_data.append(imu)

    data = {
        "v": 2,
        "seq": seq if seq is not None else ts,
        "timestamp": ts,
        "system": system,
        "imu_data": imu_data,
    }

    if piezo is not None:
        data["piezo"] = piezo

    return data
