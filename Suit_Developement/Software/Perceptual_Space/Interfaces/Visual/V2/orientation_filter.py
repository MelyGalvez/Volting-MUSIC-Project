import math

from quaternion import (
    identity,
    normalize,
    slerp,
    angle_between,
    same_hemisphere,
    is_valid,
)
from config import (
    FILTER_TIME_CONSTANT,
    FILTER_MAX_RATE_DPS,
    FILTER_MAX_REJECTS,
)


# ================================================
# ORIENTATION FILTER
# ================================================


class OrientationFilter:
    """
    Abstract interface for every orientation filter.

    Any orientation filter used by the motion capture pipeline
    must implement this interface so that the Skeleton remains
    independent of the filtering algorithm.

    """


# --------------- Push measurement ----------------


    def push(self, q):
        """
        Process a newly acquired orientation measurement.

        """
        raise NotImplementedError


# ----------------- Update filter -----------------


    def step(self, dt):
        """
        Advance the filter by one rendering frame.

        """
        raise NotImplementedError


# ------------- Current orientation ---------------


    @property
    def value(self):
        """
        Return the current filtered orientation.

        """
        raise NotImplementedError


# ----------- Filter resynchronization ------------


    def resync(self):
        """
        Reset the filter.

        The next valid measurement is accepted immediately without
        interpolation.

        """
        raise NotImplementedError


class SlerpFilter(OrientationFilter):
    """
    Quaternion-based orientation filter.

    The filter smooths the incoming orientation measurements
    using spherical linear interpolation (SLERP), rejects
    implausible angular jumps and holds the last valid pose
    whenever data is temporarily unavailable.
    
    """


# ------------------ Constructor ------------------


    def __init__(self, time_constant, max_rate_dps, max_rejects):
        """
        Create a new SLERP orientation filter.

        """
        self.time_constant = time_constant
        self.max_rate_dps = max_rate_dps
        self.max_rejects = max_rejects

        self._value = identity()
        self._target = identity()
        self._initialized = False

        self._time_since_valid = 0.0
        self._rejects = 0

    @property
    def value(self):
        """
        Return the current filtered orientation.

        """
        return self._value

    def push(self, q):
        """
        Process a newly received quaternion.

        The quaternion is validated, normalized and compared to
        the current target orientation. Implausible angular jumps
        are rejected while valid measurements become the new
        filtering target.

        """

        if not is_valid(q):
            return False

        q = normalize(q)

        if not self._initialized:
            self._target = q
            self._value = q
            self._initialized = True
            self._time_since_valid = 0.0
            self._rejects = 0
            return True

        q = same_hemisphere(q, self._target)

        dt = max(self._time_since_valid, 1e-3)
        change = angle_between(self._target, q)
        allowed = self.max_rate_dps * dt

        if change > allowed and self._rejects < self.max_rejects:
            self._rejects += 1
            return False

        self._target = q
        self._time_since_valid = 0.0
        self._rejects = 0
        return True


# ----------------- Filter update ------------------


    def step(self, dt):
        """
        Advance the filter by one rendering frame.

        The current orientation moves progressively toward the
        target orientation using spherical linear interpolation.

        """
        
        self._time_since_valid += dt

        if not self._initialized or self.time_constant <= 0.0:
            self._value = self._target
            return self._value

        alpha = 1.0 - math.exp(-dt / self.time_constant)
        self._value = slerp(self._value, self._target, alpha)
        return self._value

    def resync(self):
        """
        Reset the filter state.

        The next accepted quaternion becomes immediately both the
        current value and the target orientation.

        """

        self._initialized = False
        self._time_since_valid = 0.0
        self._rejects = 0


def make_filter():
    """
    Create the default orientation filter.

    The filter parameters are loaded from the configuration file.

    """
    return SlerpFilter(
        time_constant=FILTER_TIME_CONSTANT,
        max_rate_dps=FILTER_MAX_RATE_DPS,
        max_rejects=FILTER_MAX_REJECTS,
    )