import tkinter as tk
from tkinter import ttk

import config
from vibration import update_vibration
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

root.title("MIDI Test Dual Hands")
root.geometry("420x300")
root.resizable(False, False)


# --------------- Tkinter variables ---------------


left_vibration = tk.BooleanVar(value=False)
right_vibration = tk.BooleanVar(value=False)


# --------------------- Title ---------------------


tk.Label(
    root,
    text="MIDI Test Dual Hands",
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


# --------------- Vibration controls --------------


tk.Checkbutton(
    root,
    text="Left vibration",
    variable=left_vibration,
    command=lambda: update_vibration(
        config.ESP32, 
        left_vibration.get(), 
        right_vibration.get()
    )
).pack()

tk.Checkbutton(
    root,
    text="Right vibration",
    variable=right_vibration,
    command=lambda: update_vibration(
        config.ESP32, 
        left_vibration.get(), 
        right_vibration.get()
    )
).pack()


# ---------------------- Notes --------------------


left_label = tk.Label(
    root,
    text="Left : --- | Octave : -",
    font=("Arial", 16)
)

left_label.pack(pady=20)

right_label = tk.Label(
    root,
    text="Right : --- | Octave : -",
    font=("Arial", 16)
)

right_label.pack()


# ------------------ Status bar -------------------


status = tk.Label(
    root,
    text="ESP32 Connected",
    fg="green"
)

status.pack(side="bottom", pady=15)