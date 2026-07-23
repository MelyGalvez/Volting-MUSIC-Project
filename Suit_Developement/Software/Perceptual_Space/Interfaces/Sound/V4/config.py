# =================================================
# CONFIG
#
# Every tunable constant of the Sound_Track
# application. Each value documents why it was
# chosen. Nothing outside this file needs editing
# for normal retuning (sensor remounts, gesture
# sensitivity, MIDI routing, playback behavior).
# =================================================


# -------------------- Network --------------------


ESP32_BASE_URL = "http://192.168.4.1"

# Per-request timeout. The ESP32 answers from a snapshot
# cache in a few ms; 0.5 s only ever triggers on real
# network trouble.
HTTP_TIMEOUT_S = 0.5

# Polling rate of the background client. The firmware's
# piezo hit counters make the polling rate irrelevant for
# *detection* (no hit is ever lost); it only bounds the
# trigger latency (mean latency = half the poll period).
# 100 Hz keeps the mean network latency at 5 ms. Reduce to
# 50 if the Visual application polls concurrently and the
# WiFi channel is busy.
POLL_HZ = 100

# After a failed request the poller backs off between
# these bounds (doubling), so a rebooting ESP32 is not
# hammered while it recovers.
ERROR_BACKOFF_MIN_S = 0.1
ERROR_BACKOFF_MAX_S = 1.0

# When no fresh packet arrived for this long, sounding
# notes are silenced (score position is preserved so the
# performance resumes where it stopped).
STALE_AFTER_S = 0.5


# ------------------- MIDI output ------------------


# Backend selection:
#   "auto"   - winmm on Windows (zero dependencies),
#              pygame elsewhere (if installed).
#   "winmm"  - force the Windows Multimedia backend.
#   "pygame" - force pygame.midi (requires pygame).
MIDI_BACKEND = "auto"

# Output device: None selects the system default.
# An int selects a device id, a string selects the first
# device whose name contains it (case-insensitive), e.g.
# "loopMIDI" to route into a DAW.
MIDI_DEVICE = None


# ------------------ Score loading -----------------


# Note onsets closer together than this are considered one
# chord (one navigation step). Human-recorded MIDI spreads
# chord notes over 10-30 ms; 30 ms groups those without
# swallowing genuine fast runs (a 32nd note at 120 BPM is
# 62 ms away). Grouping is anchored at the first onset of
# the group so long arpeggio chains never chain-merge.
CHORD_WINDOW_S = 0.030

# Restrict loading to these MIDI channels (0-15) or track
# indices. None = everything. Example: exclude the GM
# percussion channel with CHANNEL_FILTER = set(range(16)) - {9}.
CHANNEL_FILTER = None
TRACK_FILTER = None


# ------------------- Navigation --------------------


# Two accepted advances closer together than this are
# collapsed into one. This is the single guard against
# double triggers (a piezo strike also swings the arm) and
# against keyboard auto-repeat. 80 ms still allows 12.5
# steps/s, beyond realistic gesture rates.
ADVANCE_REFRACTORY_S = 0.080

# What happens when the performer advances past the final
# cutoff: True restarts the piece seamlessly, False stays
# on "finished" until Restart.
LOOP_AT_END = True

# Release mode selected at startup (the UI can switch):
#   "sustain" - notes sound until the musical position
#               passes their written end. Fully
#               deterministic, no clocks: the same gesture
#               sequence always produces the same output.
#   "timed"   - note durations follow the file, scaled by
#               the performer's current pace, so staccato
#               stays staccato even between slow gestures.
RELEASE_MODE = "sustain"


# ----------------- Velocity policy ------------------


# How note velocities are produced:
#   "file"    - use the velocities written in the file.
#   "gesture" - ignore the file; movement strength alone
#               sets the dynamics around VELOCITY_BASE.
#   "blend"   - file velocity scaled by movement strength:
#               strength 0 -> VELOCITY_FLOOR_SCALE x file,
#               strength 1 -> 1.0 x file. Keeps the score's
#               phrasing while the performer shapes it.
VELOCITY_MODE = "blend"

