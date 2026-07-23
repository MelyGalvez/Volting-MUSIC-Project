# =================================================
# MAPPING
#
# Pure angle -> music mapping logic. No I/O, no
# globals, no wall-clock access: everything here is
# deterministic and unit-testable.
# =================================================


# ---------------- Utility functions --------------


def clamp(x: float, a: float, b: float) -> float:
    """
    Clamp a value between a minimum and a maximum.
    """

    return max(a, min(b, x))


def linear_map(
    value: float,
    in_min: float,
    in_max: float,
    out_min: float,
    out_max: float,
) -> float:
    """
    Clamp value into [in_min, in_max] and map it linearly
    onto [out_min, out_max].
    """

    value = clamp(value, in_min, in_max)

    span = in_max - in_min
    if span == 0.0:
        return out_min

    ratio = (value - in_min) / span

    return out_min + ratio * (out_max - out_min)


def to_cc(value: float) -> int:
    """
    Round a 0..127 float onto an integer CC value.

    round() (not int truncation) so the top value is
    reachable across the last half step, not only at the
    exact range endpoint.
    """

    return int(round(clamp(value, 0.0, 127.0)))


# ----------------- Bin selection ------------------


class BinSelector:
    """
    Map a continuous angle onto one of N discrete bins
    with hysteresis.

    Bins divide [angle_min, angle_max] evenly (the naive
    int(ratio * (N - 1)) of the previous implementation
    produced uneven bins and made the last bin reachable
    only at the exact endpoint). The selected bin changes
    only when the angle moves `hysteresis` degrees past a
    bin boundary, which eliminates flutter when a limb
    rests near a boundary.
    """

    def __init__(self, bins, angle_min, angle_max, hysteresis):
        if bins < 1:
            raise ValueError("bins must be >= 1")
        if angle_max <= angle_min:
            raise ValueError("empty angle range")

        self.bins = bins
        self.angle_min = float(angle_min)
        self.angle_max = float(angle_max)
        self.hysteresis = float(hysteresis)

        self._width = (self.angle_max - self.angle_min) / bins
        self._current = None

    def _raw_bin(self, angle: float) -> int:
        offset = angle - self.angle_min
        raw = int(offset / self._width)
        return max(0, min(self.bins - 1, raw))

    def select(self, angle: float) -> int:
        """
        Return the stable bin index for this angle.
        """

        angle = clamp(angle, self.angle_min, self.angle_max)
        raw = self._raw_bin(angle)

        if self._current is None:
            self._current = raw
            return raw

        if raw == self._current:
            return self._current

        # Boundaries of the currently held bin.
        low = self.angle_min + self._current * self._width
        high = low + self._width

        if angle > high + self.hysteresis or \
           angle < low - self.hysteresis:
            self._current = raw

        return self._current

    @property
    def current(self):
        """
        Currently held bin index (None before the first
        selection).
        """

        return self._current

    def reset(self):
        """
        Forget the held bin (used after data loss so the
        next selection snaps directly to the measurement).
        """

        self._current = None


# ----------------- Note mapping ------------------


# C major scale as semitone offsets. The final 12 is the
# octave-up C, giving 8 selectable degrees.
SCALE = [
    0,   # C
    2,   # D
    4,   # E
    5,   # F
    7,   # G
    9,   # A
    11,  # B
    12   # C
]


def build_midi_note(octave: int, semitone: int) -> int:
    """
    Build a MIDI note number from a musical octave and a
    semitone offset.

    Standard MIDI convention: C4 = 60 = (4 + 1) * 12.
    (The previous octave * 12 formula produced notes one
    octave below the octave number shown in the UI.)
    """

    return max(0, min(127, (octave + 1) * 12 + semitone))


# --------------- Velocity mapping ----------------


def velocity_from_peak(
    peak,
    peak_floor,
    peak_ceil,
    velocity_min,
    velocity_max,
) -> int:
    """
    Map a piezo hit peak (ADC counts) onto a MIDI velocity,
    so playing dynamics follow strike strength.

    Invalid peaks fall back to the maximum velocity rather
    than silencing a detected hit.
    """

    try:
        peak = float(peak)
    except (TypeError, ValueError):
        return velocity_max

    v = linear_map(
        peak,
        peak_floor,
        peak_ceil,
        velocity_min,
        velocity_max,
    )

    return int(round(v))
