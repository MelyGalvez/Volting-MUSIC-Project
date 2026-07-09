import time
import config


# =================================================
# MAPPING
# =================================================


# ---------------- Utility functions --------------


def clamp(x: float, a: float, b: float) -> float:
    """
    Clamp a value between a minimum and a maximum.
    """

    return max(a, min(b, x))


# ---------------- Octave mapping -----------------


def map_octave(angle: float) -> int:
    """
    Convert the back angle into a MIDI octave.
    """

    angle = clamp(
        angle,
        config.ANGLE_MIN,
        config.ANGLE_MAX
    )

    ratio = (
        angle - config.ANGLE_MIN
    ) / (
        config.ANGLE_MAX - config.ANGLE_MIN
    )

    octave = int(
        ratio * (
            config.MAX_OCTAVE -
            config.MIN_OCTAVE
        )
    )

    return octave + config.MIN_OCTAVE


# ----------------- Note mapping ------------------


SCALE = [
    0,   # C
    2,   # D
    4,   # E
    5,   # F
    7,   # G
    9,   # A
    11,  # B
    12   # C
]


def map_note(angle: float) -> int:
    """
    Convert the arm angle into a note of a C major scale.
    """

    angle = clamp(
        angle,
        config.ANGLE_MIN,
        config.ANGLE_MAX
    )

    ratio = (
        angle - config.ANGLE_MIN
    ) / (
        config.ANGLE_MAX - config.ANGLE_MIN
    )

    index = int(
        ratio * (len(SCALE) - 1)
    )

    return SCALE[index]


# --------------- Volume mapping ------------------


def map_volume(angle: float) -> int:
    """
    Convert the wrist angle into MIDI volume (0-127).
    """

    angle = clamp(
        angle,
        config.ANGLE_MIN,
        config.ANGLE_MAX
    )

    ratio = (
        angle - config.ANGLE_MIN
    ) / (
        config.ANGLE_MAX - config.ANGLE_MIN
    )

    return int(ratio * 127)


# -------------- Reverb mapping -------------------


def map_reverb(angle: float) -> int:
    """
    Convert the forearm angle into MIDI reverb (0-127).
    """

    angle = clamp(
        angle,
        config.ANGLE_MIN,
        config.ANGLE_MAX
    )

    ratio = (
        angle - config.ANGLE_MIN
    ) / (
        config.ANGLE_MAX - config.ANGLE_MIN
    )

    return int(ratio * 127)


# ---------------- MIDI conversion ----------------


def build_midi_note(
    octave: int,
    note: int
) -> int:
    """
    Build a MIDI note number.
    """

    return octave * 12 + note


# --------------- Piezo percussion ----------------


last_left_hit = 0
last_right_hit = 0


def detect_left_hit(value: float) -> bool:
    """
    Detect a hit on the left piezo.
    """

    global last_left_hit

    if value < config.PIEZO_THRESHOLD:
        return False

    t = time.time()

    if t - last_left_hit < config.PIEZO_COOLDOWN:
        return False

    last_left_hit = t

    return True


def detect_right_hit(value: float) -> bool:
    """
    Detect a hit on the right piezo.
    """

    global last_right_hit

    if value < config.PIEZO_THRESHOLD:
        return False

    t = time.time()

    if t - last_right_hit < config.PIEZO_COOLDOWN:
        return False

    last_right_hit = t

    return True