# "blend": fraction of the file velocity kept at zero
# movement strength.
VELOCITY_FLOOR_SCALE = 0.45

# "gesture": velocity spans this range with strength.
VELOCITY_BASE_MIN = 10
VELOCITY_BASE_MAX = 127


# ------------------- Timed mode ---------------------


# The performer's pace (file-seconds per wall-second) is
# estimated from the gaps between recent gestures with an
# exponential moving average. Higher alpha follows tempo
# changes faster but is more nervous.
TIMED_RATE_ALPHA = 0.4

# Instantaneous pace estimates are clamped into this range
# (x nominal file tempo) so one hesitation or one double
# hit cannot produce absurd durations.
TIMED_RATE_MIN = 0.2
TIMED_RATE_MAX = 5.0

# Scheduled note lengths are clamped into this range.
TIMED_MIN_GATE_S = 0.05
TIMED_MAX_HOLD_S = 10.0


# ---------------- Gesture triggers ------------------
#
# Every trigger source maps to a navigation action.
# Available actions: "advance", "back", "off".
# Sources: the two firmware piezo strikers and one swing
# detector per arm. Keyboard/UI triggers are always
# active (Space/Right = advance, Left = back).

GESTURE_MAP = {
    "piezo_left":  "advance",
    "piezo_right": "advance",
    "swing_left":  "advance",
    "swing_right": "advance",
}

# Movement strength assigned to keyboard / UI-button
# advances (no physical energy to measure).
KEYBOARD_STRENGTH = 0.8


# Piezo hits: the firmware reports the ADC peak of each
# detected hit; peaks map linearly from the firmware
# trigger threshold to full scale onto strength 0..1.
PIEZO_PEAK_FLOOR = 500
PIEZO_PEAK_CEIL = 4095


# Swing detectors: a validated movement is a fast angular
# crossing of a trigger plane (Schmitt trigger + speed
# gate + refractory). Angles are degrees, T-pose relative,
# in each sensor's calibration frame; the field/sign
# assignments follow the documented IMU mounting (same
# conventions as Sound_V2: arm raise = "roll", the right
# arm sensor is mounted mirrored, hence the opposite sign).
SWING_TRIGGERS = {
    "swing_left": dict(
        body="left_arm",
        field="roll",
        sign=1.0,
        fire_deg=35.0,       # crossing this angle fires...
        rearm_deg=20.0,      # ...after coming back below this
        min_speed_dps=60.0, # slower crossings are posture, not gesture
        full_speed_dps=600.0,# speed mapped to strength 1.0
        refractory_ms=150,   # device-time lockout per arm
    ),
    "swing_right": dict(
        body="right_arm",
        field="roll",
        sign=1.0,
        fire_deg=20.0,
        rearm_deg=10.0,
        min_speed_dps=60.0,
        full_speed_dps=600.0,
        refractory_ms=150,
    ),
}

# Frame-to-frame angle jumps above this are sensor
# glitches or heading wraps, not motion (a human arm does
# not move 90 deg in one 10-20 ms frame); the detector
# resynchronizes instead of firing.
SWING_MAX_STEP_DEG = 90.0

# Gaps in the device timeline above this (dropped frames,
# reconnect) resynchronize the detector state.
SWING_MAX_GAP_MS = 250


# ---------------------- UI --------------------------


# UI refresh period (Tk after-loop). The UI only displays
# engine state; 33 ms = 30 Hz is smooth and cheap. The
# audio path does not run through the UI loop.
UI_TICK_MS = 33

# How long a gesture indicator stays lit after a trigger.
UI_FLASH_S = 0.18

# Path preloaded into the file picker. None = none.
DEFAULT_MIDI_PATH = None
