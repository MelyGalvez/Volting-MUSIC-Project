# ================================================
# CONFIG
# ================================================


TORSO_LENGTH = 0.6

UPPER_ARM_LENGTH = 0.35

FOREARM_LENGTH = 0.30

HAND_LENGTH = 0.15

HEAD_RADIUS = 0.12


# --------------------- Network -------------------


ESP32_IP = "192.168.4.1"

NETWORK_TIMEOUT = 0.5

STALE_AFTER = 0.4


# ------- Orientation filtering / robustness ------


FILTER_TIME_CONSTANT = 0.12

FILTER_MAX_RATE_DPS = 1200.0

FILTER_MAX_REJECTS = 8