# =================================================
# MAIN — Body Motion MIDI
#
# Orchestrates the UI, the MIDI engine and the
# background ESP32 client. The control loop runs as
# a Tk after-callback: the UI thread never blocks on
# the network (the previous design performed a
# blocking HTTP request — with a 10 s timeout —
# inside the UI loop and crashed on the first
# network error).
# =================================================

import time
import tkinter as tk

import config
import mapping
import names
from client import SuitClient
from interface import AppUI
from player import MidiEngine, MidiUnavailableError


RUNNING_STATES = ("ready", "degraded")


class SoundApp:

    def __init__(self, ui, engine, client):
        self.ui = ui
        self.engine = engine
        self.client = client

        # Discrete selectors with hysteresis.
        self.octave_selector = mapping.BinSelector(
            bins=config.MAX_OCTAVE - config.MIN_OCTAVE + 1,
            angle_min=config.OCTAVE_ANGLE_RANGE[0],
            angle_max=config.OCTAVE_ANGLE_RANGE[1],
            hysteresis=config.OCTAVE_HYSTERESIS_DEG,
        )

        self.note_selectors = {
            side: mapping.BinSelector(
                bins=len(mapping.SCALE),
                angle_min=config.NOTE_ANGLE_RANGE[0],
                angle_max=config.NOTE_ANGLE_RANGE[1],
                hysteresis=config.NOTE_HYSTERESIS_DEG,
            )
            for side in ("left", "right")
        }

        # Piezo hit-counter baselines (None until the first
        # packet so history is never replayed as hits).
        self._hit_base = {"left": None, "right": None}

        # Fallback hit detection for firmwares without
        # counters.
        self._legacy_last_hit = {"left": 0.0, "right": 0.0}

        self._silenced = True
        self._last_seq = None
        self._display = {
            "left": {"note": "---", "octave": "-"},
            "right": {"note": "---", "octave": "-"},
        }

        self._last_console = 0.0
        self._last_error_log = 0.0
        self._closing = False

        self._wire_instrument_callbacks()


# ------------------ UI wiring ---------------------


    def _wire_instrument_callbacks(self):
        self.ui.left_combo.bind(
            "<<ComboboxSelected>>",
            lambda _e: self.engine.set_instrument(
                config.LEFT_CHANNEL,
                self.ui.left_instrument(),
            ),
        )

        self.ui.right_combo.bind(
            "<<ComboboxSelected>>",
            lambda _e: self.engine.set_instrument(
                config.RIGHT_CHANNEL,
                self.ui.right_instrument(),
            ),
        )

        self.engine.set_instrument(
            config.LEFT_CHANNEL, self.ui.left_instrument()
        )
        self.engine.set_instrument(
            config.RIGHT_CHANNEL, self.ui.right_instrument()
        )


# ------------------- Main tick --------------------


    def tick(self):
        if self._closing:
            return

        try:
            self._process()
        except Exception as exc:
            # Keep the control loop alive on unexpected
            # data; log at most once per second.
            now = time.monotonic()
            if now - self._last_error_log > 1.0:
                self._last_error_log = now
                print(f"\n[tick error] {exc!r}")

        self.ui.root.after(config.TICK_MS, self.tick)

    def _process(self):
        self.engine.process()

        data, age, connected = self.client.get()

        if data is None or age > config.STALE_AFTER_S:
            self._enter_silence(
                "Disconnected" if not connected
                else "No data from ESP32",
                "red",
            )
            return

        system = data.get("system")

        if system not in RUNNING_STATES:
            self._enter_silence(f"ESP32: {system}", "orange")
            return

        self._silenced = False

        if system == "degraded":
            self.ui.set_status(
                "Connected (degraded: sensor loss)", "orange"
            )
        else:
            self.ui.set_status("Connected", "green")

        imus = {
            imu.get("body"): imu
            for imu in data.get("imu_data", [])
            if isinstance(imu, dict)
        }

        seq = data.get("seq", data.get("timestamp"))
        new_frame = seq != self._last_seq
        self._last_seq = seq

        octave = self._map_octave(imus)

        for side in ("left", "right"):
            self._map_side(side, imus, octave)

        if new_frame:
            self._process_hits(data, imus)

        self._console_line(octave)


