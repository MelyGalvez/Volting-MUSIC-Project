# =================================================
# GESTURE DETECTOR & ROUTER TESTS
#
# Validation logic on synthetic suit frames: piezo
# counter diffs (reboot-safe), swing Schmitt trigger
# with speed gate / re-arm / refractory /
# discontinuity resync, and the router's system-state
# gating and action mapping.
# =================================================

from inputs import GestureRouter, PiezoHitDetector, SwingDetector
from tests.helpers import packet


# --------------------- Piezo ------------------------


def piezo(hits, peak=4095, side="left", ts=1000):
    return packet(ts, piezo={
        side: {"peak": 0, "hits": hits, "hit_peak": peak},
    })


def make_piezo():
    return PiezoHitDetector(
        "piezo_left", "left", peak_floor=500, peak_ceil=4095,
    )


def test_piezo_baseline_absorbed_without_firing():
    det = make_piezo()
    assert det.process(piezo(17), 0.0) == []


def test_piezo_fires_on_counter_increase():
    det = make_piezo()
    det.process(piezo(17), 0.0)

    events = det.process(piezo(18, peak=4095), 1.0)
    assert len(events) == 1
    assert events[0].source == "piezo_left"
    assert events[0].strength == 1.0


def test_piezo_strength_from_hit_peak():
    det = make_piezo()
    det.process(piezo(0), 0.0)

    mid_peak = (500 + 4095) / 2
    events = det.process(piezo(1, peak=mid_peak), 1.0)
    assert abs(events[0].strength - 0.5) < 0.01

    events = det.process(piezo(2, peak=100), 2.0)
    assert events[0].strength == 0.0


def test_piezo_reboot_resets_baseline_without_firing():
    det = make_piezo()
    det.process(piezo(50), 0.0)

    assert det.process(piezo(3), 1.0) == []      # counter fell
    events = det.process(piezo(4), 2.0)          # next real hit
    assert len(events) == 1


def test_piezo_reset_absorbs_pending_hits():
    det = make_piezo()
    det.process(piezo(10), 0.0)
    det.reset()

    assert det.process(piezo(25), 1.0) == []     # re-baseline
    assert len(det.process(piezo(26), 2.0)) == 1


def test_piezo_malformed_fields_ignored():
    det = make_piezo()
    assert det.process(packet(0), 0.0) == []
    assert det.process(
        packet(1, piezo={"left": {"hits": "NaN"}}), 0.1
    ) == []


# --------------------- Swings ------------------------


def make_swing(**overrides):
    params = dict(
        body="left_arm", field="roll", sign=1.0,
        fire_deg=35.0, rearm_deg=20.0,
        min_speed_dps=120.0, full_speed_dps=600.0,
        refractory_ms=150, max_step_deg=90.0, max_gap_ms=250,
    )
    params.update(overrides)
    return SwingDetector("swing_left", **params)


def frame(ts, roll):
    return packet(ts, imus={"left_arm": {"roll": roll}})


def run(det, samples):
    events = []
    for ts, roll in samples:
        events.extend(det.process(frame(ts, roll), ts / 1000.0))
    return events


def test_fast_crossing_fires_once():
    det = make_swing()
    events = run(det, [
        (1000, 0.0), (1020, 10.0), (1040, 45.0), (1060, 70.0),
    ])

    assert len(events) == 1
    assert events[0].strength == 1.0     # 1750 dps, well past full


def test_slow_crossing_never_fires():
    det = make_swing()
    samples = [(1000 + i * 100, i * 8.0) for i in range(10)]
    assert run(det, samples) == []       # 80 dps < 120 dps gate


def test_jitter_above_plane_cannot_fire():
    det = make_swing()
    run(det, [(1000 + i * 100, i * 8.0) for i in range(10)])

    # Parked at 72 deg; noise spikes with high instant speed
    # but no crossing from below the plane.
    events = run(det, [(2000, 72.0), (2010, 76.0), (2020, 72.0)])
    assert events == []


