# =================================================
# RELEASE MODE TESTS
#
# TimedRelease pace estimation (EMA, clamps) and
# duration scheduling, plus factory validation.
# =================================================

from types import SimpleNamespace

import pytest

import config
from engine import SustainRelease, TimedRelease, make_release_mode
from engine.velocity import make_velocity_policy
from tests.helpers import make_note


def step(time_s, notes):
    return SimpleNamespace(time_s=time_s, notes=tuple(notes))


def timed(**kw):
    defaults = dict(
        alpha=0.5, rate_min=0.2, rate_max=5.0,
        min_gate_s=0.01, max_hold_s=10.0,
    )
    defaults.update(kw)
    return TimedRelease(**defaults)


def test_sustain_schedules_nothing():
    mode = SustainRelease()
    note = make_note(60, 0, 480)
    assert list(mode.on_step(step(0.0, [note]), 100.0)) == []


def test_first_step_uses_nominal_rate():
    mode = timed()
    note = make_note(60, 0, 480)      # 0.48 s written

    requests = mode.on_step(step(0.0, [note]), 100.0)

    assert requests == [((0, 60), pytest.approx(100.48))]
    assert mode.rate == 1.0


def test_rate_follows_performer_pace():
    mode = timed(alpha=0.5)
    note = make_note(60, 0, 480)

    mode.on_step(step(0.0, [note]), 100.0)
    # 0.5 file-seconds performed in 1.0 wall-second: half pace.
    requests = mode.on_step(step(0.5, [note]), 101.0)

    assert mode.rate == pytest.approx(0.75)   # 1.0 EMA-> 0.5
    # Duration is stretched by the slower pace.
    assert requests[0][1] == pytest.approx(101.0 + 0.48 / 0.75)


def test_instant_rate_clamped():
    mode = timed(rate_max=5.0)
    note = make_note(60, 0, 480)

    mode.on_step(step(0.0, [note]), 100.0)
    # 10 file-seconds in 2 ms would be rate 5000: clamp to 5.
    mode.on_step(step(10.0, [note]), 100.002)

    assert mode.rate <= 1.0 + 0.5 * (5.0 - 1.0)


def test_duration_clamps():
    mode = timed(min_gate_s=0.05, max_hold_s=2.0)

    tiny = make_note(60, 0, 10)        # 10 ms written
    long = make_note(62, 0, 60_000)    # 60 s written

    requests = mode.on_step(step(0.0, [tiny, long]), 100.0)

    assert requests[0][1] == pytest.approx(100.05)
    assert requests[1][1] == pytest.approx(102.0)


def test_reset_restores_nominal():
    mode = timed(alpha=1.0)
    note = make_note(60, 0, 480)

    mode.on_step(step(0.0, [note]), 100.0)
    mode.on_step(step(0.5, [note]), 101.0)
    assert mode.rate != 1.0

    mode.reset()
    assert mode.rate == 1.0
    # No stale gap: next step is a "first" step again.
    requests = mode.on_step(step(3.0, [note]), 200.0)
    assert requests[0][1] == pytest.approx(200.48)


# ------------------- Factories ------------------------


def test_release_mode_factory():
    assert make_release_mode("sustain", config).name == "sustain"
    assert make_release_mode("timed", config).name == "timed"

    with pytest.raises(ValueError):
        make_release_mode("beat", config)


def test_velocity_factory():
    kw = dict(floor_scale=0.5, base_min=30, base_max=127)

    assert make_velocity_policy("file", **kw).apply(90, 0.0) == 90

    gesture_policy = make_velocity_policy("gesture", **kw)
    assert gesture_policy.apply(90, 0.0) == 30
    assert gesture_policy.apply(90, 1.0) == 127

    blend = make_velocity_policy("blend", **kw)
    assert blend.apply(100, 0.0) == 50
    assert blend.apply(100, 1.0) == 100
    assert blend.apply(1, 0.0) == 1        # never 0 (= note-off)

    with pytest.raises(ValueError):
        make_velocity_policy("loudness", **kw)
