import math

import quaternion as quat


# ================================================
# IMU MAPPING
# ================================================


"""
Reference unit vectors defining the body coordinate system.

These vectors are used to describe the physical orientation
of each BNO055 sensor on the motion capture suit.

They are also used to automatically compute the mounting
correction quaternion for each IMU.

Coordinate system:

+X : Right
-Y : Left
+Y : Up
-Y : Down
+Z : Back
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
    normalized quaternion.

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

    Computes the quaternion transforming the sensor
    coordinate frame into the body coordinate frame.

    The correction is generated directly from the
    physical orientation of the BNO055.

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


WORLD_ALIGN = quat.identity()


# -------------- Quaternion Conversion ------------


def convert_quaternion(body, w, x, y, z):
    """
    Convert one IMU quaternion into the body frame.

    Applies both the per-sensor mounting correction
    and the optional global world alignment.

    The returned quaternion is directly usable by
    the skeleton kinematics.

    """
    
    q = quat.normalize((w, x, y, z))

    correction = MOUNT_CORRECTION.get(body)
    if correction is not None:
        q = quat.multiply(
            quat.multiply(correction, q),
            quat.conjugate(correction),
        )

    if WORLD_ALIGN != quat.identity():
        q = quat.multiply(
            quat.multiply(WORLD_ALIGN, q),
            quat.conjugate(WORLD_ALIGN),
        )

    return quat.normalize(q)


# ------------------ Euler mapping ----------------


IMU_MAPPING = {

    "back_upper":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "back_lower":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "left_arm":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "right_arm":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "left_forearm":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "right_forearm":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "left_hand":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    },

    "right_hand":
    {
        "pitch_axis": "pitch",
        "roll_axis": "roll",
        "heading_axis": "heading",

        "invert_pitch": False,
        "invert_roll": False,
        "invert_heading": False
    }
}

def apply_orientation(body, imu):
    """
    Apply the Euler axis mapping of one IMU.

    Reorders and optionally inverts the raw Euler angles
    according to the configuration defined for the specified
    body segment.

    This function is used only by the legacy Euler pipeline
    for debugging and backward compatibility.

    """

    if body not in IMU_MAPPING:

        return imu
    

    config = IMU_MAPPING[body]
    

    corrected = {}


    corrected["pitch"] = imu[
        config["pitch_axis"]
    ]


    corrected["roll"] = imu[
        config["roll_axis"]
    ]


    corrected["heading"] = imu[
        config["heading_axis"]
    ]


    if config["invert_pitch"]:

        corrected["pitch"] *= -1


    if config["invert_roll"]:

        corrected["roll"] *= -1


    if config["invert_heading"]:

        corrected["heading"] *= -1


    return corrected


class Rotation:
    """
    Body-frame joint rotation.

    Stores the three body rotations applied to one skeleton
    segment.

    These rotations are expressed around the body X, Y and Z
    axes and are used only by the legacy Euler pipeline.

    """

    def __init__(self, rx, ry, rz):
        """
        Initialize a body rotation.

        Stores the rotations around the body X, Y and Z axes.
    
        """
        
        self.rx = rx
        self.ry = ry
        self.rz = rz


# ------------- Euler rotation mapping ------------


ROTATION_MAP = {

    "back_upper":    {"rx": ("roll", 1),  "ry": ("heading", -1), "rz": ("pitch", 1)},
    "back_lower":    {"rx": ("roll", 1),  "ry": ("heading", -1), "rz": ("pitch", -1)},

    "left_arm":      {"rx": ("roll", 1),  "ry": ("pitch", 1),    "rz": ("heading", -1)},
    "left_forearm":  {"rx": ("roll", 1),  "ry": ("pitch", 1),    "rz": ("heading", -1)},
    "left_hand":     {"rx": ("roll", 1),  "ry": ("pitch", 1),    "rz": ("heading", -1)},

    "right_arm":     {"rx": ("roll", 1),  "ry": ("pitch", 1),    "rz": ("heading", -1)},
    "right_forearm": {"rx": ("roll", 1),  "ry": ("pitch", 1),    "rz": ("heading", -1)},
    "right_hand":    {"rx": ("roll", 1),  "ry": ("pitch", 1),    "rz": ("heading", -1)},
}


# ------- Euler to Body Rotation Conversion -------


def convert_imu(body, heading, pitch, roll):
    """
    Convert Euler angles into body-frame rotations.

    Converts the raw heading, pitch and roll received from
    one BNO055 into rotations expressed in the body frame.

    The conversion is performed in two stages:

        1. Apply the IMU axis remapping and sign corrections.
        2. Assign the corrected angles to the body axes
           according to the rotation mapping.

    This function belongs to the legacy Euler pipeline and is
    retained for debugging and compatibility purposes. The
    quaternion pipeline is now the primary orientation
    representation.

    """

    corrected = apply_orientation(
        body,
        {
            "heading": heading,
            "pitch": pitch,
            "roll": roll,
        },
    )

    mapping = ROTATION_MAP.get(body)

    if mapping is None:

        return Rotation(
            corrected.get("roll", 0.0),
            corrected.get("heading", 0.0),
            corrected.get("pitch", 0.0),
        )

    def axis_value(axis):
        source, sign = mapping[axis]
        return corrected[source] * sign

    return Rotation(
        axis_value("rx"),
        axis_value("ry"),
        axis_value("rz"),
    )