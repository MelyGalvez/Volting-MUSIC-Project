"""All tunable parameters of the motion replay system.

Every value can also be given as an environment variable of the same
name, which is handy for trying a different tolerance without editing
the file:

    set POSITION_TOLERANCE_DEG=15
    python main.py

The MQTT values are not invented: they are the ones used by the V4
project (V4/Python_MQTT_Bridge/main.py for the data topic, and
V4/Arduino_Suit_ESP32_Get_Data_V4/config.h for the haptic topic the
firmware subscribes to).
"""

from __future__ import annotations

import os


def _text(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _number(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in ("1", "true", "yes", "on")


# ----------------------------------------------------------------------
# MQTT
# ----------------------------------------------------------------------

#: Broker used by the V4 bridge (Python_MQTT_Bridge/main.py, line 64).
MQTT_BROKER_HOST = _text("MQTT_BROKER_HOST", "192.168.56.1")
MQTT_BROKER_PORT = int(_number("MQTT_BROKER_PORT", 1883))

#: Topic the suit data arrives on (published by the V4 bridge).
MQTT_DATA_TOPIC = _text("MQTT_DATA_TOPIC", "motion_suit/data")

#: Topic the ESP32 listens on for vibration commands
#: (MQTT_HAPTIC_TOPIC in Arduino_Suit_ESP32_Get_Data_V4/config.h).
MQTT_HAPTIC_TOPIC = _text("MQTT_HAPTIC_TOPIC", "motion_suit/haptic")

#: No authentication and no TLS: the bridge and the firmware both
#: connect anonymously.
MQTT_QOS = 0
MQTT_KEEPALIVE_S = 30
MQTT_RECONNECT_MIN_S = 1
MQTT_RECONNECT_MAX_S = 30

#: Live data older than this counts as "no data": the hold timer is
#: reset instead of counting on a frozen orientation.
STALE_DATA_TIMEOUT_S = _number("STALE_DATA_TIMEOUT_S", 1.0)


# ----------------------------------------------------------------------
# Recordings
# ----------------------------------------------------------------------

#: Where the CSV files of the recording project live.
RECORDINGS_DIR = _text(
    "RECORDINGS_DIR",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Python_Motion_Recorder",
        "recordings",
    ),
)


# ----------------------------------------------------------------------
# Reference pose extracted from the end of each movement
# ----------------------------------------------------------------------

#: Length of the window taken at the END of a recorded movement. The
#: target orientation is the average over that window, never a single
#: sample: one sample carries the full sensor noise, half a second at
#: 10 Hz averages ~5 of them.
REFERENCE_WINDOW_S = _number("REFERENCE_WINDOW_S", 0.5)

#: If the window holds fewer usable samples than this, the last
#: REFERENCE_MIN_SAMPLES valid samples of the movement are used instead.
REFERENCE_MIN_SAMPLES = int(_number("REFERENCE_MIN_SAMPLES", 3))

#: A reference whose samples disagree by more than this is reported as
#: unstable (the user was still moving at the END marker). It is a
#: warning, not a rejection.
REFERENCE_MAX_DISPERSION_DEG = _number("REFERENCE_MAX_DISPERSION_DEG", 8.0)

#: Window used to capture the neutral pose (see NEUTRAL_ALIGNMENT).
NEUTRAL_WINDOW_S = _number("NEUTRAL_WINDOW_S", 1.0)


# ----------------------------------------------------------------------
# Comparison
# ----------------------------------------------------------------------

#: Which IMUs take part in the comparison. Empty = every IMU that has a
#: usable target in the recording. Example: ("left_arm", "right_arm").
COMPARE_IMUS: tuple[str, ...] = tuple(
    name.strip()
    for name in _text("COMPARE_IMUS", "").split(",")
    if name.strip()
)

#: How the per-IMU errors become one number.
#:   "max"  : the worst body segment decides (strict, the default)
#:   "mean" : average error over the compared IMUs (forgiving)
ERROR_AGGREGATION = _text("ERROR_AGGREGATION", "max")

#: Low pass filter on the live orientation: the filtered quaternion
#: moves this fraction of the way towards each new sample (SLERP).
#: 1.0 = no filtering, 0.1 = very smooth but slow to react.
FILTER_ALPHA = _number("FILTER_ALPHA", 0.35)

#: Compare the live pose against the reference after aligning both on
#: their neutral pose. It cancels a different T-pose calibration
#: between the recording session and the live session. Press N during
#: the session to (re)capture the live neutral pose.
NEUTRAL_ALIGNMENT = _flag("NEUTRAL_ALIGNMENT", False)

#: Duration of the live neutral capture triggered by the N key.
NEUTRAL_CAPTURE_S = _number("NEUTRAL_CAPTURE_S", 2.0)


# ----------------------------------------------------------------------
# Reaching the target: tolerance, hysteresis, hold
# ----------------------------------------------------------------------

#: Angular error below which the pose counts as reached.
POSITION_TOLERANCE_DEG = _number("POSITION_TOLERANCE_DEG", 12.0)

#: Hysteresis: once inside, the pose stays valid until the error grows
#: past this larger value. Without it, an error hovering around the
#: tolerance would start and reset the timer many times per second.
EXIT_TOLERANCE_DEG = _number("EXIT_TOLERANCE_DEG", 18.0)

#: How long the pose must be held, continuously, before the next
#: movement starts.
HOLD_DURATION_S = _number("HOLD_DURATION_S", 5.0)


# ----------------------------------------------------------------------
# Haptic feedback
# ----------------------------------------------------------------------

#: How often a command is published while guiding.
HAPTIC_UPDATE_HZ = _number("HAPTIC_UPDATE_HZ", 10.0)

#: ON time of one vibration pulse, in milliseconds.
HAPTIC_PULSE_MS = int(_number("HAPTIC_PULSE_MS", 80))

#: Pulse rate. Like a parking sensor, the pulses get faster as the user
#: approaches the target: PULSE_HZ_MIN at a large error,
#: PULSE_HZ_MAX just outside the tolerance.
HAPTIC_PULSE_HZ_MIN = _number("HAPTIC_PULSE_HZ_MIN", 2.0)
HAPTIC_PULSE_HZ_MAX = _number("HAPTIC_PULSE_HZ_MAX", 8.0)

#: Motor power, 0..1. The minimum keeps the motor above its start
#: voltage; the firmware maps this range onto its own PWM floor.
HAPTIC_INTENSITY_MIN = _number("HAPTIC_INTENSITY_MIN", 0.35)
HAPTIC_INTENSITY_MAX = _number("HAPTIC_INTENSITY_MAX", 1.0)

#: Error at which the vibration reaches full intensity.
HAPTIC_FULL_INTENSITY_DEG = _number("HAPTIC_FULL_INTENSITY_DEG", 60.0)

#: Lifetime given to each command. The firmware stops the motors by
#: itself when no new command arrives within this delay, so a crash of
#: this program can never leave a motor running.
HAPTIC_HOLD_MS = int(_number("HAPTIC_HOLD_MS", 800))

#: The rotation the user must perform is split into a component around
#: the vertical axis (a left/right turn) and the rest. Below this many
#: degrees the vertical part is too small to give a direction.
DIRECTION_DEADBAND_DEG = _number("DIRECTION_DEADBAND_DEG", 3.0)

#: ... and it must also represent at least this fraction of the whole
#: error, otherwise the correction is mostly out of the horizontal
#: plane (bend, lift) and both motors pulse together instead of
#: pretending a side.
DIRECTION_DOMINANCE = _number("DIRECTION_DOMINANCE", 0.5)

#: The BNO055 "gravity" output follows the accelerometer sign
#: convention (ACC = LIA + GRV): a sensor lying flat with its Z axis
#: pointing up reads +9.81 on Z. The vector therefore points UP in the
#: sensor frame. Set to False only for a sensor library that returns
#: the opposite sign.
GRAVITY_VECTOR_POINTS_UP = _flag("GRAVITY_VECTOR_POINTS_UP", True)

#: Plausible magnitude of the gravity vector, m/s². Outside this range
#: the reading is not trusted and no side is chosen.
GRAVITY_MIN_MAGNITUDE = _number("GRAVITY_MIN_MAGNITUDE", 7.0)
GRAVITY_MAX_MAGNITUDE = _number("GRAVITY_MAX_MAGNITUDE", 12.0)

#: Master switch: False disables all vibration commands (useful when
#: no motors are wired yet).
HAPTICS_ENABLED = _flag("HAPTICS_ENABLED", True)


# ----------------------------------------------------------------------
# Optional trajectory score (never gates the progression)
# ----------------------------------------------------------------------

#: Compare the whole performed trajectory with the recorded one after
#: each movement, with dynamic time warping on the quaternion geodesic
#: distance. It is shown as a quality score only; the progression
#: criterion stays "final position + 5 second hold".
ENABLE_TRAJECTORY_SCORE = _flag("ENABLE_TRAJECTORY_SCORE", True)

#: Both trajectories are resampled to at most this many points before
#: the DTW, which bounds the cost of the O(n*m) algorithm.
DTW_MAX_POINTS = int(_number("DTW_MAX_POINTS", 120))


# ----------------------------------------------------------------------
# Terminal interface
# ----------------------------------------------------------------------

#: Screen refresh rate.
UI_REFRESH_HZ = _number("UI_REFRESH_HZ", 10.0)

#: How often the keyboard is polled, in seconds.
KEY_POLL_PERIOD_S = 0.02
