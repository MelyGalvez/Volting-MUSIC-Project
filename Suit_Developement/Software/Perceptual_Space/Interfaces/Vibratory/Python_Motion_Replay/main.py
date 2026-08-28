#!/usr/bin/env python3
"""Replays a recorded choreography and guides the user through it.

    recordings/session_*.csv          live suit (MQTT)
            |                                |
            v                                v
      choreography.py  -- targets -->   guidance.py  --> haptics.py
      (START/END cut)                   (error, hold)     (vibration)
                                             |
                                             v
                                           ui.py

For each movement the target is the average orientation of the last
half second of the RECORDED movement. The user performs the movement,
and as soon as every compared sensor is within the tolerance a five
second countdown starts. Leaving the tolerance resets it to zero. Once
the five seconds are complete the next movement begins.

While the user is off target, the ESP32 vibrates the left or the right
motor to tell which way to turn.

Keys during a session:

    N   capture the neutral pose (aligns a different T-pose calibration)
    S   skip the current movement
    Q, ESC, Ctrl+C   stop the session

This program only guides. It does not control any motor other than the
two vibrators, and it never moves a wheelchair.
"""

from __future__ import annotations

import os
import sys
import time

import choreography as choreography_module
import config
import guidance
import haptics as haptics_module
import ui
from keyboard import KeyReader
from live_data import MqttLink


# ----------------------------------------------------------------------
# Choosing the recording
# ----------------------------------------------------------------------


def choose_recording(argument: str | None) -> str | None:
    """Return the CSV to replay, asking the user if needed."""
    if argument:
        if os.path.isfile(argument):
            return argument

        print("File not found: %s" % argument)
        return None

    recordings = choreography_module.list_recordings(config.RECORDINGS_DIR)

    if not recordings:
        print("No recording found in %s" % config.RECORDINGS_DIR)
        print("Record a choreography first with Python_Motion_Recorder,")
        print("or pass a file: python main.py path/to/session.csv")
        return None

    if len(recordings) == 1:
        return recordings[0]

    print()
    print("Recordings available in %s" % config.RECORDINGS_DIR)
    print()

    for position, path in enumerate(recordings[:20], start=1):
        size_kb = os.path.getsize(path) / 1024.0
        moment = time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path))
        )

        print("  %2d.  %-42s  %s  %6.0f kB"
              % (position, os.path.basename(path), moment, size_kb))

    print()

    try:
        answer = input("Which one? [1] ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not answer:
        return recordings[0]

    try:
        choice = int(answer)
    except ValueError:
        print("Not a number.")
        return None

    if not 1 <= choice <= len(recordings):
        print("Out of range.")
        return None

    return recordings[choice - 1]


# ----------------------------------------------------------------------
# The session loop
# ----------------------------------------------------------------------


def run_session(choreo, session, link, haptic) -> None:
    """Redraw, evaluate and vibrate until the user stops or finishes."""
    ui.enable_ansi()

    refresh = 1.0 / max(config.UI_REFRESH_HZ, 1.0)
    last_draw = 0.0

    # Message rate, measured over a sliding second.
    last_count = 0
    last_rate_check = time.monotonic()
    rate_hz = 0.0

    with KeyReader() as keys:
        while True:
            now = time.monotonic()

            for key in keys.poll():
                if key in ("q", "Q", "\x1b", "\x03"):
                    return

                if key in ("n", "N"):
                    session.start_neutral_capture(now)

                if key in ("s", "S"):
                    session.skip(now)

            evaluation = session.evaluate(link.state(), now)

            haptic.update(evaluation, now)

            if now - last_rate_check >= 1.0:
                rate_hz = (link.message_count - last_count) / (now - last_rate_check)
                last_count = link.message_count
                last_rate_check = now

            if now - last_draw >= refresh:
                last_draw = now
                ui.clear()
                print(ui.render(choreo, session, evaluation, link, haptic, rate_hz))

            if evaluation.state == guidance.FINISHED:
                # One last frame so the user sees the final screen.
                time.sleep(1.0)
                return

            time.sleep(config.KEY_POLL_PERIOD_S)


def main() -> int:
    path = choose_recording(sys.argv[1] if len(sys.argv) > 1 else None)

    if path is None:
        return 1

    try:
        choreo = choreography_module.load(path)
    except choreography_module.ChoreographyError as error:
        print()
        print("This recording cannot be used:")
        print("   %s" % error)
        print()
        return 1

    print()
    print(ui.choreography_summary(choreo))
    print()
    print("  Broker  : mqtt://%s:%d" % (config.MQTT_BROKER_HOST,
                                        config.MQTT_BROKER_PORT))
    print("  Data    : %s" % config.MQTT_DATA_TOPIC)
    print("  Haptic  : %s%s" % (
        config.MQTT_HAPTIC_TOPIC,
        "" if config.HAPTICS_ENABLED else "   (disabled)",
    ))
    print()

    try:
        input("  Press ENTER to start the session (Ctrl+C to abort)... ")
    except (EOFError, KeyboardInterrupt):
        return 0

    session = guidance.GuidanceSession(choreo)
    link = MqttLink()
    haptic = haptics_module.HapticController(link)

    link.start()

    try:
        run_session(choreo, session, link, haptic)
    except KeyboardInterrupt:
        pass
    finally:
        # Silence the motors before leaving, then close the link. The
        # firmware would stop them by itself after HAPTIC_HOLD_MS, this
        # simply makes it immediate.
        haptic.stop()
        time.sleep(0.1)
        link.stop()

    print(ui.session_summary(session))

    return 0


if __name__ == "__main__":
    sys.exit(main())
