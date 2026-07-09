import tkinter as tk
from tkinter import ttk

from names import DRUMS


# =================================================
# INTERFACE
# =================================================


# ---------------- Instrument list ----------------


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


# ------------------ Main window ------------------


root = tk.Tk()

root.title("Body Motion MIDI")
root.geometry("470x600")
root.resizable(False, False)


# ---------------------- Title --------------------


tk.Label(
    root,
    text="Body Motion MIDI",
    font=("Arial", 18, "bold")
).pack(pady=10)


# ---------------- Left instrument ----------------


tk.Label(
    root,
    text="Left Instrument"
).pack()

left_combo = ttk.Combobox(
    root,
    values=list(INSTRUMENTS.keys()),
    state="readonly",
    width=30
)

left_combo.current(0)
left_combo.pack()


# ---------------- Right instrument ---------------


tk.Label(
    root,
    text="Right Instrument"
).pack(pady=(10, 0))

right_combo = ttk.Combobox(
    root,
    values=list(INSTRUMENTS.keys()),
    state="readonly",
    width=30
)

right_combo.current(2)
right_combo.pack()


# ---------------- Left drum ----------------------


tk.Label(
    root,
    text="Left Drum"
).pack(pady=(10, 0))

left_drum_combo = ttk.Combobox(
    root,
    values=list(DRUMS.keys()),
    state="readonly",
    width=30
)

left_drum_combo.set("Snare")
left_drum_combo.pack()


# ---------------- Right drum ---------------------


tk.Label(
    root,
    text="Right Drum"
).pack(pady=(10, 0))

right_drum_combo = ttk.Combobox(
    root,
    values=list(DRUMS.keys()),
    state="readonly",
    width=30
)

right_drum_combo.set("Kick")
right_drum_combo.pack()


# ---------------- Left status --------------------


left_frame = tk.LabelFrame(
    root,
    text="Left Instrument",
    padx=10,
    pady=10
)

left_frame.pack(
    fill="x",
    padx=15,
    pady=(20, 10)
)

left_label = tk.Label(
    left_frame,
    justify="left",
    anchor="w",
    font=("Consolas", 11),
    text=
    "Note     : ---\n"
    "Octave   : -\n"
    "Volume   : -\n"
    "Reverb   : -"
)

left_label.pack(anchor="w")


# ---------------- Right status -------------------


right_frame = tk.LabelFrame(
    root,
    text="Right Instrument",
    padx=10,
    pady=10
)

right_frame.pack(
    fill="x",
    padx=15,
    pady=(0, 10)
)

right_label = tk.Label(
    right_frame,
    justify="left",
    anchor="w",
    font=("Consolas", 11),
    text=
    "Note     : ---\n"
    "Octave   : -\n"
    "Volume   : -\n"
    "Reverb   : -"
)

right_label.pack(anchor="w")


# ------------------ Status bar -------------------


status = tk.Label(
    root,
    text="ESP32 Connected",
    fg="green"
)

status.pack(
    side="bottom",
    pady=10
)