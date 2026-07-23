# =================================================
# NAVIGATION ENGINE TESTS
#
# Cursor semantics, the positional release rule
# (polyphony), retriggering, controls, cutoff/loop,
# refractory, back/jump/restart, suspend/panic and
# the timed-release scheduling with its generation
# guard. All output is observed through FakeMidi.
# =================================================

from engine import (
    GestureEvent,
    NavigationEngine,
    SustainRelease,
    TimedRelease,
)
from engine.velocity import BlendVelocity, FileVelocity
from tests.helpers import (
    FakeMidi,
    control,
    make_note,
    make_score,
)


def gesture(mono, strength=1.0):
    return GestureEvent("test", strength, mono)


def build(score=None, *, mode=None, velocity=None,
          refractory=0.0, loop=False):
    midi = FakeMidi()
    engine = NavigationEngine(
        midi,
        mode or SustainRelease(),
        velocity or FileVelocity(),
        refractory_s=refractory,
        loop_at_end=loop,
    )
    if score is not None:
        engine.load(score)
    return engine, midi


# ------------------- Basic advance --------------------


def test_advance_plays_steps_in_order():
    score = make_score([
        [make_note(60, 0, 480)],
        [make_note(62, 480, 960)],
    ])
    engine, midi = build(score)

    assert engine.advance(gesture(1.0))
    assert engine.advance(gesture(2.0))

    assert midi.sent == [
        ("on", 0, 60, 64),
        ("off", 0, 60),          # positional release at step 1
        ("on", 0, 62, 64),
    ]


def test_advance_without_score_rejected():
    engine, midi = build()
    assert not engine.advance(gesture(1.0))
    assert midi.sent == []


def test_chord_fires_together():
    score = make_score([
        [make_note(60, 0, 480), make_note(64, 0, 480),
         make_note(67, 0, 480)],
    ])
    engine, midi = build(score)
    engine.advance(gesture(1.0))

    assert midi.of_kind("on") == [
        ("on", 0, 60, 64), ("on", 0, 64, 64), ("on", 0, 67, 64),
    ]


# ---------------- Polyphony (overlaps) -----------------


def test_held_note_survives_across_steps():
    score = make_score([
        [make_note(48, 0, 1920), make_note(60, 0, 480)],
        [make_note(62, 480, 960)],
        [make_note(64, 960, 1440)],
        [make_note(65, 1440, 1920)],
    ])
    engine, midi = build(score)

    for t in range(4):
        engine.advance(gesture(float(t)))

    # The whole note must still be sounding after 4 steps.
    assert ("off", 0, 48) not in midi.sent
    assert (0, 48) in engine.view().sounding

    # The cutoff gesture releases it.
    engine.advance(gesture(10.0))
    assert ("off", 0, 48) in midi.sent
    assert midi.balanced()
    assert engine.view().finished


def test_retrigger_same_key_releases_first():
    score = make_score([
        [make_note(60, 0, 960)],
        [make_note(60, 480, 1440)],     # overlaps the first
    ])
    engine, midi = build(score)

    engine.advance(gesture(1.0))
    engine.advance(gesture(2.0))

    assert midi.sent == [
        ("on", 0, 60, 64),
        ("off", 0, 60),
        ("on", 0, 60, 64),
    ]


# ------------------ Controls & velocity ------------------


def test_step_controls_before_notes():
    score = make_score(
        [
            [make_note(60, 0, 480)],
            [make_note(62, 480, 960)],
        ],
        step_controls={1: [control("program", 0, 5, tick=480)]},
    )
    engine, midi = build(score)

    engine.advance(gesture(1.0))
    engine.advance(gesture(2.0))

    assert midi.sent == [
        ("on", 0, 60, 64),
        ("off", 0, 60),
        ("program", 0, 5),
        ("on", 0, 62, 64),
    ]


def test_setup_emitted_at_load():
    score = make_score(
        [[make_note(60, 0, 480)]],
        setup=[control("program", 0, 12),
               control("control", 0, 7, 100)],
    )
    _engine, midi = build(score)

    assert ("program", 0, 12) in midi.sent
    assert ("control", 0, 7, 100) in midi.sent


def test_blend_velocity_scales_with_strength():
    score = make_score([
        [make_note(60, 0, 480, velocity=100)],
        [make_note(62, 480, 960, velocity=100)],
    ])
    engine, midi = build(
        score, velocity=BlendVelocity(floor_scale=0.5)
    )

    engine.advance(gesture(1.0, strength=0.0))
    engine.advance(gesture(2.0, strength=1.0))

    ons = midi.of_kind("on")
    assert ons[0][3] == 50
    assert ons[1][3] == 100


# ------------------- End of score ----------------------


def test_cutoff_releases_and_emits_tail():
    score = make_score(
        [[make_note(60, 0, 9999)]],
        tail=[control("control", 0, 91, 0, tick=9999)],
    )
    engine, midi = build(score)

    engine.advance(gesture(1.0))         # last step
    assert not engine.view().finished

    engine.advance(gesture(2.0))         # cutoff
    assert engine.view().finished
    assert midi.sent[-2:] == [
        ("off", 0, 60), ("control", 0, 91, 0),
    ]

    # Finished + no loop: further gestures are ignored.
    assert not engine.advance(gesture(3.0))


def test_loop_restarts_after_cutoff():
    score = make_score(
        [[make_note(60, 0, 480)]],
        setup=[control("program", 0, 7)],
    )
    engine, midi = build(score, loop=True)

    engine.advance(gesture(1.0))         # play
    engine.advance(gesture(2.0))         # cutoff
    midi.sent.clear()

    assert engine.advance(gesture(3.0))  # loop: step 0 again

    assert ("program", 0, 7) in midi.sent   # setup state replayed
    assert ("on", 0, 60, 64) in midi.sent
    assert not engine.view().finished


