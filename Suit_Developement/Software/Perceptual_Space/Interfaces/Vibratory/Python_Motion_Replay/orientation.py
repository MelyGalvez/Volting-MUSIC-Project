"""Quaternion tools, in the exact convention used by the V4 firmware.

Convention (Arduino_Suit_ESP32_Get_Data_V4/quat.h):

  * Hamilton product;
  * component order (w, x, y, z);
  * unit quaternions represent rotations;
  * a quaternion maps a vector expressed in the SENSOR frame to the
    frame captured during the T-pose calibration, because the firmware
    publishes  conj(reference) * raw  (quatDeltaLocal in quat.h).

Two facts are used everywhere below:

  * q and -q are the same rotation (double cover). Every comparison
    must be insensitive to that sign, which is why the angle uses
    |w| and why averaging aligns the signs first.
  * the angle of the rotation separating two orientations is the
    geodesic distance on the rotation group: the shortest angle by
    which the body must turn to go from one to the other. That is the
    quantity a physiotherapist would call "the orientation error", and
    it is what this module returns.
"""

from __future__ import annotations

import math

import numpy as np

#: Below this norm a quaternion carries no usable direction.
_EPSILON = 1e-9


# ----------------------------------------------------------------------
# Basic algebra
# ----------------------------------------------------------------------


def is_valid(values) -> bool:
    """True when the four numbers can be a rotation quaternion.

    The firmware applies the same test (quatIsValid in quat.h): a
    failed I2C read returns four zeros, a corrupted one returns a
    wildly non-unit quaternion.
    """
    if values is None or len(values) != 4:
        return False

    for value in values:
        if value is None:
            return False
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if math.isnan(value) or math.isinf(value):
            return False

    norm_squared = sum(float(value) ** 2 for value in values)

    return 0.7 < norm_squared < 1.3


def normalize(quaternion) -> np.ndarray:
    """Return the unit quaternion, or the identity if it has no norm."""
    quaternion = np.asarray(quaternion, dtype=float)
    norm = float(np.linalg.norm(quaternion))

    if norm < _EPSILON:
        return np.array([1.0, 0.0, 0.0, 0.0])

    return quaternion / norm


def conjugate(quaternion) -> np.ndarray:
    """Inverse rotation (for a unit quaternion)."""
    w, x, y, z = np.asarray(quaternion, dtype=float)

    return np.array([w, -x, -y, -z])


def multiply(left, right) -> np.ndarray:
    """Hamilton product, identical to quatMultiply() in quat.h."""
    lw, lx, ly, lz = np.asarray(left, dtype=float)
    rw, rx, ry, rz = np.asarray(right, dtype=float)

    return np.array([
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    ])


def canonical(quaternion) -> np.ndarray:
    """Return the representative with w >= 0.

    Of the two quaternions describing a rotation, this one always
    encodes the short way round (angle <= 180 degrees).
    """
    quaternion = np.asarray(quaternion, dtype=float)

    return -quaternion if quaternion[0] < 0.0 else quaternion


# ----------------------------------------------------------------------
# Comparing two orientations
# ----------------------------------------------------------------------


def error_rotation(live, reference) -> np.ndarray:
    """Rotation the user must still perform, in the LIVE sensor frame.

        q_error = conj(q_live) * q_reference

    Right-multiplying the live orientation by this quaternion gives the
    reference orientation exactly, which is what makes it "the rotation
    the body must apply". Its axis is a body-fixed axis, so it can be
    compared directly with the gravity vector the same sensor reports
    (see guidance.py for the left/right decision).
    """
    return canonical(
        multiply(conjugate(normalize(live)), normalize(reference))
    )


def angle_deg(quaternion) -> float:
    """Rotation angle of a quaternion, in degrees, within [0, 180].

    Uses atan2 rather than acos(w): near zero error the vector part is
    tiny and acos loses most of its precision there, while atan2 stays
    accurate.
    """
    w, x, y, z = normalize(quaternion)

    vector_norm = math.sqrt(x * x + y * y + z * z)

    return math.degrees(2.0 * math.atan2(vector_norm, abs(w)))


