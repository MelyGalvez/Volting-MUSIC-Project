# =================================================
# LOADER TESTS
#
# MIDI file -> Score preloading: chord grouping,
# polyphony, tempo integration, control attachment,
# labels and malformed-file rejection.
# All files are generated in tmp_path via mido.
# =================================================

import mido
import pytest

from score import ScoreError, load_score
from tests.helpers import off, on, write_midi


# Default tempo (120 BPM) at 480 tpb: 480 ticks = 0.5 s.


def load(path, **kw):
    kw.setdefault("chord_window_s", 0.030)
    return load_score(path, **kw)


# ------------------- Steps & chords -------------------


def test_single_notes_become_steps(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0), off(60, 480),
        on(62, 480), off(62, 960),
        on(64, 960), off(64, 1440),
    ]])

    score = load(path)

    assert score.total_steps == 3
    assert [s.tick for s in score.steps] == [0, 480, 960]
    assert [s.notes[0].key for s in score.steps] == [60, 62, 64]
    assert score.steps[1].time_s == pytest.approx(0.5)
    assert score.note_count == 3


def test_exact_chord_is_one_step(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(67, 0), on(60, 0), on(64, 0),
        off(60, 480), off(64, 480), off(67, 480),
    ]])

    score = load(path)

    assert score.total_steps == 1
    assert [n.key for n in score.steps[0].notes] == [60, 64, 67]


def test_humanized_chord_grouped_by_window(tmp_path):
    # 0, ~10 ms, ~25 ms: one step; ~100 ms: the next.
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0), on(64, 10), on(67, 24),
        on(72, 96),
        off(60, 480), off(64, 480), off(67, 480), off(72, 480),
    ]])

    score = load(path)

    assert score.total_steps == 2
    assert len(score.steps[0].notes) == 3
    assert score.steps[1].notes[0].key == 72


def test_window_anchored_not_chained(tmp_path):
    # Onsets every 25 ms: each within 30 ms of the previous
    # but not of the group anchor -> must NOT merge into one
    # endless step.
    events = []
    for i in range(4):
        events.append(on(60 + i, i * 24))
        events.append(off(60 + i, 480 + i * 24))

    score = load(write_midi(tmp_path / "a.mid", [events]))

    assert score.total_steps > 1


# ---------------- Note pairing rules -----------------


def test_polyphony_overlap_preserved(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(48, 0), off(48, 1920),              # whole note
        on(60, 0), off(60, 480),
        on(62, 480), off(62, 960),
        on(64, 960), off(64, 1440),
        on(65, 1440), off(65, 1920),
    ]])

    score = load(path)

    assert score.total_steps == 4
    whole = [n for n in score.steps[0].notes if n.key == 48][0]
    assert whole.end_tick == 1920
    assert whole.end_s == pytest.approx(2.0)


def test_note_on_velocity_zero_is_note_off(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0),
        on(60, 480, velocity=0),
    ]])

    score = load(path)

    assert score.note_count == 1
    assert score.steps[0].notes[0].end_tick == 480


def test_dangling_note_closed_at_file_end(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0),                     # no off
        on(62, 960), off(62, 1440),
    ]])

    score = load(path)

    dangling = score.steps[0].notes[0]
    assert dangling.end_tick == 1440


def test_retrigger_closes_previous_note(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0),
        on(60, 480),                   # retrigger before off
        off(60, 960),
    ]])

    score = load(path)

    assert score.note_count == 2
    first, second = sorted(
        (n for s in score.steps for n in s.notes),
        key=lambda n: n.start_tick,
    )
    assert (first.start_tick, first.end_tick) == (0, 480)
    assert (second.start_tick, second.end_tick) == (480, 960)


def test_zero_length_note_gets_min_duration(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0), off(60, 0),
    ]])

    score = load(path)

    note = score.steps[0].notes[0]
    assert note.end_tick == 1
    assert note.end_s > note.start_s


def test_unmatched_note_off_ignored(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        off(72, 0),
        on(60, 480), off(60, 960),
    ]])

    score = load(path)
    assert score.note_count == 1


# -------------------- Tempo map ----------------------


def test_tempo_change_reflected_in_seconds(tmp_path):
    meta = [
        (0, mido.MetaMessage("set_tempo", tempo=500_000)),
        (480, mido.MetaMessage("set_tempo", tempo=1_000_000)),
    ]
    notes = [
        on(60, 0), off(60, 480),
        on(62, 960), off(62, 1440),
    ]

    score = load(write_midi(tmp_path / "a.mid", [meta, notes]))

    # 480 ticks at 120 BPM (0.5 s) + 480 ticks at 60 BPM (1 s).
    assert score.steps[1].time_s == pytest.approx(1.5)
    assert len(score.tempo_map) == 2


