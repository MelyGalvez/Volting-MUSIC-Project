# ================================================
# CONFIG
#
# Every tunable constant of the Visual application.
# ================================================


# ------------------ Skeleton ---------------------


TORSO_LENGTH = 0.6

LOWER_BACK_LENGTH = 0.4

UPPER_ARM_LENGTH = 0.35

FOREARM_LENGTH = 0.30

HAND_LENGTH = 0.15

HEAD_RADIUS = 0.12

SHOULDER_OFFSET = 0.25


# --------------------- Network -------------------


ESP32_IP = "192.168.4.1"

# Per-request timeout; the firmware answers from cache in
# a few ms, so anything longer than this is real trouble.
NETWORK_TIMEOUT = 0.5

# Background polling rate. 60 Hz matches the render rate;
# polling faster only rereads the same 100 Hz snapshot and
# loads the ESP32 for nothing.
POLL_HZ = 60

# After a failed request the poller backs off between
# these bounds (doubling) instead of hammering a
# rebooting ESP32.
ERROR_BACKOFF_MIN_S = 0.1
ERROR_BACKOFF_MAX_S = 1.0

# Data older than this freezes the skeleton (hold last
# pose) and flags the UI as stale.
STALE_AFTER = 0.4


# ------- Orientation filtering / robustness ------


# Exponential smoothing time constant (seconds). The
# BNO055 output is already fusion-filtered, so heavy
# smoothing only adds lag: 0.05 s keeps residual jitter
# invisible while cutting perceived latency vs the
# previous 0.12 s.
FILTER_TIME_CONSTANT = 0.05

# Angular-rate plausibility gate. Fast intentional hand
# moves reach well above 1000 deg/s; isolated jumps above
# this rate are treated as glitches. Two consecutive
# consistent samples are accepted immediately (real motion
# is continuous), so the gate adds no lag to real moves.
FILTER_MAX_RATE_DPS = 1200.0

# Consecutive rejections before the filter force-accepts,
# guaranteeing convergence even after a true teleport
# (e.g. recalibration while moving).
FILTER_MAX_REJECTS = 8


# ------------------ Recording --------------------


# Flush the CSV at most once per second: flushing after
# every frame (previous behaviour) forces a syscall per
# frame on the render thread.
RECORDER_FLUSH_PERIOD_S = 1.0
