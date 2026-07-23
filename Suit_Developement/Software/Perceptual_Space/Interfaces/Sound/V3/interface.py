# =================================================
# INTERFACE
#
# Tkinter user interface. A class with explicit
# construction: importing this module no longer
# creates a window as a side effect. All widget
# access happens from the Tk main thread.
# =================================================

import tkinter as tk
from tkinter import ttk

from names import DRUMS, INSTRUMENTS


class AppUI:
    """
    Builds the window and exposes:

      - selected instrument / drum names
      - display setters for both voices
      - a real connection status indicator (the previous
        version displayed a hardcoded "ESP32 Connected")
    """

    def __init__(self):
        self.root = tk.Tk()

        self.root.title("Body Motion MIDI")
        self.root.geometry("470x600")
        self.root.resizable(False, False)

        self._build_title()
        self._build_selectors()
        self._build_status_frames()
        self._build_status_bar()


# -------------------- Widgets ---------------------


    def _build_title(self):
        tk.Label(
            self.root,
            text="Body Motion MIDI",
            font=("Arial", 18, "bold"),
        ).pack(pady=10)

    def _make_combo(self, label, values, default):
        tk.Label(self.root, text=label).pack(pady=(10, 0))

        combo = ttk.Combobox(
            self.root,
            values=values,
            state="readonly",
            width=30,
        )
        combo.set(default)
        combo.pack()

        return combo

    def _build_selectors(self):
        instrument_names = list(INSTRUMENTS.keys())
        drum_names = list(DRUMS.keys())

        self.left_combo = self._make_combo(
            "Left Instrument", instrument_names,
            instrument_names[0],
        )

        self.right_combo = self._make_combo(
            "Right Instrument", instrument_names,
            instrument_names[2],
        )

        self.left_drum_combo = self._make_combo(
            "Left Drum", drum_names, "Snare",
        )

        self.right_drum_combo = self._make_combo(
            "Right Drum", drum_names, "Kick",
        )

    def _make_status_frame(self, title, pady):
        frame = tk.LabelFrame(
            self.root, text=title, padx=10, pady=10,
        )
        frame.pack(fill="x", padx=15, pady=pady)

        label = tk.Label(
            frame,
            justify="left",
            anchor="w",
            font=("Consolas", 11),
            text=(
                "Note     : ---\n"
                "Octave   : -\n"
                "Volume   : -\n"
                "Reverb   : -"
            ),
        )
        label.pack(anchor="w")

        return label

    def _build_status_frames(self):
        self.left_label = self._make_status_frame(
            "Left Instrument", (20, 10)
        )
        self.right_label = self._make_status_frame(
            "Right Instrument", (0, 10)
        )

    def _build_status_bar(self):
        self.status = tk.Label(
            self.root,
            text="Connecting...",
            fg="orange",
        )
        self.status.pack(side="bottom", pady=10)


# ------------------- Accessors --------------------


    def left_instrument(self):
        return INSTRUMENTS.get(self.left_combo.get(), 0)

    def right_instrument(self):
        return INSTRUMENTS.get(self.right_combo.get(), 0)

    def left_drum(self):
        return DRUMS.get(self.left_drum_combo.get(), 38)

    def right_drum(self):
        return DRUMS.get(self.right_drum_combo.get(), 36)


# -------------------- Updates ---------------------


    def set_status(self, text, color):
        if self.status.cget("text") != text:
            self.status.config(text=text, fg=color)

    def set_side(self, side, note_name, octave, volume, reverb):
        label = self.left_label if side == "left" \
            else self.right_label

        text = (
            f"Note     : {note_name}\n"
            f"Octave   : {octave}\n"
            f"Volume   : {volume}\n"
            f"Reverb   : {reverb}"
        )

        if label.cget("text") != text:
            label.config(text=text)
