# =================================================
# CONFIG
#
# Every tunable constant of the Sound application.
# Each value documents why it was chosen.
# =================================================


# -------------------- Network --------------------


ESP32_BASE_URL = "http://192.168.4.1"

# Per-request timeout. The ESP32 answers from a snapshot
# cache in a few ms; 0.5 s only ever triggers on real
# network trouble instead of freezing the UI for 10 s as
# the previous timeout did.
HTTP_TIMEOUT_S = 0.5

# Polling rate of the background client. 50 Hz gives a
# 20 ms control period (imperceptible for continuous MIDI
# controls) while keeping ESP32 load moderate alongside
# the Visual application.
POLL_HZ = 50

# After a failed request the poller backs off between
# these bounds (doubling), so a rebooting ESP32 is not
# hammered while it recovers.
ERROR_BACKOFF_MIN_S = 0.1
ERROR_BACKOFF_MAX_S = 1.0

# When no fresh packet arrived for this long, every voice
# is silenced instead of holding the last note forever.
STALE_AFTER_S = 0.5


# --------------------- Timing --------------------


# Main application tick (Tk after-loop). 20 ms = 50 Hz,
# matched to the polling rate.
TICK_MS = 20

# Console status line refresh period.
CONSOLE_PERIOD_S = 0.1


# ---------------------- MIDI ---------------------


LEFT_CHANNEL = 0
RIGHT_CHANNEL = 1
DRUM_CHANNEL = 9          # GM percussion channel

NOTE_VELOCITY = 120

# Preferred pygame.midi output device id. None selects the
# system default output automatically (the previous
# hardcoded id 1 crashed on machines where device 1 is not
# an output).
MIDI_DEVICE_ID = None

# Gate time of a triggered drum note.
DRUM_GATE_S = 0.02


# ---------------- Control Change -----------------


CC_VOLUME = 7
CC_REVERB = 91

# Continuous controls quantized from noisy angles flap by
# +-1 step at rest; a change smaller than this many CC
# steps is not transmitted (endpoints 0/127 always pass).
CC_MIN_DELTA = 2


# ------------- Piezo velocity mapping ------------


# Firmware reports the ADC peak of each detected hit
# (see PROTOCOL.md). Peaks map linearly from the firmware
# trigger threshold to full scale onto this velocity range.
PIEZO_PEAK_FLOOR = 500
PIEZO_PEAK_CEIL = 4095

VELOCITY_MIN = 40
VELOCITY_MAX = 127

# Fallback threshold when talking to a firmware that only
# sends raw piezo values (no hit counters).
PIEZO_THRESHOLD = 500
PIEZO_COOLDOWN_S = 0.10


# -------------------- Mapping --------------------
#
# All angles are degrees, T-pose relative, in each
# sensor's own calibration frame (aerospace convention:
# roll = about X, pitch = about Y, heading = about Z).
# Which anatomical motion lands on which axis depends on
# how each IMU is mounted; the field/sign constants below
# are derived from the documented mounting directions and
# are the single place to retune if a sensor is remounted.


# Octave: torso lean (rotation about the body left-right
# axis = sensor X of the back IMUs -> "roll").
# +-45 deg instead of the previous +-90: a performer
# cannot lean +-90 deg, so the old range compressed all
# octaves into a small usable arc.
OCTAVE_FIELD = "roll"
OCTAVE_SIGN = 1.0
OCTAVE_ANGLE_RANGE = (-45.0, 45.0)
MIN_OCTAVE = 2
MAX_OCTAVE = 6

# Notes: arm raise (rotation about the body forward axis =
# sensor X of the arm IMUs -> "roll"). The right arm
# sensor is mounted mirrored, hence the opposite sign.
NOTE_FIELD = "roll"
NOTE_SIGN_LEFT = 1.0
NOTE_SIGN_RIGHT = -1.0
NOTE_ANGLE_RANGE = (-90.0, 90.0)

# Volume: hand pronation (rotation about the arm long
# axis = sensor Y of the hand IMUs -> "pitch").
VOLUME_FIELD = "pitch"
VOLUME_SIGN_LEFT = 1.0
VOLUME_SIGN_RIGHT = -1.0
VOLUME_ANGLE_RANGE = (-90.0, 90.0)

# Reverb: elbow flexion (rotation about the vertical axis
# = sensor Z of the forearm IMUs -> "heading").
REVERB_FIELD = "heading"
REVERB_SIGN_LEFT = 1.0
REVERB_SIGN_RIGHT = -1.0
REVERB_ANGLE_RANGE = (-90.0, 90.0)


# ------------------ Hysteresis --------------------
#
# Without hysteresis, an arm resting exactly on a note
# boundary retriggers notes continuously (audible flutter).
# The selected bin only changes once the angle moves this
# many degrees past the boundary.

NOTE_HYSTERESIS_DEG = 4.0
OCTAVE_HYSTERESIS_DEG = 5.0
