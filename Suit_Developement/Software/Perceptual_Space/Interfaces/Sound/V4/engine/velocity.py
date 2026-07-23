# =================================================
# VELOCITY POLICIES
#
# How the velocity of each played note is produced
# from (written file velocity, movement strength).
# Pure functions of their inputs: no I/O, no clocks.
#
# Strategy objects so new dynamics behaviors (e.g.
# per-limb weighting, accent detection) plug in
# without touching the navigation engine.
# =================================================


def _clamp_velocity(value):
    # 0 would be a note-off on the wire; 1 is the softest
    # audible velocity.
    return max(1, min(127, int(round(value))))


class FileVelocity:
    """Play exactly the dynamics written in the file."""

    name = "file"

    def apply(self, file_velocity, strength):
        return _clamp_velocity(file_velocity)


class GestureVelocity:
    """
    Ignore the file; movement strength alone sets the
    dynamics across [base_min, base_max].
    """

    name = "gesture"

    def __init__(self, base_min, base_max):
        self._min = base_min
        self._max = base_max

    def apply(self, file_velocity, strength):
        strength = max(0.0, min(1.0, strength))
        return _clamp_velocity(
            self._min + strength * (self._max - self._min)
        )


class BlendVelocity:
    """
    Scale the written velocity by movement strength:
    strength 0 keeps floor_scale of the file velocity,
    strength 1 keeps all of it. The score's internal
    phrasing (melody above accompaniment) is preserved
    while the performer shapes the overall dynamics.
    """

    name = "blend"

    def __init__(self, floor_scale):
        self._floor = max(0.0, min(1.0, floor_scale))

    def apply(self, file_velocity, strength):
        strength = max(0.0, min(1.0, strength))
        scale = self._floor + (1.0 - self._floor) * strength
        return _clamp_velocity(file_velocity * scale)


def make_velocity_policy(mode, *, floor_scale, base_min, base_max):
    """
    Build the policy selected by config.VELOCITY_MODE.
    Unknown names fail immediately at startup, not during
    a performance.
    """

    if mode == "file":
        return FileVelocity()
    if mode == "gesture":
        return GestureVelocity(base_min, base_max)
    if mode == "blend":
        return BlendVelocity(floor_scale)

    raise ValueError(f"Unknown velocity mode: {mode!r}")