# ----------------- Silence handling ----------------


    def _enter_silence(self, message, color):
        self.ui.set_status(message, color)

        if not self._silenced:
            self._silenced = True
            self.engine.silence()

            # Selectors snap to the next measurement instead
            # of applying hysteresis against stale state.
            self.octave_selector.reset()
            for selector in self.note_selectors.values():
                selector.reset()


# ------------------- Field access -------------------


    @staticmethod
    def _angle(imus, body, field, sign):
        """
        Return the sign-adjusted angle of one IMU, or None
        when the sensor is absent, not ok, or the value is
        not numeric. Missing limbs mute their own control
        instead of crashing the loop.
        """

        imu = imus.get(body)

        if not imu or imu.get("ok") is False:
            return None

        value = imu.get(field)

        if not isinstance(value, (int, float)):
            return None

        return sign * float(value)


# --------------------- Octave ----------------------


    def _map_octave(self, imus):
        angles = []

        for body in ("back_upper", "back_lower"):
            angle = self._angle(
                imus, body,
                config.OCTAVE_FIELD, config.OCTAVE_SIGN,
            )
            if angle is not None:
                angles.append(angle)

        if not angles:
            # No torso data: hold the current octave.
            current = self.octave_selector.current
            return config.MIN_OCTAVE + (current or 0)

        mean = sum(angles) / len(angles)
        index = self.octave_selector.select(mean)

        return config.MIN_OCTAVE + index


# ------------------- Per-side voice ------------------


    def _map_side(self, side, imus, octave):
        channel = config.LEFT_CHANNEL if side == "left" \
            else config.RIGHT_CHANNEL

        # ------------------- Note --------------------

        note_sign = config.NOTE_SIGN_LEFT if side == "left" \
            else config.NOTE_SIGN_RIGHT

        angle = self._angle(
            imus, f"{side}_arm", config.NOTE_FIELD, note_sign
        )

        if angle is not None:
            index = self.note_selectors[side].select(angle)
            midi = mapping.build_midi_note(
                octave, mapping.SCALE[index]
            )

            self.engine.play_note(channel, midi)

            self._display[side]["note"] = names.midi_name(midi)
            self._display[side]["octave"] = octave

        # ------------------ Volume -------------------

        vol_sign = config.VOLUME_SIGN_LEFT if side == "left" \
            else config.VOLUME_SIGN_RIGHT

        angle = self._angle(
            imus, f"{side}_hand", config.VOLUME_FIELD, vol_sign
        )

        if angle is not None:
            value = mapping.linear_map(
                angle,
                config.VOLUME_ANGLE_RANGE[0],
                config.VOLUME_ANGLE_RANGE[1],
                0.0, 127.0,
            )
            self.engine.set_cc(
                channel, config.CC_VOLUME, mapping.to_cc(value)
            )

        # ------------------ Reverb -------------------

        rev_sign = config.REVERB_SIGN_LEFT if side == "left" \
            else config.REVERB_SIGN_RIGHT

        angle = self._angle(
            imus, f"{side}_forearm",
            config.REVERB_FIELD, rev_sign,
        )

        if angle is not None:
            value = mapping.linear_map(
                angle,
                config.REVERB_ANGLE_RANGE[0],
                config.REVERB_ANGLE_RANGE[1],
                0.0, 127.0,
            )
            self.engine.set_cc(
                channel, config.CC_REVERB, mapping.to_cc(value)
            )

        # ------------------ Display ------------------

        self.ui.set_side(
            side,
            self._display[side]["note"],
            self._display[side]["octave"],
            self.engine.get_cc(channel, config.CC_VOLUME),
            self.engine.get_cc(channel, config.CC_REVERB),
        )


