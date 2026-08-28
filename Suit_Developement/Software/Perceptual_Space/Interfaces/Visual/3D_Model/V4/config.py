# ==========================================
# CONFIG
# ==========================================


# ---------------- Skeleton ----------------


TORSO_LENGTH = 0.6

LOWER_BACK_LENGTH = 0.4

UPPER_ARM_LENGTH = 0.35

FOREARM_LENGTH = 0.30

HAND_LENGTH = 0.15

HEAD_RADIUS = 0.12

SHOULDER_OFFSET = 0.25


# ----------------- Network ----------------


MQTT_BROKER_HOST = "192.168.56.1"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "motion_suit/data"

MQTT_QOS = 0

MQTT_KEEPALIVE_S = 30

MQTT_RECONNECT_MIN_S = 1
MQTT_RECONNECT_MAX_S = 30

STALE_AFTER = 1.0


# --- Orientation filtering / robustness ---


FILTER_TIME_CONSTANT = 0.05

FILTER_MAX_RATE_DPS = 1200.0

FILTER_MAX_REJECTS = 8


# ---------------- Recording ---------------


# Flush the CSV at most once per second: flushing after
# every frame (previous behaviour) forces a syscall per
# frame on the render thread.
RECORDER_FLUSH_PERIOD_S = 1.0