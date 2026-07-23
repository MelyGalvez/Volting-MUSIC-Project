# =================================================
# INTERFACE
#
# Tkinter front-end. Pure presentation: it renders
# EngineView snapshots and forwards user commands to
# the controller; no musical or network state lives
# here, and the audio path never runs through the Tk
# loop. All widget access happens on the Tk thread.
#
# The controller passed in must provide:
#   load_file(path)      advance_from_keyboard()
#   back()  restart()  panic()  set_mode(name)
# =================================================

import time
import tkinter as tk
from tkinter import filedialog, ttk


NOTE_NAMES = (
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
)


def midi_note_name(key):
    """MIDI 60 -> 'C4' (standard convention)."""
    key = max(0, min(127, int(key)))
    return f"{NOTE_NAMES[key % 12]}{key // 12 - 1}"


def _mmss(seconds):
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


class AppUI:

    def __init__(self, controller, *, gesture_sources,
                 mode_names, initial_mode, flash_s=0.18):
        self._controller = controller
        self._flash_s = flash_s

        self.root = tk.Tk()
        self.root.title("Sound_Track — MIDI Score Navigation")
        self.root.geometry("560x520")
        self.root.minsize(520, 480)

        self._build_header()
        self._build_progress()
        self._build_transport(mode_names, initial_mode)
        self._build_gestures(gesture_sources)
        self._build_status()
        self._bind_keys()

        self._seen_advances = None
        self._flash_until = {}

    # ------------------- Widgets ---------------------

    def _build_header(self):
        tk.Label(
            self.root,
            text="Sound_Track",
            font=("Arial", 18, "bold"),
        ).pack(pady=(12, 0))

        tk.Label(
            self.root,
            text="validated movements advance the score",
            font=("Arial", 9),
            fg="#666666",
        ).pack()

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=15, pady=(12, 4))

        tk.Button(
            frame, text="Open MIDI…", takefocus=0,
            command=self._pick_file,
        ).pack(side="left")

        self._score_name = tk.Label(
            frame, text="no score loaded", anchor="w",
            font=("Arial", 11, "bold"),
        )
        self._score_name.pack(side="left", padx=10)

        self._score_info = tk.Label(
            self.root, text="", anchor="w", fg="#444444",
        )
        self._score_info.pack(fill="x", padx=15)

    def _build_progress(self):
        frame = tk.LabelFrame(
            self.root, text="Position", padx=10, pady=8,
        )
        frame.pack(fill="x", padx=15, pady=(10, 4))

        self._bar = ttk.Progressbar(frame, maximum=1)
        self._bar.pack(fill="x")

        row = tk.Frame(frame)
        row.pack(fill="x", pady=(6, 0))

        self._position = tk.Label(
            row, text="—", font=("Consolas", 11), anchor="w",
        )
        self._position.pack(side="left")

        self._section = tk.Label(
            row, text="", fg="#666666", anchor="e",
        )
        self._section.pack(side="right")

        self._sounding = tk.Label(
            frame, text="", font=("Consolas", 11),
            anchor="w", fg="#005500",
        )
        self._sounding.pack(fill="x", pady=(4, 0))

    def _build_transport(self, mode_names, initial_mode):
        frame = tk.LabelFrame(
            self.root, text="Transport", padx=10, pady=8,
        )
        frame.pack(fill="x", padx=15, pady=4)

        tk.Button(
            frame, text="⟲ Restart", takefocus=0,
            command=self._controller.restart,
        ).pack(side="left")

        tk.Button(
            frame, text="◀ Back", takefocus=0,
            command=self._controller.back,
        ).pack(side="left", padx=(6, 0))

        tk.Button(
            frame, text="Advance ▶", takefocus=0,
            command=self._controller.advance_from_keyboard,
        ).pack(side="left", padx=(6, 0))

        tk.Button(
            frame, text="Panic", takefocus=0, fg="#aa0000",
            command=self._controller.panic,
        ).pack(side="right")

        tk.Label(frame, text="Release:").pack(
            side="left", padx=(16, 4)
        )

        self._mode = ttk.Combobox(
            frame, values=list(mode_names), width=9,
            state="readonly", takefocus=0,
        )
        self._mode.set(initial_mode)
        self._mode.pack(side="left")
        self._mode.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._controller.set_mode(
                self._mode.get()
            ),
        )

    def _build_gestures(self, sources):
        frame = tk.LabelFrame(
            self.root, text="Triggers", padx=10, pady=8,
        )
        frame.pack(fill="x", padx=15, pady=4)

        self._lamps = {}

        for source in (*sources, "keyboard"):
            cell = tk.Frame(frame)
            cell.pack(side="left", expand=True)

            lamp = tk.Canvas(
                cell, width=22, height=22, highlightthickness=0,
            )
            dot = lamp.create_oval(
                3, 3, 19, 19, fill="#cccccc", outline="#888888",
            )
            lamp.pack()

            tk.Label(
                cell, text=source.replace("_", " "),
                font=("Arial", 8),
            ).pack()

            self._lamps[source] = (lamp, dot)

        tk.Label(
            self.root,
            text="Space/→ advance · ← back · Home restart"
                 " · Esc panic",
            font=("Arial", 8), fg="#888888",
        ).pack()

    def _build_status(self):
        bar = tk.Frame(self.root)
        bar.pack(side="bottom", fill="x", padx=10, pady=6)

        self._midi_label = tk.Label(
            bar, text="", fg="#444444", anchor="w",
        )
        self._midi_label.pack(side="left")

        self._status = tk.Label(
            bar, text="Connecting…", fg="orange", anchor="e",
        )
        self._status.pack(side="right")

    def _bind_keys(self):
        advance = lambda _e: \
            self._controller.advance_from_keyboard()

        self.root.bind("<space>", advance)
        self.root.bind("<Right>", advance)
        self.root.bind(
            "<Left>", lambda _e: self._controller.back()
        )
        self.root.bind(
            "<Home>", lambda _e: self._controller.restart()
        )
        self.root.bind(
            "<Escape>", lambda _e: self._controller.panic()
        )

    # ---------------- User actions --------------------

    def _pick_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open MIDI file",
            filetypes=[
                ("MIDI files", "*.mid *.midi"),
                ("All files", "*.*"),
            ],
        )

        if path:
            self._controller.load_file(path)

    # ------------------- Updates ----------------------

    def set_midi_name(self, name):
        self._set(self._midi_label, f"MIDI out: {name}")

    def show_loading(self, path):
        self._set(self._score_name, "Loading…")
        self._set(self._score_info, path)

    def show_score(self, score):
        self._set(self._score_name, score.name)

        tracks = sum(1 for t in score.track_names) or 1
        self._set(
            self._score_info,
            f"{score.total_steps} steps · "
            f"{score.note_count} notes · "
            f"{_mmss(score.duration_s)} nominal · "
            f"{tracks} tracks · "
            f"channels {sorted(score.channels)}",
        )

        self._bar.configure(maximum=max(1, score.total_steps))

    def show_load_error(self, message):
        self._set(self._score_name, "load failed")
        self._set(self._score_info, message)

    def set_status(self, text, color):
        if self._status.cget("text") != text:
            self._status.config(text=text, fg=color)

    def refresh(self, view):
        """
        Render one EngineView snapshot (called from the Tk
        after-loop at the UI rate).
        """

        now = time.monotonic()

        # Position ------------------------------------
        if view.total_steps:
            self._bar["value"] = view.next_index

            if view.finished:
                position = (
                    f"finished ({view.total_steps} steps)"
                    " — Restart or Back"
                )
            elif view.next_index >= view.total_steps:
                position = "last step played — next" \
                    " gesture cuts off"
            else:
                position = (
                    f"next step {view.next_index + 1}"
                    f" / {view.total_steps}"
                )

            if view.rate is not None:
                position += f"   pace ×{view.rate:.2f}"
        else:
            self._bar["value"] = 0
            position = "—"

        self._set(self._position, position)

        section = view.next_label or view.section or ""
        self._set(
            self._section, f"· {section}" if section else ""
        )

        # Sounding notes -------------------------------
        if view.sounding:
            names = " ".join(
                midi_note_name(key)
                for _ch, key in view.sounding[:10]
            )
            if len(view.sounding) > 10:
                names += f" (+{len(view.sounding) - 10})"
        else:
            names = "silence" if view.total_steps else ""

        self._set(self._sounding, names)

        # Trigger lamps --------------------------------
        if self._seen_advances is None:
            self._seen_advances = view.advance_count
        elif view.advance_count != self._seen_advances:
            self._seen_advances = view.advance_count
            if view.last_source in self._lamps:
                self._flash_until[view.last_source] = \
                    now + self._flash_s

        for source, (lamp, dot) in self._lamps.items():
            lit = self._flash_until.get(source, 0.0) > now
            lamp.itemconfigure(
                dot, fill="#33cc33" if lit else "#cccccc",
            )

    @staticmethod
    def _set(label, text):
        if label.cget("text") != text:
            label.config(text=text)
