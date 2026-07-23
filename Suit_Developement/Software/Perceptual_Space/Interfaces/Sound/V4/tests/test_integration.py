# =================================================
# INTEGRATION TESTS
#
# Full pipeline: a realistic multi-track MIDI file
# (chords, spread chord, cross-step polyphony,
# program changes, pedal, pitch bend, tempo change,
# markers) -> loader -> navigation engine -> fake
# MIDI port. Verifies that playing an entire piece
# leaves the MIDI state perfectly balanced in both
# release modes, and that gestures drive it through
# the real router.
# =================================================

import mido

from engine import (
    GestureEvent,
    NavigationEngine,
    SustainRelease,
    TimedRelease,
)
from engine.velocity import FileVelocity
from inputs import GestureRouter, PiezoHitDetector
from score import load_score
from tests.helpers import FakeMidi, off, on, packet, write_midi


def make_piece(tmp_path):
    meta = [
        (0, mido.MetaMessage("track_name", name="Piece")),
        (0, mido.MetaMessage("set_tempo", tempo=500_000)),
        (0, mido.MetaMessage("marker", text="A")),
        (1920, mido.MetaMessage("set_tempo", tempo=666_667)),
        (1920, mido.MetaMessage("marker", text="B")),
    ]

    piano = [
        (0, mido.Message("program_change", program=0, channel=0)),
        # Chord.
        on(60, 0, velocity=90), on(64, 0, velocity=90),
        off(60, 480), off(64, 480),
        # Spread chord (one step through the 30 ms window).
        on(62, 480, velocity=85), on(65, 489, velocity=85),
        off(62, 960), off(65, 960),
        # Pedal under two staccato notes.
        (960, mido.Message(
            "control_change", control=64, value=127, channel=0)),
        on(72, 960, velocity=100), off(72, 1080),
        on(74, 1440, velocity=100), off(74, 1560),
        (1900, mido.Message(
            "control_change", control=64, value=0, channel=0)),
        # After the tempo change: bend swell on a long note.
        (1920, mido.Message("pitchwheel", pitch=0, channel=0)),
        on(76, 1920, velocity=95), off(76, 3840),
        (2400, mido.Message("pitchwheel", pitch=2000, channel=0)),
        # Trailing controls after the last onset -> tail.
        (3900, mido.Message("pitchwheel", pitch=0, channel=0)),
    ]

    pad = [
        (0, mido.Message("program_change", program=48, channel=1)),
        on(36, 0, velocity=60, channel=1),
        off(36, 1920, channel=1),               # spans 4 steps
        on(43, 1920, velocity=60, channel=1),
        off(43, 3840, channel=1),
    ]

    return write_midi(tmp_path / "piece.mid", [meta, piano, pad])


def play_through(engine, score, *, spacing=0.2, process=None):
    mono = 100.0

    for _ in range(score.total_steps + 1):   # + cutoff gesture
        assert engine.advance(GestureEvent("test", 0.7, mono))
        if process is not None:
            process(mono + spacing * 0.99)
        mono += spacing

    return mono


def test_sustain_full_playthrough_balanced(tmp_path):
    score = load_score(make_piece(tmp_path), chord_window_s=0.03)

    # Onset groups: 0 (chord+pad), 480 (spread chord),
    # 960, 1440 (staccato pair), 1920 (long note + pad).
    assert score.name == "Piece"
    assert score.total_steps == 5
    assert score.note_count == 9
    assert score.steps[0].section == "A"
    assert score.steps[4].label == "B"
    assert len(score.tempo_map) == 2
    assert len(score.tail_controls) == 2   # trailing bends

    midi = FakeMidi()
    engine = NavigationEngine(
        midi, SustainRelease(), FileVelocity(),
        refractory_s=0.0,
    )
    engine.load(score)

    # Setup replayed at load: both programs + nothing else
    # sounding yet.
    assert ("program", 0, 0) in midi.sent
    assert ("program", 1, 48) in midi.sent
    assert midi.of_kind("on") == []

    play_through(engine, score)

    view = engine.view()
    assert view.finished
    assert view.sounding == ()
    assert midi.balanced()

    assert len(midi.of_kind("on")) == score.note_count
    assert len(midi.of_kind("off")) == score.note_count

    # Pedal down, pedal up, and every pitch bend all arrived.
    pedal = [m for m in midi.sent if m[0] == "control"
             and m[2] == 64]
    assert [m[3] for m in pedal] == [127, 0]
    assert len(midi.of_kind("pitchwheel")) == 3


def test_timed_full_playthrough_balanced(tmp_path):
    score = load_score(make_piece(tmp_path), chord_window_s=0.03)

    midi = FakeMidi()
    engine = NavigationEngine(
        midi,
        TimedRelease(alpha=0.4, rate_min=0.2, rate_max=5.0,
                     min_gate_s=0.02, max_hold_s=10.0),
        FileVelocity(),
        refractory_s=0.0,
    )
    engine.load(score)

    mono = 100.0
    for index in range(score.total_steps + 1):
        assert engine.advance(GestureEvent("test", 0.7, mono))

        if index == 2:
            # Step 2 is the staccato note 72 (125 ms
            # written). In timed mode it must end from the
            # *schedule*, well before the next gesture.
            engine.process(mono + 0.20)
            assert ("off", 0, 72) in midi.sent
            assert (0, 72) not in engine.view().sounding

        engine.process(mono + 0.29)
        mono += 0.3

    engine.process(mono + 60.0)       # drain any late schedule

    assert engine.view().finished
    assert midi.balanced()
    assert len(midi.of_kind("on")) == score.note_count
    assert len(midi.of_kind("off")) == score.note_count


def test_router_drives_engine(tmp_path):
    score = load_score(make_piece(tmp_path), chord_window_s=0.03)

    midi = FakeMidi()
    engine = NavigationEngine(
        midi, SustainRelease(), FileVelocity(),
        refractory_s=0.0,
    )
    engine.load(score)

    router = GestureRouter(
        [PiezoHitDetector("piezo_left", "left",
                          peak_floor=500, peak_ceil=4095)],
        {"piezo_left": "advance"},
    )

    def strike(ts, hits):
        frame = packet(ts, piezo={
            "left": {"peak": 0, "hits": hits, "hit_peak": 3000},
        })
        for action, event in router.process(frame, ts / 1000.0):
            assert action == "advance"
            engine.advance(event)

    strike(1000, 10)                  # baseline, no advance
    assert engine.view().next_index == 0

    for i in range(score.total_steps + 1):
        strike(2000 + i * 500, 11 + i)

    assert engine.view().finished
    assert midi.balanced()
