import math

import quaternion as quat


# ================================================
# IMU MAPPING
# ================================================


"""
Reference unit vectors defining the body coordinate system.

These vectors describe the physical mounting orientation of
each BNO055 on the suit and are used to compute the mounting
correction quaternion for each IMU.

Coordinate system (OpenGL display frame):

+X : Right
-X : Left
+Y : Up
-Y : Down
+Z : Back (toward the viewer)
-Z : Forward
"""

RIGHT = (1.0, 0.0, 0.0)
LEFT = (-1.0, 0.0, 0.0)
UP = (0.0, 1.0, 0.0)
DOWN = (0.0, -1.0, 0.0)
BACK = (0.0, 0.0, 1.0)
FORWARD = (0.0, 0.0, -1.0)


# -------------- Quaternion utilities -------------


def _quat_from_matrix(m):
    """
    Compute a quaternion from a rotation matrix.

    Converts a 3×3 rotation matrix into its equivalent
    normalized quaternion (Shepperd's method: the branch is
    chosen from the largest diagonal term for numerical
    stability).

    The matrix is provided as three rows.

    """

    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    return quat.normalize((w, x, y, z))


# --------------- Mounting correction -------------


def _mount_correction(x_to, y_to, z_to):
    """
    Build the mounting correction quaternion.

    The arguments state where each SENSOR axis points in
    the BODY frame while the wearer holds the T-pose. The
    resulting quaternion C maps sensor-frame vectors into
    body-frame vectors; it is applied to the local delta
    rotation as C * delta * conj(C).

    """

    m = [
        [x_to[0], y_to[0], z_to[0]],
        [x_to[1], y_to[1], z_to[1]],
        [x_to[2], y_to[2], z_to[2]],
    ]
    return _quat_from_matrix(m)


# ----------- IMU Mounting Configuration ----------


MOUNT_CORRECTION = {

    "back_upper":    _mount_correction(RIGHT,   UP,    BACK),
    "back_lower":    _mount_correction(LEFT,    DOWN,  BACK),

    "left_arm":      _mount_correction(FORWARD, LEFT,  UP),
    "left_forearm":  _mount_correction(FORWARD, LEFT,  UP),
    "left_hand":     _mount_correction(FORWARD, LEFT,  UP),

    "right_arm":     _mount_correction(BACK,    RIGHT, UP),
    "right_forearm": _mount_correction(BACK,    RIGHT, UP),
    "right_hand":    _mount_correction(BACK,    RIGHT, UP),
}


# ------------- Global World Alignment ------------


# Optional fixed rotation applied after the mounting
# correction. Identity by default; the flag below is
# precomputed so the per-frame path never rebuilds and
# compares quaternions.
WORLD_ALIGN = quat.identity()

_WORLD_ALIGN_ACTIVE = WORLD_ALIGN != quat.identity()


# -------------- Quaternion Conversion ------------


def convert_quaternion(body, w, x, y, z):
    """
    Convert one IMU delta quaternion into the body frame.

    Expects a LOCAL delta (conj(reference) * current, the
    firmware v2 convention): its rotation axes live in the
    sensor's calibration frame, which is exactly the frame
    the mounting table describes. The similarity transform
    C * q * conj(C) then re-expresses the same physical
    rotation around body axes.

    """

    q = quat.normalize((w, x, y, z))

    correction = MOUNT_CORRECTION.get(body)
    if correction is not None:
        q = quat.multiply(
            quat.multiply(correction, q),
            quat.conjugate(correction),
        )

    if _WORLD_ALIGN_ACTIVE:
        q = quat.multiply(
            quat.multiply(WORLD_ALIGN, q),
            quat.conjugate(WORLD_ALIGN),
        )

    return quat.normalize(q)
