# =================================================
# NAMES
# =================================================


# ------------------ Note names -------------------


NOTE_NAMES = [
    "C","C#","D","D#","E","F",
    "F#","G","G#","A","A#","B"
]


# ---------------- Drum names ---------------------


DRUMS = {
    "Kick":36,
    "Snare":38,
    "Side Stick":37,
    "Clap":39,
    "Closed HiHat":42,
    "Open HiHat":46,
    "Crash":49,
    "Ride":51,
    "Cowbell":56,
    "Tambourine":54
}


# ---------------- Utility functions --------------


def midi_name(note: int) -> str:
    """
    Convert a MIDI note number into its musical name.
    """

    octave = note // 12 - 1

    return f"{NOTE_NAMES[note % 12]}{octave}"