# -------------------- Refractory -----------------------


def test_refractory_collapses_double_triggers():
    score = make_score([
        [make_note(60, 0, 480)],
        [make_note(62, 480, 960)],
    ])
    engine, midi = build(score, refractory=0.08)

    assert engine.advance(gesture(10.000))
    assert not engine.advance(gesture(10.010))   # piezo+swing double
    assert engine.advance(gesture(10.100))

    assert len(midi.of_kind("on")) == 2


# ----------------- Back / jump / restart ----------------


def test_back_replays_previous_step():
    score = make_score([
        [make_note(60, 0, 480)],
        [make_note(62, 480, 960)],
    ])
    engine, midi = build(score)

    engine.advance(gesture(1.0))
    engine.back()

    assert midi.sent[-1] == ("off", 0, 60)
    assert engine.view().next_index == 0

    engine.advance(gesture(2.0))
    assert midi.sent[-1] == ("on", 0, 60, 64)

    engine.back()
    engine.back()                          # clamps at 0
    assert engine.view().next_index == 0


def test_jump_replays_control_state():
    score = make_score(
        [
            [make_note(60, 0, 480)],
            [make_note(62, 480, 960)],
            [make_note(64, 960, 1440)],
        ],
        setup=[control("program", 0, 1)],
        step_controls={1: [control("program", 0, 5, tick=480)]},
    )
    engine, midi = build(score)
    midi.sent.clear()

    engine.jump(2)

    # Only the *latest* program state is replayed.
    assert midi.of_kind("program") == [("program", 0, 5)]
    assert engine.view().next_index == 2

    engine.advance(gesture(1.0))
    assert midi.sent[-1] == ("on", 0, 64, 64)


def test_restart_resets_and_replays_setup():
    score = make_score(
        [[make_note(60, 0, 480)], [make_note(62, 480, 960)]],
        setup=[control("program", 0, 3)],
    )
    engine, midi = build(score)

    engine.advance(gesture(1.0))
    midi.sent.clear()

    engine.restart()

    assert ("off", 0, 60) in midi.sent
    assert ("program", 0, 3) in midi.sent
    assert engine.view().next_index == 0


# ------------------- Suspend / panic ---------------------


def test_suspend_silences_but_keeps_position():
    score = make_score([
        [make_note(60, 0, 480)],
        [make_note(62, 480, 960)],
    ])
    engine, midi = build(score)

    engine.advance(gesture(1.0))
    engine.suspend()

    assert midi.sent[-1] == ("off", 0, 60)
    view = engine.view()
    assert view.suspended
    assert view.next_index == 1            # position preserved

    engine.advance(gesture(2.0))
    assert midi.sent[-1] == ("on", 0, 62, 64)
    assert not engine.view().suspended


def test_panic_sends_midi_panic():
    score = make_score([[make_note(60, 0, 480)]])
    engine, midi = build(score)

    engine.advance(gesture(1.0))
    engine.panic()

    assert ("off", 0, 60) in midi.sent
    assert midi.sent[-1] == ("panic",)


# ------------------- Timed releases ----------------------


def timed(**kw):
    defaults = dict(
        alpha=0.4, rate_min=0.2, rate_max=5.0,
        min_gate_s=0.01, max_hold_s=10.0,
    )
    defaults.update(kw)
    return TimedRelease(**defaults)


def test_timed_mode_schedules_note_off():
    score = make_score([[make_note(60, 0, 250)]])   # 0.25 s
    engine, midi = build(score, mode=timed())

    engine.advance(gesture(100.0))

    assert engine.process(100.20) is not None      # still pending
    assert ("off", 0, 60) not in midi.sent

    engine.process(100.26)
    assert midi.sent[-1] == ("off", 0, 60)
    assert midi.balanced()


def test_positional_release_beats_late_schedule():
    score = make_score([
        [make_note(60, 0, 480)],                    # 0.48 s
        [make_note(62, 480, 960)],
    ])
    engine, midi = build(score, mode=timed())

    engine.advance(gesture(100.0))
    engine.advance(gesture(100.1))    # boundary releases 60 early

    offs_60 = [m for m in midi.sent if m == ("off", 0, 60)]
    assert len(offs_60) == 1

    engine.process(101.0)             # stale schedule: no double off
    offs_60 = [m for m in midi.sent if m == ("off", 0, 60)]
    assert len(offs_60) == 1


def test_generation_guard_protects_retriggered_note():
    score = make_score([
        [make_note(60, 0, 960)],                    # 0.96 s
        [make_note(60, 480, 1440)],                 # same key again
    ])
    engine, midi = build(score, mode=timed())

    engine.advance(gesture(200.0))    # gen 1, off due 200.96
    engine.advance(gesture(200.1))    # retrigger -> gen 2

    # Exactly one off so far (the retrigger release); the
    # gen-2 note is sounding with its own, earlier schedule
    # (pace estimate shortened it).
    midi.sent.clear()

    engine.process(200.7)             # gen-2 schedule fires
    assert midi.sent == [("off", 0, 60)]

    engine.process(201.5)             # stale gen-1 entry pops:
    assert midi.sent == [("off", 0, 60)]   # no double release
    assert engine.view().sounding == ()


def test_mode_switch_clears_pending_schedule():
    score = make_score([[make_note(60, 0, 250)]])
    engine, midi = build(score, mode=timed())

    engine.advance(gesture(100.0))
    engine.set_mode(SustainRelease())

    engine.process(200.0)
    assert ("off", 0, 60) not in midi.sent   # sustain holds it

    engine.advance(gesture(300.0))           # cutoff releases
    assert midi.balanced()
