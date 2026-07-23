# =================================================
# GESTURE DETECTORS
#
# Turn raw suit frames into *validated movements*.
# Pure state machines: no I/O, no wall clock — all
# timing uses the ESP32's own 64-bit millisecond
# timestamp, so detection is deterministic and
# replayable given the same frame sequence, and
# immune to HTTP jitter.
#
# Two validation principles:
#   Piezo   - the firmware's 1 kHz detector already
#             validated the strike; we only diff its
#             monotonic hit counter (reboot-safe).
#   Swing   - Schmitt trigger on an Euler angle
#             (fire / re-arm thresholds) + minimum
#             angular speed + refractory period, so
#             posture drift, slow repositioning and
#             sensor noise can never advance the
#             score. Only a deliberate, fast crossing
#             fires.
# =================================================

from engine.navigation import GestureEvent


def _clamp01(x):
    return max(0.0, min(1.0, x))


# ------------------- Piezo hits --------------------


class PiezoHitDetector:
    """
    Diffs the firmware's monotonic hit counter for one
    side ("left"/"right"). A decrease means the ESP32
    rebooted: the baseline resets without firing, so a
    reboot can never replay history as gestures. Strength
    comes from the reported ADC hit peak.
    """

    def __init__(self, source, side, *, peak_floor, peak_ceil):
        self.source = source
        self._side = side
        self._floor = float(peak_floor)
        self._ceil = float(peak_ceil)
        self._baseline = None

    def reset(self):
        # Forces re-baselining on the next frame; pending
        # counts accumulated while suspended are absorbed,
        # not replayed.
        self._baseline = None

    def _strength(self, peak):
        if not isinstance(peak, (int, float)):
            # A detected hit with a corrupt peak still
            # advances — at full strength, like Sound_V2's
            # velocity fallback.
            return 1.0

        span = self._ceil - self._floor
        if span <= 0.0:
            return 1.0

        return _clamp01((float(peak) - self._floor) / span)

    def process(self, packet, mono):
        piezo = packet.get("piezo")
        if not isinstance(piezo, dict):
            return []

        channel = piezo.get(self._side)
        if not isinstance(channel, dict):
            return []

        hits = channel.get("hits")
        if not isinstance(hits, int):
            return []

        if self._baseline is None or hits < self._baseline:
            self._baseline = hits
            return []

        if hits == self._baseline:
            return []

        self._baseline = hits

        # Several counts inside one ~10 ms frame are switch
        # bounce, not intent: one gesture per frame.
        return [GestureEvent(
            source=self.source,
            strength=self._strength(channel.get("hit_peak")),
            mono=mono,
            device_ts=packet.get("timestamp"),
        )]


# ------------------- Arm swings ---------------------


class SwingDetector:
    """
    One arm's swing trigger. Fires when the sign-adjusted
    angle crosses fire_deg while moving at least
    min_speed_dps, then stays disarmed until the angle
    returns below rearm_deg and refractory_ms of device
    time has passed. Strength is the crossing speed
    normalized to full_speed_dps.

    Discontinuities (frame gaps, ESP32 reboots, heading
    wraps, sensor glitches) resynchronize the state
    instead of firing — codified in _resync().
    """

    def __init__(
        self,
        source,
        *,
        body,
        field,
        sign,
        fire_deg,
        rearm_deg,
        min_speed_dps,
        full_speed_dps,
        refractory_ms,
        max_step_deg=90.0,
        max_gap_ms=250,
    ):
        if rearm_deg >= fire_deg:
            raise ValueError(
                f"{source}: rearm_deg must be below fire_deg"
            )

        self.source = source
        self._body = body
        self._field = field
        self._sign = float(sign)
        self._fire = float(fire_deg)
        self._rearm = float(rearm_deg)
        self._min_speed = float(min_speed_dps)
        self._full_speed = float(full_speed_dps)
        self._refractory = float(refractory_ms)
        self._max_step = float(max_step_deg)
        self._max_gap = float(max_gap_ms)

        self._last_ts = None
        self._last_angle = None
        self._armed = False
        self._last_fire_ts = -1e15

    def reset(self):
        self._last_ts = None
        self._last_angle = None
        self._armed = False

    def _angle_of(self, packet):
        for imu in packet.get("imu_data", ()):
            if isinstance(imu, dict) and \
                    imu.get("body") == self._body:
                if imu.get("ok") is False:
                    return None

                value = imu.get(self._field)
                if isinstance(value, (int, float)):
                    return self._sign * float(value)

                return None
        return None

    def _resync(self, ts, angle):
        self._last_ts = ts
        self._last_angle = angle
        # Only arm from below the re-arm plane: an arm that
        # reappears already past the trigger cannot fire on
        # its first fresh frame.
        self._armed = angle <= self._rearm

    def process(self, packet, mono):
        ts = packet.get("timestamp")
        if not isinstance(ts, int):
            return []

        angle = self._angle_of(packet)
        if angle is None:
            # Sensor missing/not ok: hold state. A long gap
            # will resync through the dt check on return.
            return []

        if self._last_ts is None:
            self._resync(ts, angle)
            return []

        dt_ms = ts - self._last_ts

        if dt_ms <= 0 or dt_ms > self._max_gap or \
                abs(angle - self._last_angle) > self._max_step:
            # Reboot (ts decrease), dropped frames, heading
            # wrap or glitch: never derive a speed from it.
            self._resync(ts, angle)
            return []

        speed = (angle - self._last_angle) / dt_ms * 1000.0

        events = []

        if self._armed:
            # Fire only on the actual crossing (previous
            # frame below the plane, current at/above): an
            # arm parked above the plane cannot fire from
            # jitter, and each excursion fires exactly once.
            if self._last_angle < self._fire <= angle and \
                    speed >= self._min_speed and \
                    ts - self._last_fire_ts >= self._refractory:
                span = self._full_speed - self._min_speed
                strength = _clamp01(
                    (speed - self._min_speed) / span
                ) if span > 0 else 1.0

                events.append(GestureEvent(
                    source=self.source,
                    strength=strength,
                    mono=mono,
                    device_ts=ts,
                ))

                self._armed = False
                self._last_fire_ts = ts
        elif angle <= self._rearm:
            self._armed = True

        self._last_ts = ts
        self._last_angle = angle

        return events
