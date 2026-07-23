# =================================================
# NAMES
#
# Musical naming data (notes, GM instruments, GM
# percussion). Pure data, no side effects.
# =================================================


# ------------------ Note names -------------------


NOTE_NAMES = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]


# --------------- Instrument names ----------------
# General MIDI program numbers.


INSTRUMENTS = {
    "Piano": 0,
    "Guitar": 24,
    "Violin": 40,
    "Trumpet": 56,
    "Flute": 73,
    "Choir": 52,
    "Synth Pad": 89,
    "FX Goblins": 102
}


# ---------------- Drum names ---------------------
# General MIDI percussion key numbers (channel 10).


DRUMS = {
    "Kick": 36,
    "Snare": 38,
    "Side Stick": 37,
    "Clap": 39,
    "Closed HiHat": 42,
    "Open HiHat": 46,
    "Crash": 49,
    "Ride": 51,
    "Cowbell": 56,
    "Tambourine": 54
}


# ---------------- Utility functions --------------


def midi_name(note: int) -> str:
    """
    Convert a MIDI note number into its musical name.

    Uses the standard convention where MIDI 60 is C4.
    Out-of-range values are clamped so a corrupt note
    number can never crash the display path.
    """

    note = max(0, min(127, int(note)))

    octave = note // 12 - 1

    return f"{NOTE_NAMES[note % 12]}{octave}"