# ------------------ Controls & labels -----------------


def test_setup_step_and_tail_controls(tmp_path):
    events = [
        (0, mido.Message("program_change", program=5, channel=0)),
        on(60, 0), off(60, 480),
        (600, mido.Message(
            "control_change", control=64, value=127, channel=0)),
        on(62, 960), off(62, 1440),
        (2000, mido.Message(
            "control_change", control=64, value=0, channel=0)),
    ]

    score = load(write_midi(tmp_path / "a.mid", [events]))

    assert [c.kind for c in score.setup] == ["program"]
    assert score.setup[0].data1 == 5

    assert score.steps[0].controls == ()
    assert len(score.steps[1].controls) == 1
    assert score.steps[1].controls[0].data1 == 64
    assert score.steps[1].controls[0].data2 == 127

    assert len(score.tail_controls) == 1
    assert score.tail_controls[0].data2 == 0


def test_pitchwheel_center_encoding(tmp_path):
    events = [
        (0, mido.Message("pitchwheel", pitch=0, channel=0)),
        (0, mido.Message("pitchwheel", pitch=-8192, channel=3)),
        on(60, 0), off(60, 480),
    ]

    score = load(write_midi(tmp_path / "a.mid", [events]))

    wheels = [c for c in score.setup if c.kind == "pitchwheel"]
    assert sorted(w.data1 for w in wheels) == [0, 8192]


def test_markers_become_labels_and_sections(tmp_path):
    meta = [
        (0, mido.MetaMessage("marker", text="Intro")),
        (960, mido.MetaMessage("marker", text="Theme")),
    ]
    notes = []
    for i in range(4):
        notes.append(on(60 + i, i * 480))
        notes.append(off(60 + i, (i + 1) * 480))

    score = load(write_midi(tmp_path / "a.mid", [meta, notes]))

    assert score.steps[0].label == "Intro"
    assert score.steps[1].label is None
    assert score.steps[1].section == "Intro"
    assert score.steps[2].label == "Theme"
    assert score.steps[3].section == "Theme"


def test_track_name_becomes_score_name(tmp_path):
    meta = [(0, mido.MetaMessage("track_name", name="My Song"))]
    notes = [on(60, 0), off(60, 480)]

    score = load(write_midi(tmp_path / "a.mid", [meta, notes]))

    assert score.name == "My Song"
    assert score.track_names[0] == "My Song"


# --------------------- Filters ------------------------


def test_channel_filter(tmp_path):
    events = [
        on(60, 0), off(60, 480),
        on(36, 0, channel=9), off(36, 480, channel=9),
    ]

    score = load(
        write_midi(tmp_path / "a.mid", [events]),
        channel_filter={0},
    )

    assert score.note_count == 1
    assert score.channels == frozenset({0})


def test_track_filter(tmp_path):
    track_a = [on(60, 0), off(60, 480)]
    track_b = [on(72, 0), off(72, 480)]

    score = load(
        write_midi(tmp_path / "a.mid", [track_a, track_b]),
        track_filter={1},
    )

    assert score.note_count == 1
    assert score.steps[0].notes[0].key == 72


# ------------------- Rejections -----------------------


def test_not_a_midi_file(tmp_path):
    path = tmp_path / "junk.mid"
    path.write_bytes(b"this is not midi at all")

    with pytest.raises(ScoreError, match="MThd"):
        load(str(path))


def test_format2_rejected(tmp_path):
    path = write_midi(
        tmp_path / "f2.mid",
        [[on(60, 0), off(60, 480)]],
        file_type=2,
    )

    with pytest.raises(ScoreError, match="format 2"):
        load(path)


def test_smpte_division_rejected(tmp_path):
    header = (
        b"MThd" + (6).to_bytes(4, "big")
        + (0).to_bytes(2, "big") + (1).to_bytes(2, "big")
        + bytes([0xE7, 0x28])          # SMPTE -25 fps
    )
    track = b"MTrk" + (4).to_bytes(4, "big") + b"\x00\xff\x2f\x00"

    path = tmp_path / "smpte.mid"
    path.write_bytes(header + track)

    with pytest.raises(ScoreError, match="SMPTE"):
        load(str(path))


def test_no_notes_rejected(tmp_path):
    path = write_midi(tmp_path / "empty.mid", [[
        (0, mido.MetaMessage("marker", text="nothing here")),
    ]])

    with pytest.raises(ScoreError, match="no notes"):
        load(path)


def test_filters_removing_all_notes_explained(tmp_path):
    path = write_midi(tmp_path / "a.mid", [[
        on(60, 0), off(60, 480),
    ]])

    with pytest.raises(ScoreError, match="filters"):
        load(path, channel_filter={5})
