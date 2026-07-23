# =================================================
# MAIN — Sound_Track
#
# Interactive MIDI score navigation: the performer's
# validated movements advance through a preloaded
# MIDI file; the file decides *what* sounds, the
# body decides *when*.
#
# This is the composition root: it owns process
# lifecycle and wires the layers together —
#
#   SuitClient (poll thread)
#     └─ on new frame ─▶ GestureRouter ─▶ engine.advance()
#   Ticker (2.5 ms thread)
#     ├─ engine.process()      scheduled note releases
#     └─ watchdog              silence on stale/not-ready
#   Tk main thread
#     ├─ AppUI                 display + keyboard triggers
#     └─ 30 Hz refresh of EngineView snapshots
#
# Threading rule: the engine serializes everything
# behind its own lock; the UI never blocks on the
# network and the audio path never runs through Tk.
#
# CLI:
#   python main.py [file.mid]      run (optionally autoload)
#   python main.py --check [file]  headless verification
#   python main.py --list-devices  show MIDI outputs
# =================================================

import argparse
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import config
from engine import (
    GestureEvent,
    NavigationEngine,
    Ticker,
    make_release_mode,
    make_velocity_policy,
)
from inputs import (
    GestureRouter,
    PiezoHitDetector,
    SuitClient,
    SwingDetector,
)
from midiout import MidiOut, MidiPortError, open_port
from midiout.ports import describe_devices
from score import ScoreError, load_score
from ui import AppUI


RUNNING_STATES = ("ready", "degraded")

MODE_NAMES = ("sustain", "timed")


# ------------------ Construction -------------------


def build_detectors():
    detectors = [
        PiezoHitDetector(
            "piezo_left", "left",
            peak_floor=config.PIEZO_PEAK_FLOOR,
            peak_ceil=config.PIEZO_PEAK_CEIL,
        ),
        PiezoHitDetector(
            "piezo_right", "right",
            peak_floor=config.PIEZO_PEAK_FLOOR,
            peak_ceil=config.PIEZO_PEAK_CEIL,
        ),
    ]

    for source, params in config.SWING_TRIGGERS.items():
        detectors.append(SwingDetector(
            source,
            max_step_deg=config.SWING_MAX_STEP_DEG,
            max_gap_ms=config.SWING_MAX_GAP_MS,
            **params,
        ))

    return detectors


class SoundTrackApp:
    """
    Controller: owns every component and implements the
    commands the UI and keyboard invoke. All navigation
    calls funnel into the (thread-safe) engine.
    """

    def __init__(self):
        port = open_port(config.MIDI_BACKEND, config.MIDI_DEVICE)
        self.midi = MidiOut(port)
        print(f"MIDI output: {self.midi.name}")

        self.engine = NavigationEngine(
            self.midi,
            make_release_mode(config.RELEASE_MODE, config),
            make_velocity_policy(
                config.VELOCITY_MODE,
                floor_scale=config.VELOCITY_FLOOR_SCALE,
                base_min=config.VELOCITY_BASE_MIN,
                base_max=config.VELOCITY_BASE_MAX,
            ),
            refractory_s=config.ADVANCE_REFRACTORY_S,
            loop_at_end=config.LOOP_AT_END,
        )

        self.router = GestureRouter(
            build_detectors(), config.GESTURE_MAP
        )

        self.client = SuitClient(
            config.ESP32_BASE_URL,
            timeout_s=config.HTTP_TIMEOUT_S,
            poll_hz=config.POLL_HZ,
            backoff_min_s=config.ERROR_BACKOFF_MIN_S,
            backoff_max_s=config.ERROR_BACKOFF_MAX_S,
            on_frame=self._on_frame,
        )

        self.ticker = Ticker(
            self.engine, housekeeping=self._watchdog
        )

        self.ui = AppUI(
            self,
            gesture_sources=self.router.active_sources,
            mode_names=MODE_NAMES,
            initial_mode=config.RELEASE_MODE,
            flash_s=config.UI_FLASH_S,
        )
        self.ui.set_midi_name(self.midi.name)

        self._was_healthy = False
        self._loading = False
        self._closing = False


# --------------- Suit data path (poll thread) ---------------


    def _on_frame(self, packet, mono):
        for action, event in self.router.process(packet, mono):
            if action == "advance":
                self.engine.advance(event)
            elif action == "back":
                self.engine.back()


# --------------- Watchdog (ticker thread) -------------------


    def _watchdog(self):
        """
        Silence sounding notes the moment suit data goes
        stale or the ESP32 leaves the running states —
        without losing the score position, and without
        affecting keyboard-driven use.
        """

        data, age, _connected = self.client.get()

        healthy = (
            data is not None
            and age <= config.STALE_AFTER_S
            and data.get("system") in RUNNING_STATES
        )

        if self._was_healthy and not healthy:
            self.engine.suspend()
            self.router.reset()

        self._was_healthy = healthy