# --------------------- Drums ------------------------


    def _process_hits(self, data, imus):
        piezo = data.get("piezo")

        if isinstance(piezo, dict):
            self._counter_hits(piezo)
        else:
            self._legacy_hits(imus)

    def _drum_note(self, side):
        return self.ui.left_drum() if side == "left" \
            else self.ui.right_drum()

    def _counter_hits(self, piezo):
        """
        Firmware-side hit detection (protocol v2): diff the
        monotonic hit counters. Immune to polling rate and
        to the Visual client polling concurrently. A counter
        that moved backwards means the ESP32 rebooted: the
        baseline resets without firing.
        """

        for side in ("left", "right"):
            channel = piezo.get(side)

            if not isinstance(channel, dict):
                continue

            hits = channel.get("hits")

            if not isinstance(hits, int):
                continue

            base = self._hit_base[side]

            if base is None or hits < base:
                self._hit_base[side] = hits
                continue

            if hits > base:
                self._hit_base[side] = hits

                velocity = mapping.velocity_from_peak(
                    channel.get("hit_peak"),
                    config.PIEZO_PEAK_FLOOR,
                    config.PIEZO_PEAK_CEIL,
                    config.VELOCITY_MIN,
                    config.VELOCITY_MAX,
                )

                self.engine.play_drum(
                    self._drum_note(side), velocity
                )

    def _legacy_hits(self, imus):
        """
        Protocol v1 fallback: raw threshold + cooldown on
        the per-IMU piezo fields.
        """

        now = time.monotonic()

        for side, body, field in (
            ("left", "left_hand", "piezo_left"),
            ("right", "right_hand", "piezo_right"),
        ):
            imu = imus.get(body)

            if not imu:
                continue

            value = imu.get(field, 0)

            if not isinstance(value, (int, float)):
                continue

            if value < config.PIEZO_THRESHOLD:
                continue

            if now - self._legacy_last_hit[side] < \
                    config.PIEZO_COOLDOWN_S:
                continue

            self._legacy_last_hit[side] = now

            self.engine.play_drum(
                self._drum_note(side), config.NOTE_VELOCITY
            )


# -------------------- Console -----------------------


    def _console_line(self, octave):
        now = time.monotonic()

        if now - self._last_console < config.CONSOLE_PERIOD_S:
            return

        self._last_console = now

        left = self._display["left"]["note"]
        right = self._display["right"]["note"]

        lv = self.engine.get_cc(
            config.LEFT_CHANNEL, config.CC_VOLUME)
        lr = self.engine.get_cc(
            config.LEFT_CHANNEL, config.CC_REVERB)
        rv = self.engine.get_cc(
            config.RIGHT_CHANNEL, config.CC_VOLUME)
        rr = self.engine.get_cc(
            config.RIGHT_CHANNEL, config.CC_REVERB)

        print(
            f"L {left:4s}  Oct:{octave}"
            f"  Vol:{lv:3d}  Rev:{lr:3d}"
            f"    |    "
            f"R {right:4s}  Oct:{octave}"
            f"  Vol:{rv:3d}  Rev:{rr:3d}",
            end="\r",
        )


# -------------------- Shutdown ----------------------


    def request_close(self):
        self._closing = True
        self.ui.root.destroy()


# ==================== Entry point =====================


def main():
    print("======================================")
    print("      BODY MOTION MIDI")
    print("======================================")

    ui = AppUI()

    try:
        engine = MidiEngine()
    except MidiUnavailableError as exc:
        print(exc)
        ui.root.destroy()
        return

    client = SuitClient()
    client.start()

    app = SoundApp(ui, engine, client)

    ui.root.protocol("WM_DELETE_WINDOW", app.request_close)
    ui.root.after(config.TICK_MS, app.tick)

    try:
        ui.root.mainloop()

    except KeyboardInterrupt:
        print("\nProgram stopped.")

    finally:
        client.stop()
        engine.close()

        try:
            ui.root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    main()
