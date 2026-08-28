"""Turns the orientation error into vibration commands for the ESP32.

One command is published on the haptic topic at HAPTIC_UPDATE_HZ. The
firmware (Arduino_Suit_ESP32_Get_Data_V4/haptic_mqtt.cpp) subscribes to
it and drives the two motors on GPIO12 (left) and GPIO13 (right).

Payload, flat JSON so the firmware can parse it without a JSON library:

    {"v":1,"seq":42,
     "left":0.80,"right":0.00,
     "pulse_hz":6.0,"pulse_ms":80,"hold_ms":800}

    left / right : motor power, 0.0 = off ... 1.0 = full
    pulse_hz     : pulses per second (0 would mean continuous)
    pulse_ms     : ON time of one pulse
    hold_ms      : lifetime of the command; the firmware stops the
                   motors on its own if nothing new arrives, so a
                   crash of this program cannot leave a motor running

The vibration is pulsed, never continuous: a continuous buzz is quickly
ignored by the skin, and pulses carry a second piece of information
through their rhythm. Like a parking sensor, the pulses accelerate as
the user approaches the target, and the vibration stops completely once
the pose is inside the tolerance.
"""

from __future__ import annotations

import json
import time

import config
import guidance


def _ramp(error_deg: float) -> float:
    """0 at the tolerance boundary, 1 at HAPTIC_FULL_INTENSITY_DEG."""
    low = config.POSITION_TOLERANCE_DEG
    high = max(config.HAPTIC_FULL_INTENSITY_DEG, low + 1.0)

    return max(0.0, min(1.0, (error_deg - low) / (high - low)))


class HapticController:
    """Builds, rate limits and publishes the vibration commands."""

    def __init__(self, link, topic: str = config.MQTT_HAPTIC_TOPIC) -> None:
        self.link = link
        self.topic = topic

        self.left = 0.0
        self.right = 0.0
        self.pulse_hz = 0.0
        self.sent_count = 0
        self.last_error: str | None = None

        self._sequence = 0
        self._last_publish = 0.0

    # -- main entry ----------------------------------------------------

    def update(self, evaluation: guidance.Evaluation, now: float | None = None) -> None:
        """Publish the command matching the current evaluation."""
        moment = time.monotonic() if now is None else now

        period = 1.0 / max(config.HAPTIC_UPDATE_HZ, 0.1)

        if moment - self._last_publish < period:
            return

        # Advance on a fixed grid rather than restarting from "now":
        # a sleep of 20 ms really lasts ~31 ms on Windows, and
        # restarting from the late wake-up would slowly stretch the
        # period (10 Hz asked, 8 Hz obtained). If the loop falls more
        # than one period behind, resynchronise instead of catching up
        # with a burst.
        self._last_publish += period

        if moment - self._last_publish > period:
            self._last_publish = moment

        left, right, pulse_hz = self._decide(evaluation)

        self.left = left
        self.right = right
        self.pulse_hz = pulse_hz

        if not config.HAPTICS_ENABLED:
            return

        self._publish(left, right, pulse_hz)

    def stop(self) -> None:
        """Silence both motors immediately (end of session, Ctrl+C)."""
        self.left = 0.0
        self.right = 0.0
        self.pulse_hz = 0.0

        if config.HAPTICS_ENABLED:
            self._publish(0.0, 0.0, 0.0)

    # -- decision ------------------------------------------------------

    def _decide(self, evaluation: guidance.Evaluation) -> tuple[float, float, float]:
        """Which motor, how strong, how fast."""
        direction = evaluation.direction

        # On target, holding, finished, or no data to trust: silence.
        if (direction == guidance.NONE
                or evaluation.error_deg is None
                or evaluation.state in (guidance.WAITING_DATA, guidance.FINISHED)):
            return 0.0, 0.0, 0.0

        ramp = _ramp(evaluation.error_deg)

        intensity = (
            config.HAPTIC_INTENSITY_MIN
            + (config.HAPTIC_INTENSITY_MAX - config.HAPTIC_INTENSITY_MIN) * ramp
        )

        # Far from the target: slow pulses. Close to it: fast pulses.
        pulse_hz = (
            config.HAPTIC_PULSE_HZ_MAX
            - (config.HAPTIC_PULSE_HZ_MAX - config.HAPTIC_PULSE_HZ_MIN) * ramp
        )

        if direction == guidance.LEFT:
            return intensity, 0.0, pulse_hz

        if direction == guidance.RIGHT:
            return 0.0, intensity, pulse_hz

        # BOTH: the correction is not a left/right turn (the user has to
        # bend, lift or lower). Both motors pulse together rather than
        # pointing to a side that would be wrong.
        return intensity, intensity, pulse_hz

    # -- transport -----------------------------------------------------

    def _publish(self, left: float, right: float, pulse_hz: float) -> None:
        self._sequence += 1

        payload = json.dumps({
            "v": 1,
            "seq": self._sequence,
            "left": round(left, 3),
            "right": round(right, 3),
            "pulse_hz": round(pulse_hz, 2),
            "pulse_ms": config.HAPTIC_PULSE_MS,
            "hold_ms": config.HAPTIC_HOLD_MS,
        })

        if self.link.publish(self.topic, payload):
            self.sent_count += 1
            self.last_error = None
        else:
            # Not fatal: the motors stop by themselves when commands
            # stop arriving, and the next attempt is 100 ms away.
            self.last_error = "not delivered (broker unreachable?)"
