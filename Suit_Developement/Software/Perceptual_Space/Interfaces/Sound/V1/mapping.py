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

    return max(a,min(b,x))


# ---------------- Octave mapping -----------------


def map_octave(pitch: float) -> int:
    """
    Convert the hand pitch angle into a MIDI octave.
    """

    pitch=clamp(pitch,-90,90)

    octave=int((pitch+90)/180*4)

    return octave+2


# ----------------- Note mapping ------------------


def map_note(roll: float) -> int:
    """
    Convert the wrist roll angle into a MIDI note.
    """

    roll=clamp(roll,-90,90)

    scale=[0,2,4,5,7,9,11,12]

    index=int((roll+90)/180*(len(scale)-1))

    return scale[index]


# ---------------- MIDI conversion ----------------


def build_midi_note(octave: int, note: int) -> int:
    """
    Build the MIDI note number from an octave and a note.
    """

    return octave*12+note


# --------------- Piezo percussion ----------------


last_left_hit = 0
last_right_hit = 0

def detect_left_hit(value):

    global last_left_hit

    if value < config.PIEZO_THRESHOLD:
        return False

    t = time.time()

    if t-last_left_hit < config.PIEZO_COOLDOWN:
        return False

    last_left_hit = t

    return True

def detect_right_hit(value):

    global last_right_hit

    if value < config.PIEZO_THRESHOLD:
        return False

    t = time.time()

    if t-last_right_hit < config.PIEZO_COOLDOWN:
        return False

    last_right_hit = t

    return True