def test_rearm_required_between_fires():
    det = make_swing()
    events = run(det, [
        (1000, 0.0), (1020, 45.0),          # fire
        (1200, 30.0), (1220, 60.0),         # above rearm: no fire
        (1400, 10.0),                       # re-arm
        (1420, 50.0),                       # fire again
    ])

    assert len(events) == 2


def test_refractory_blocks_immediate_refire():
    det = make_swing(refractory_ms=500)
    events = run(det, [
        (1000, 0.0), (1020, 45.0),          # fire at ts 1020
        (1100, 10.0),                       # re-arm
        (1120, 50.0),                       # only 100 ms later
        (1700, 5.0),                        # re-arm, past refractory
        (1720, 55.0),                       # fires
    ])

    assert [e.device_ts for e in events] == [1020, 1720]


def test_time_gap_resyncs_instead_of_firing():
    det = make_swing()
    events = run(det, [
        (1000, 0.0),
        (2000, 80.0),      # 1 s hole: resync, never a gesture
    ])
    assert events == []


def test_timestamp_reboot_resyncs():
    det = make_swing()
    events = run(det, [
        (500_000, 0.0),
        (100, 50.0),       # ESP32 rebooted: ts went backwards
        (120, 55.0),
    ])
    assert events == []


def test_angle_jump_glitch_resyncs():
    det = make_swing()
    events = run(det, [
        (1000, 0.0), (1020, 5.0),
        (1040, 170.0),     # 165 deg in one frame: wrap/glitch
    ])
    assert events == []


def test_sensor_not_ok_holds_state():
    det = make_swing()
    det.process(frame(1000, 0.0), 1.0)

    bad = packet(1020, imus={"left_arm": {"roll": 45.0}})
    bad["imu_data"][0]["ok"] = False
    assert det.process(bad, 1.02) == []

    # Sensor returns quickly: normal crossing still fires.
    events = det.process(frame(1040, 45.0), 1.04)
    assert len(events) == 1


def test_sign_flips_direction():
    det = make_swing(sign=-1.0)
    events = run(det, [(1000, 0.0), (1020, -45.0)])
    assert len(events) == 1


def test_reappearing_above_plane_cannot_fire():
    det = make_swing()
    # First ever frame already past the trigger: must arm
    # only after coming below rearm.
    events = run(det, [
        (1000, 60.0), (1020, 80.0),
        (1200, 10.0),                       # arms here
        (1220, 50.0),                       # genuine crossing
    ])
    assert len(events) == 1
    assert events[0].device_ts == 1220


# --------------------- Router ------------------------


class FakeDetector:
    def __init__(self, source, events_per_call=1):
        self.source = source
        self.events_per_call = events_per_call
        self.resets = 0

    def process(self, packet_, mono):
        from engine import GestureEvent
        return [
            GestureEvent(self.source, 1.0, mono)
            for _ in range(self.events_per_call)
        ]

    def reset(self):
        self.resets += 1


def test_router_maps_sources_to_actions():
    left = FakeDetector("piezo_left")
    right = FakeDetector("piezo_right")

    router = GestureRouter(
        [left, right],
        {"piezo_left": "advance", "piezo_right": "back"},
    )

    actions = router.process(packet(1000), 1.0)
    assert [a for a, _e in actions] == ["advance", "back"]


def test_router_off_disables_source():
    det = FakeDetector("swing_left")
    router = GestureRouter([det], {"swing_left": "off"})

    assert router.active_sources == ()
    assert router.process(packet(1000), 1.0) == []


def test_router_gates_on_system_state():
    det = FakeDetector("piezo_left")
    router = GestureRouter([det], {"piezo_left": "advance"})

    calibrating = packet(1000, system="calibration")
    assert router.process(calibrating, 1.0) == []
    assert det.resets == 1                  # state dropped

    ready = packet(1100, system="ready")
    assert len(router.process(ready, 1.1)) == 1

    degraded = packet(1200, system="degraded")
    assert len(router.process(degraded, 1.2)) == 1


def test_router_rejects_unknown_action():
    det = FakeDetector("piezo_left")

    try:
        GestureRouter([det], {"piezo_left": "teleport"})
    except ValueError as exc:
        assert "teleport" in str(exc)
    else:
        raise AssertionError("expected ValueError")
