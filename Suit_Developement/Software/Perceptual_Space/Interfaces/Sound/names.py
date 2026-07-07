# =================================================
# NAMES
# =================================================


# ------------------ Note names -------------------


NOTE_NAMES = [
"C","C#","D","D#","E","F",
"F#","G","G#","A","A#","B"
]


# ---------------- Utility functions --------------


def midi_name(note: int) -> str:
    """
    Convert a MIDI note number into its musical name.
    """

    octave = note//12-1

    return f"{NOTE_NAMES[note%12]}{octave}"