# ------------------- UI commands ----------------------------


    def load_file(self, path):
        """
        Parse in a worker thread (a large file takes a
        moment) and install atomically; the UI stays live.
        """

        if self._loading:
            return

        self._loading = True
        self.ui.show_loading(path)

        def work():
            try:
                score = load_score(
                    path,
                    chord_window_s=config.CHORD_WINDOW_S,
                    channel_filter=config.CHANNEL_FILTER,
                    track_filter=config.TRACK_FILTER,
                )
            except ScoreError as exc:
                self.ui.root.after(0, self._load_failed, str(exc))
                return
            except Exception as exc:
                self.ui.root.after(
                    0, self._load_failed, f"Unexpected: {exc!r}"
                )
                return

            self.engine.load(score)
            self.ui.root.after(0, self._load_done, score)

        threading.Thread(target=work, daemon=True).start()

    def _load_done(self, score):
        self._loading = False
        self.ui.show_score(score)
        print(
            f"Loaded: {score.name} — {score.total_steps} steps, "
            f"{score.note_count} notes, "
            f"{score.duration_s:.1f}s nominal"
        )

    def _load_failed(self, message):
        self._loading = False
        self.ui.show_load_error(message)
        messagebox.showerror(
            "Cannot load MIDI file", message, parent=self.ui.root
        )

    def advance_from_keyboard(self):
        self.engine.advance(GestureEvent.now(
            "keyboard", config.KEYBOARD_STRENGTH
        ))

    def back(self):
        self.engine.back()

    def restart(self):
        self.engine.restart()

    def panic(self):
        self.engine.panic()

    def set_mode(self, name):
        try:
            self.engine.set_mode(make_release_mode(name, config))
        except ValueError as exc:
            print(f"[mode] {exc}")


# ------------------- UI refresh loop -------------------------


    def _ui_tick(self):
        if self._closing:
            return

        try:
            self.ui.refresh(self.engine.view())
            self._refresh_status()
        except Exception as exc:
            print(f"[ui error] {exc!r}")

        self.ui.root.after(config.UI_TICK_MS, self._ui_tick)

    def _refresh_status(self):
        data, age, _connected = self.client.get()

        if data is None or age > config.STALE_AFTER_S:
            self.ui.set_status(
                "Suit: disconnected — keyboard active", "red"
            )
            return

        system = data.get("system")

        if system == "ready":
            self.ui.set_status("Suit: connected", "green")
        elif system == "degraded":
            self.ui.set_status(
                "Suit: connected (degraded)", "orange"
            )
        else:
            self.ui.set_status(f"Suit: {system}", "orange")


# --------------------- Lifecycle -----------------------------


    def run(self, initial_file=None):
        self.client.start()
        self.ticker.start()

        self.ui.root.protocol(
            "WM_DELETE_WINDOW", self._request_close
        )
        self.ui.root.after(config.UI_TICK_MS, self._ui_tick)

        if initial_file:
            self.ui.root.after(
                0, lambda: self.load_file(initial_file)
            )

        try:
            self.ui.root.mainloop()
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            self._teardown()

    def _request_close(self):
        self._closing = True
        self.ui.root.destroy()

    def _teardown(self):
        self._closing = True
        self.client.stop()
        self.ticker.stop()
        self.midi.close()          # panic + port close

        try:
            self.ui.root.destroy()
        except tk.TclError:
            pass


# ------------------- Headless check ---------------------------


def run_check(path):
    """
    Verify the machine without the suit or a window: open
    the real MIDI device, and if a file is given, preload
    it and print what navigation will see. Returns a
    process exit code.
    """

    print("Sound_Track self-check")
    print("----------------------")

    try:
        port = open_port(config.MIDI_BACKEND, config.MIDI_DEVICE)
    except MidiPortError as exc:
        print(f"MIDI: FAILED\n{exc}")
        return 1

    print(f"MIDI: ok — {port.name}")
    port.close()

    path = path or config.DEFAULT_MIDI_PATH
    if not path:
        print("Score: skipped (no file given)")
        return 0

    started = time.perf_counter()

    try:
        score = load_score(
            path,
            chord_window_s=config.CHORD_WINDOW_S,
            channel_filter=config.CHANNEL_FILTER,
            track_filter=config.TRACK_FILTER,
        )
    except ScoreError as exc:
        print(f"Score: FAILED — {exc}")
        return 1

    elapsed_ms = (time.perf_counter() - started) * 1e3

    previous = -1
    for step in score.steps:
        if step.tick < previous:
            print("Score: FAILED — steps out of order")
            return 1
        previous = step.tick

    print(f"Score: ok — loaded in {elapsed_ms:.0f} ms")
    print(f"  name       {score.name}")
    print(f"  steps      {score.total_steps}")
    print(f"  notes      {score.note_count}")
    print(f"  duration   {score.duration_s:.1f} s nominal")
    print(f"  tracks     {len(score.track_names)}")
    print(f"  channels   {sorted(score.channels)}")
    print(f"  setup ctl  {len(score.setup)}")
    print(f"  tempo mrk  {len(score.tempo_map)}")

    return 0


# --------------------- Entry point ----------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Sound_Track — interactive MIDI score "
                    "navigation driven by the motion suit.",
    )
    parser.add_argument(
        "file", nargs="?", default=config.DEFAULT_MIDI_PATH,
        help="MIDI file to load at startup",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="headless self-check (MIDI device + score load)",
    )
    parser.add_argument(
        "--list-devices", action="store_true",
        help="list MIDI output devices and exit",
    )
    args = parser.parse_args()

    if args.list_devices:
        print("MIDI output devices:")
        print(describe_devices(config.MIDI_BACKEND))
        return

    if args.check:
        sys.exit(run_check(args.file))

    print("======================================")
    print("   SOUND_TRACK — score navigation")
    print("======================================")

    try:
        app = SoundTrackApp()
    except MidiPortError as exc:
        print(exc)

        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("No MIDI output", str(exc))
            root.destroy()
        except tk.TclError:
            pass

        sys.exit(1)

    app.run(args.file)


if __name__ == "__main__":
    main()