def geodesic_angle_deg(first, second) -> float:
    """Angle separating two orientations, in degrees.

    This is the primary error measure of the whole project.
    """
    return angle_deg(error_rotation(first, second))


def rotation_vector_deg(quaternion) -> np.ndarray:
    """Axis multiplied by angle, in degrees.

    The result is a normal 3D vector: its direction is the rotation
    axis, its length the rotation angle. Components can therefore be
    projected onto physical axes, which Euler angles cannot do safely.
    """
    w, x, y, z = canonical(normalize(quaternion))

    vector = np.array([x, y, z])
    vector_norm = float(np.linalg.norm(vector))

    if vector_norm < _EPSILON:
        return np.zeros(3)

    angle = math.degrees(2.0 * math.atan2(vector_norm, abs(w)))

    return vector / vector_norm * angle


# ----------------------------------------------------------------------
# Averaging and filtering
# ----------------------------------------------------------------------


def average(quaternions) -> np.ndarray | None:
    """Mean orientation of a set of quaternions (Markley's method).

    The mean rotation is the eigenvector of  M = sum(q q^T)  belonging
    to the largest eigenvalue. Unlike a plain component-wise average it
    is exact for the double cover (q and -q give the same M) and it
    stays a valid rotation without a normalisation hack.

    Reference: Markley, Cheng, Crassidis & Oshman, "Averaging
    Quaternions", Journal of Guidance, Control and Dynamics, 2007.
    """
    samples = [normalize(q) for q in quaternions if q is not None]

    if not samples:
        return None

    if len(samples) == 1:
        return canonical(samples[0])

    matrix = np.zeros((4, 4))

    for quaternion in samples:
        matrix += np.outer(quaternion, quaternion)

    matrix /= len(samples)

    _eigenvalues, eigenvectors = np.linalg.eigh(matrix)

    # eigh returns them in ascending order: the last one is the mean.
    return canonical(normalize(eigenvectors[:, -1]))


def dispersion_deg(quaternions, mean=None) -> float:
    """Average angular distance of a set of quaternions to their mean.

    It says how still the body was during the window: a few degrees is
    a stable pose, tens of degrees means the user was still moving.
    """
    samples = [normalize(q) for q in quaternions if q is not None]

    if not samples:
        return float("nan")

    if mean is None:
        mean = average(samples)

    if mean is None:
        return float("nan")

    return float(
        np.mean([geodesic_angle_deg(sample, mean) for sample in samples])
    )


def slerp(start, end, fraction: float) -> np.ndarray:
    """Spherical interpolation, used as the live low pass filter.

    Interpolating on the sphere keeps every intermediate value a unit
    quaternion, so the filtered orientation is always a real rotation.
    """
    start = normalize(start)
    end = normalize(end)

    dot = float(np.dot(start, end))

    # Take the short way round.
    if dot < 0.0:
        end = -end
        dot = -dot

    if fraction <= 0.0:
        return start
    if fraction >= 1.0:
        return canonical(end)

    # Almost identical: a straight line is accurate and avoids a
    # division by a vanishing sine.
    if dot > 0.9995:
        result = start + fraction * (end - start)
        return canonical(normalize(result))

    theta = math.acos(max(-1.0, min(1.0, dot)))
    sin_theta = math.sin(theta)

    weight_start = math.sin((1.0 - fraction) * theta) / sin_theta
    weight_end = math.sin(fraction * theta) / sin_theta

    return canonical(normalize(weight_start * start + weight_end * end))


# ----------------------------------------------------------------------
# Vectors
# ----------------------------------------------------------------------


def unit_vector(vector) -> np.ndarray | None:
    """Return the unit vector, or None when there is nothing to point at."""
    if vector is None:
        return None

    array = np.asarray(vector, dtype=float)

    if array.shape != (3,) or not np.all(np.isfinite(array)):
        return None

    norm = float(np.linalg.norm(array))

    if norm < _EPSILON:
        return None

    return array / norm
