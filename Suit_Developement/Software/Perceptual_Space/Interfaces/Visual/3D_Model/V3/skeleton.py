from OpenGL.GL import *
from OpenGL.GLU import *

from bone import Bone
from config import (
    TORSO_LENGTH,
    LOWER_BACK_LENGTH,
    UPPER_ARM_LENGTH,
    FOREARM_LENGTH,
    HAND_LENGTH,
    HEAD_RADIUS,
    SHOULDER_OFFSET,
)
from mathutils import add
from quaternion import rotate_vector, from_json
from imu_mapping import convert_quaternion
from calibration import apply_offset
from orientation_filter import make_filter


# ================================================
# SKELETON
# ================================================


_UP = (0.0, 1.0, 0.0)
_LEFT = (-1.0, 0.0, 0.0)
_RIGHT = (1.0, 0.0, 0.0)

_HIP = (0.0, -0.5, 0.0)

# System states in which packets carry usable pose data.
_RENDERABLE_STATES = ("ready", "degraded")

# Shared quadric for the head sphere. The previous
# implementation called gluNewQuadric() every frame without
# ever freeing it: a memory leak that grows for the entire
# session.
_head_quadric = None


def _get_head_quadric():
    global _head_quadric
    if _head_quadric is None:
        _head_quadric = gluNewQuadric()
    return _head_quadric


class Skeleton:


# ---------------- Initialization -----------------


    def __init__(self):
        """
        Create the complete kinematic skeleton.

        The constructor initializes every body segment (bones),
        builds the body lookup table, creates one orientation
        filter per segment and resets the sequence tracking used
        to reject duplicated frames.

        """

        self.back_lower = Bone(LOWER_BACK_LENGTH, _UP)
        self.back_upper = Bone(TORSO_LENGTH, _UP)

        self.left_arm = Bone(UPPER_ARM_LENGTH, _LEFT)
        self.left_forearm = Bone(FOREARM_LENGTH, _LEFT)
        self.left_hand = Bone(HAND_LENGTH, _LEFT)

        self.right_arm = Bone(UPPER_ARM_LENGTH, _RIGHT)
        self.right_forearm = Bone(FOREARM_LENGTH, _RIGHT)
        self.right_hand = Bone(HAND_LENGTH, _RIGHT)

        self.bones = {
            "back_upper": self.back_upper,
            "back_lower": self.back_lower,
            "left_arm": self.left_arm,
            "right_arm": self.right_arm,
            "left_forearm": self.left_forearm,
            "right_forearm": self.right_forearm,
            "left_hand": self.left_hand,
            "right_hand": self.right_hand,
        }

        self.filters = {name: make_filter() for name in self.bones}

        self._last_seq = None


# ------------------ Rendering --------------------


    def draw(self):
        """
        Draw the complete articulated skeleton.

        The method performs the forward kinematic traversal of the
        body hierarchy, computes every joint position from the
        current bone orientations and renders the body segments and
        the head.

        """

        self.back_lower.draw(_HIP)
        upper_back = self.back_lower.end_position(_HIP)

        self.back_upper.draw(upper_back)
        neck = self.back_upper.end_position(upper_back)


        torso_quat = self.back_upper.quat
        left_shoulder = add(neck, rotate_vector(torso_quat, (-SHOULDER_OFFSET, 0.0, 0.0)))
        right_shoulder = add(neck, rotate_vector(torso_quat, (SHOULDER_OFFSET, 0.0, 0.0)))


        self.left_arm.draw(left_shoulder)
        left_elbow = self.left_arm.end_position(left_shoulder)

        self.left_forearm.draw(left_elbow)
        left_wrist = self.left_forearm.end_position(left_elbow)

        self.left_hand.draw(left_wrist)


        self.right_arm.draw(right_shoulder)
        right_elbow = self.right_arm.end_position(right_shoulder)

        self.right_forearm.draw(right_elbow)
        right_wrist = self.right_forearm.end_position(right_elbow)

        self.right_hand.draw(right_wrist)


        self.draw_head(neck, torso_quat)

    def draw_head(self, neck, torso_quat):
        """
        Draw the head of the skeleton.

        The head is positioned above the neck by applying the torso
        orientation to a fixed offset before rendering a sphere.

        """

        head_center = add(neck, rotate_vector(torso_quat, (0.0, HEAD_RADIUS * 1.6, 0.0)))

        glColor3f(0.8, 0.8, 0.85)
        glPushMatrix()
        glTranslatef(head_center[0], head_center[1], head_center[2])
        gluSphere(_get_head_quadric(), HEAD_RADIUS, 20, 20)
        glPopMatrix()
        glColor3f(1.0, 1.0, 1.0)


# ---------------- IMU integration ----------------


    def update_from_imu(self, data):
        """
        Integrate one IMU acquisition frame.

        The function validates the received packet, ignores
        invalid or duplicated frames (by sequence number),
        skips sensors flagged not-ok by the firmware, converts
        every valid sensor quaternion into the body reference
        frame and pushes the resulting orientations into the
        corresponding filters. Invalid quaternions are skipped
        (holding the last pose) instead of snapping the bone
        back to T-pose.

        """

        if not isinstance(data, dict):
            return

        if "imu_data" not in data:
            return

        if data.get("system", "ready") not in _RENDERABLE_STATES:
            return


        seq = data.get("seq", data.get("timestamp"))
        if seq is not None and seq == self._last_seq:
            return
        self._last_seq = seq

        for imu in data["imu_data"]:

            body = imu.get("body")
            filt = self.filters.get(body)

            if filt is None:
                continue

            if imu.get("ok") is False:
                continue

            q = from_json(imu)

            if q is None:
                continue

            q = apply_offset(body, q)

            q = convert_quaternion(body, *q)

            filt.push(q)


# ------------------ Filter update ----------------


    def advance(self, dt):
        """
        Advance every orientation filter.

        Each filter is updated according to the elapsed time and
        the resulting filtered quaternion is copied to the
        corresponding bone.

        """

        for body, filt in self.filters.items():
            filt.step(dt)
            self.bones[body].quat = filt.value

    def resync(self):
        """
        Reset the orientation filters.

        The next valid quaternion received from every IMU is
        accepted immediately without interpolation. This is used
        after a manual calibration or after detecting an ESP32
        reboot.

        """
        self._last_seq = None
        for filt in self.filters.values():
            filt.resync()
