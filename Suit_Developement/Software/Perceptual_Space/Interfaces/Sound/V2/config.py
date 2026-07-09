# =================================================
# CONFIG
# =================================================


# -------------------- Network --------------------


ESP32 = "http://192.168.4.1"


# ---------------------- MIDI ---------------------


LEFT_CHANNEL = 0
RIGHT_CHANNEL = 1

VELOCITY = 120


# ---------------- Control Change -----------------


# MIDI Control Change numbers
CC_VOLUME = 7
CC_REVERB = 91


# -------------------- Drums ----------------------


DRUM_CHANNEL = 9

LEFT_DRUM = 38
RIGHT_DRUM = 36

PIEZO_THRESHOLD = 500
PIEZO_COOLDOWN = 0.10


# -------------------- Mapping --------------------


ANGLE_MIN = -90
ANGLE_MAX = 90

MIN_OCTAVE = 2
MAX_OCTAVE = 6