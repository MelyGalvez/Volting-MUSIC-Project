#!/usr/bin/env python3
"""Continuous motion recorder for the ESP32 Motion Suit (project V4).

The suit publishes one JSON snapshot per MQTT message.  This program
subscribes to that topic, writes every message it receives into a CSV
file, and lets the user mark the beginning and the end of each movement
by pressing SPACE:

    MQTT messages :  data  data  data  data  data  data  data  data
    SPACE presses :              ^                 ^
    CSV records   :  data  data  START data  data  END   data  data

Recording is CONTINUOUS.  SPACE only inserts a marker row into the
stream; it never pauses, stops or restarts the MQTT reception.

    ESP32 suit -> Python_MQTT_Bridge -> MQTT broker -> this recorder -> CSV

Controls:

    SPACE   insert a marker (1st = start of movement 1, 2nd = end of
            movement 1, 3rd = start of movement 2, ...)
    Q, ESC  stop the session and close the CSV file
    Ctrl+C  same as Q

This project only records and segments.  Movement recognition,
comparison, wheelchair control and vibration feedback are NOT part of
it.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt


# ----------------------------------------------------------------------
# Configuration
#
# The MQTT values below are NOT invented: they are the ones used by
# V4/Python_MQTT_Bridge/main.py, which is the program that publishes the
# suit data.  Each constant can be overridden with an environment
# variable of the same name, exactly like in the bridge.
# ----------------------------------------------------------------------

#: Broker the bridge publishes to (Python_MQTT_Bridge/main.py, line 64).
MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "192.168.56.1")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))

#: Topic carrying the suit snapshots (Python_MQTT_Bridge/main.py, line 66).
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "motion_suit/data")

#: The bridge publishes with QoS 0, without authentication and without
#: TLS, so the recorder subscribes exactly the same way.
MQTT_QOS = 0
MQTT_KEEPALIVE_S = 30

#: Bounds of the automatic reconnection backoff of paho, in seconds.  A
#: temporary broker outage therefore only creates a gap in the
#: recording; the program keeps running and resumes on its own.
MQTT_RECONNECT_MIN_S = 1
MQTT_RECONNECT_MAX_S = 30

#: Top level keys of a valid suit snapshot (wire protocol v2, produced
#: by Arduino_Suit_ESP32_Get_Data_V4/json.cpp).  A message that does not
#: carry them is counted as invalid and skipped instead of crashing.
REQUIRED_KEYS = ("seq", "timestamp", "system", "imu_data")

#: Where the CSV files are written (next to this file).
RECORDINGS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "recordings"
)

#: How often the main thread looks at the keyboard.  50 times per second
#: is instant for a human and costs almost no CPU.
KEY_POLL_PERIOD_S = 0.02

#: Two SPACE events closer than this belong to the same physical press
#: (the operating system repeats a key that is held down).  One physical
#: press must create exactly one marker.
SPACE_DEBOUNCE_S = 0.25

#: Period of the "still recording" status line.
STATUS_PERIOD_S = 2.0


# ----------------------------------------------------------------------
# The 8 IMUs of the suit
#
# Names and order come from BODY_NAMES in
# Arduino_Suit_ESP32_Get_Data_V4/json.cpp, which matches the BodyPart
# enum of types.h.  The position in this list is the IMU index used by
# the firmware (0 = back_upper ... 7 = right_hand).
# ----------------------------------------------------------------------

IMU_NAMES = [
    "back_upper",      # 0
    "back_lower",      # 1
    "left_arm",        # 2
    "right_arm",       # 3
    "left_forearm",    # 4
    "right_forearm",   # 5
    "left_hand",       # 6
    "right_hand",      # 7
]

#: Single value fields of one IMU object, in JSON order.  qw..qz is the
#: T-pose relative quaternion, heading/pitch/roll the Euler angles
#: derived from it (degrees).
IMU_SCALARS = ["qw", "qx", "qy", "qz", "heading", "pitch", "roll"]

#: Fields of one IMU object that are {"x":..,"y":..,"z":..} objects.
#: json.cpp also exports "total_accel", but it writes the very same
#: numbers as "accel" (see its comment), so this recorder stores that
#: measurement once, under accel_*.
IMU_VECTORS = ["accel", "lin_accel", "gravity", "gyro", "mag"]

#: BNO055 self calibration levels, 0 (none) to 3 (full).
IMU_CALIB = ["sys", "gyro", "accel", "mag"]

#: BNO055 diagnostic registers.
IMU_STATUS = ["system", "self_test", "error"]


# ----------------------------------------------------------------------
# CSV layout
#
# One row = one record.  "record_type" says which kind:
#
#   sample : one MQTT message from the suit (sensor columns filled)
#   marker : one SPACE press (sensor columns left empty on purpose)
# ----------------------------------------------------------------------

COMMON_COLUMNS = [
    "record_type",       # "sample" or "marker"
    "sample_index",      # counts the samples, always increasing
    "event",             # "" for samples, "START" / "END" for markers
    "movement_id",       # 1, 2, 3 ... ; empty outside a movement
    "pc_time_iso",       # PC clock, human readable
    "pc_time_unix",      # PC clock, seconds since 1970
    "esp_timestamp_ms",  # suit clock: ms since the ESP32 booted
    "esp_seq",           # suit scan counter (detects reboots and gaps)
    "system",            # boot / calibration / ready / degraded / error
    "piezo_left_peak",
    "piezo_left_hits",
    "piezo_left_hit_peak",
    "piezo_right_peak",
    "piezo_right_hits",
    "piezo_right_hit_peak",
]


def imu_column_names(imu_name):
    """Return the column names holding the data of one IMU."""
    columns = [imu_name + "_ok", imu_name + "_calibrated"]
    columns += [imu_name + "_" + field for field in IMU_SCALARS]

    for vector in IMU_VECTORS:
        columns += [
            imu_name + "_" + vector + "_" + axis for axis in ("x", "y", "z")
        ]

    columns += [imu_name + "_temp"]
    columns += [imu_name + "_calib_" + field for field in IMU_CALIB]
    columns += [imu_name + "_status_" + field for field in IMU_STATUS]

    return columns


def imu_values(frame):
    """Return the values of one IMU, in the order of imu_column_names().

    Anything missing or not numeric becomes an empty cell: the recorder
    never invents a value the suit did not send.
    """
    if not isinstance(frame, dict):
        frame = {}

    # "cal" in the JSON is the T-pose reference flag (json.cpp).
    values = [to_flag(frame.get("ok")), to_flag(frame.get("cal"))]
    values += [to_number(frame.get(field)) for field in IMU_SCALARS]

    for vector in IMU_VECTORS:
        measurement = frame.get(vector)

        # json.cpp exports the accelerometer under two names holding the
        # same numbers; use the other one if "accel" is ever absent.
        if vector == "accel" and not isinstance(measurement, dict):
            measurement = frame.get("total_accel")

        if not isinstance(measurement, dict):
            measurement = {}

        values += [to_number(measurement.get(axis)) for axis in ("x", "y", "z")]

    values += [to_number(frame.get("temp"))]

    calib = frame.get("calib")
    calib = calib if isinstance(calib, dict) else {}
    values += [to_number(calib.get(field)) for field in IMU_CALIB]

    status = frame.get("status")
    status = status if isinstance(status, dict) else {}
    values += [to_number(status.get(field)) for field in IMU_STATUS]

    return values


#: Full header: the common columns followed by the 8 IMU blocks.
CSV_COLUMNS = list(COMMON_COLUMNS)

for _imu_name in IMU_NAMES:
    CSV_COLUMNS += imu_column_names(_imu_name)


# ----------------------------------------------------------------------
# Small conversion helpers
# ----------------------------------------------------------------------


def to_number(value):
    """Return the value if it is a real number, otherwise an empty cell."""
    if isinstance(value, bool):
        return ""

    if isinstance(value, (int, float)):
        return value

    return ""


def to_flag(value):
    """Return a JSON boolean as 1 / 0, anything else as an empty cell."""
    if isinstance(value, bool):
        return 1 if value else 0

    return ""


def unique_csv_path(directory):
    """Build a file name that does not exist yet in the directory."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(directory, "session_" + stamp + ".csv")

    counter = 2

    while os.path.exists(path):
        path = os.path.join(
            directory, "session_" + stamp + "_" + str(counter) + ".csv"
        )
        counter += 1

    return path


# ----------------------------------------------------------------------
# Recorder
#
# Writes the CSV file.  Two different threads use it: the MQTT network
# thread (samples) and the main thread (markers), so every write is
# protected by a lock.
# ----------------------------------------------------------------------


class Recorder:
    """Continuous CSV writer for samples and markers."""

    def __init__(self, path):
        self.path = path

        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(CSV_COLUMNS)
        self._file.flush()

        self._lock = threading.Lock()

        # Statistics, readable from any thread.
        self.sample_count = 0     # also the index of the next sample
        self.marker_count = 0
        self.movement_count = 0
        self.invalid_count = 0

        # Id of the movement being recorded, None between movements.
        self.active_movement = None

        self.last_seq = None
        self.last_system = None

    # -- samples -------------------------------------------------------

    def record_sample(self, payload):
        """Decode one MQTT payload and append it as a sample row.

        Returns False (and counts the message as invalid) when the
        payload is not a usable suit snapshot.  A malformed message must
        never stop the recording.
        """
        snapshot = parse_snapshot(payload)

        if snapshot is None:
            with self._lock:
                self.invalid_count += 1
            return False

        row = self._build_sample_row(snapshot)

        with self._lock:
            row[1] = self.sample_count
            row[3] = (
                "" if self.active_movement is None else self.active_movement
            )

            self._writer.writerow(row)
            self._file.flush()

            self.sample_count += 1
            self.last_seq = snapshot.get("seq")
            self.last_system = snapshot.get("system")

        return True

    def _build_sample_row(self, snapshot):
        """Turn one snapshot into a CSV row (built outside the lock)."""
        now = time.time()

        piezo = snapshot.get("piezo")
        piezo = piezo if isinstance(piezo, dict) else {}

        left = piezo.get("left")
        left = left if isinstance(left, dict) else {}

        right = piezo.get("right")
        right = right if isinstance(right, dict) else {}

        system = snapshot.get("system")

        row = [
            "sample",                                  # record_type
            0,                                         # sample_index, set later
            "",                                        # event
            "",                                        # movement_id, set later
            datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
            round(now, 3),
            to_number(snapshot.get("timestamp")),
            to_number(snapshot.get("seq")),
            system if isinstance(system, str) else "",
            to_number(left.get("peak")),
            to_number(left.get("hits")),
            to_number(left.get("hit_peak")),
            to_number(right.get("peak")),
            to_number(right.get("hits")),
            to_number(right.get("hit_peak")),
        ]

        # Keep every IMU distinguishable: each sensor is written in the
        # columns of its own body part, matched by the "body" name it
        # sends (or by its position in the array as a fallback).
        frames = frames_by_name(snapshot.get("imu_data"))

        for imu_name in IMU_NAMES:
            row += imu_values(frames.get(imu_name))

        return row

    # -- markers -------------------------------------------------------

    def record_marker(self):
        """Append a START or an END marker row.

        The first press starts movement 1, the second ends it, the third
        starts movement 2, and so on.  Returns the triplet
        (event, movement_id, sample_index).
        """
        now = time.time()

        with self._lock:
            if self.active_movement is None:
                self.movement_count += 1
                self.active_movement = self.movement_count
                event = "START"
            else:
                event = "END"

            movement_id = self.active_movement

            # Index the next sample will receive: a movement therefore
            # covers the samples start <= sample_index < end.
            sample_index = self.sample_count

            row = [""] * len(CSV_COLUMNS)
            row[0] = "marker"
            row[1] = sample_index
            row[2] = event
            row[3] = movement_id
            row[4] = datetime.fromtimestamp(now).isoformat(
                timespec="milliseconds"
            )
            row[5] = round(now, 3)

            self._writer.writerow(row)
            self._file.flush()

            self.marker_count += 1

            if event == "END":
                self.active_movement = None

        return event, movement_id, sample_index

    # -- shutdown ------------------------------------------------------

    def close(self):
        """Flush and close the CSV file."""
        with self._lock:
            self._file.flush()
            self._file.close()


def parse_snapshot(payload):
    """Return the snapshot carried by an MQTT payload, or None.

    None means "not a suit snapshot": wrong encoding, broken JSON, not a
    JSON object, or one of the protocol v2 keys is missing.
    """
    try:
        text = payload.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None

    try:
        snapshot = json.loads(text)
    except (ValueError, TypeError):
        return None

    if not isinstance(snapshot, dict):
        return None

    for key in REQUIRED_KEYS:
        if key not in snapshot:
            return None

    return snapshot


def frames_by_name(imu_data):
    """Index the imu_data array by body name.

    The firmware always sends the 8 sensors in the BODY_NAMES order, so
    an entry without a usable "body" field is assigned to the body part
    of its position in the array.
    """
    frames = {}

    if not isinstance(imu_data, list):
        return frames

    for position, frame in enumerate(imu_data):
        if not isinstance(frame, dict):
            continue

        name = frame.get("body")

        if name not in IMU_NAMES:
            if position < len(IMU_NAMES):
                name = IMU_NAMES[position]
            else:
                continue

        frames[name] = frame

    return frames


# ----------------------------------------------------------------------
# MQTT
#
# paho runs the network in its own background thread (loop_start), so
# messages keep arriving while the main thread watches the keyboard.
# ----------------------------------------------------------------------


def create_mqtt_client(recorder):
    """Build the MQTT client that feeds the recorder."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="",
        clean_session=True,
    )

    client.reconnect_delay_set(
        min_delay=MQTT_RECONNECT_MIN_S,
        max_delay=MQTT_RECONNECT_MAX_S,
    )

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            # Subscribing here, and not once at startup, restores the
            # subscription automatically after every reconnection.
            client.subscribe(MQTT_TOPIC, qos=MQTT_QOS)
            log(
                "connected to mqtt://%s:%d -- listening on '%s'"
                % (MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC)
            )
        else:
            log("connection refused (%s), retrying" % reason_code)

    def on_disconnect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            log(
                "MQTT connection lost, reconnecting in the background "
                "(the recording continues)"
            )

    def on_message(client, userdata, message):
        # This runs in the paho thread: no exception may escape, or the
        # network loop would die and the reception would stop.
        try:
            recorder.record_sample(message.payload)
        except Exception as error:
            log("could not record a message: %s" % error)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    return client


# ----------------------------------------------------------------------
# Non blocking keyboard
#
# The keyboard is only read when a key is already waiting, so the main
# thread never blocks and the MQTT thread is never delayed.
# ----------------------------------------------------------------------


class KeyReader:
    """Reads the keys pressed so far, without ever waiting for one."""

    def __init__(self):
        self._windows = os.name == "nt"
        self._fd = None
        self._saved = None

    def __enter__(self):
        if not self._windows:
            # Unix terminals normally deliver one line at a time; switch
            # to one character at a time for the session.
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)

        return self

    def __exit__(self, *exc_info):
        if not self._windows and self._saved is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)

    def poll(self):
        """Return the characters typed since the previous call."""
        if self._windows:
            return self._poll_windows()

        return self._poll_unix()

    def _poll_windows(self):
        import msvcrt

        keys = []

        while msvcrt.kbhit():
            char = msvcrt.getwch()

            # Arrows and function keys arrive as two characters; drop
            # both so they cannot be mistaken for a command.
            if char in ("\x00", "\xe0"):
                if msvcrt.kbhit():
                    msvcrt.getwch()
                continue

            keys.append(char)

        return keys

    def _poll_unix(self):
        import select

        keys = []

        while select.select([sys.stdin], [], [], 0)[0]:
            char = sys.stdin.read(1)

            if not char:
                break

            keys.append(char)

        return strip_escape_sequences(keys)


def strip_escape_sequences(keys):
    """Drop terminal escape sequences such as the arrow keys.

    They start with ESC + "[" (or "O") and end on a letter or "~"; a
    lone ESC is kept, because ESC stops the session.
    """
    cleaned = []
    index = 0

    while index < len(keys):
        char = keys[index]

        if (
            char == "\x1b"
            and index + 1 < len(keys)
            and keys[index + 1] in ("[", "O")
        ):
            index += 2

            while index < len(keys) and not (
                keys[index].isalpha() or keys[index] == "~"
            ):
                index += 1

            index += 1
            continue

        cleaned.append(char)
        index += 1

    return cleaned


# ----------------------------------------------------------------------
# Console output
# ----------------------------------------------------------------------


def log(message):
    """Print one timestamped line."""
    print(datetime.now().strftime("%H:%M:%S") + "  " + message, flush=True)


def print_banner(path):
    print()
    print("=" * 68)
    print("  ESP32 Motion Suit - continuous motion recorder")
    print("=" * 68)
    print(
        "  broker    : mqtt://%s:%d  (no authentication, no TLS)"
        % (MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    )
    print("  topic     : %s  (QoS %d)" % (MQTT_TOPIC, MQTT_QOS))
    print("  IMUs      : %d  (%s)" % (len(IMU_NAMES), ", ".join(IMU_NAMES)))
    print("  file      : %s" % path)
    print("-" * 68)
    print("  SPACE     : start / end a movement (recording never stops)")
    print("  Q or ESC  : stop the session")
    print("=" * 68)
    print()


def print_status(recorder, connected):
    if recorder.active_movement is None:
        state = "waiting for SPACE"
    else:
        state = "RECORDING movement %d" % recorder.active_movement

    log(
        "samples=%d markers=%d movements=%d invalid=%d mqtt=%s "
        "last_seq=%s suit=%s | %s"
        % (
            recorder.sample_count,
            recorder.marker_count,
            recorder.movement_count,
            recorder.invalid_count,
            "online" if connected else "offline",
            recorder.last_seq,
            recorder.last_system,
            state,
        )
    )


def print_summary(recorder):
    print()
    print("-" * 68)
    print("  samples recorded : %d" % recorder.sample_count)
    print("  markers written  : %d" % recorder.marker_count)
    print("  movements marked : %d" % recorder.movement_count)
    print("  invalid messages : %d" % recorder.invalid_count)

    if recorder.active_movement is not None:
        print(
            "  WARNING: movement %d was started but never ended, so the "
            "file has no END marker for it." % recorder.active_movement
        )

    print("  file             : %s" % recorder.path)
    print("-" * 68)
    print()


# ----------------------------------------------------------------------
# Session
# ----------------------------------------------------------------------


def run_session(recorder, client):
    """Watch the keyboard until the user stops the session.

    The MQTT thread keeps filling the CSV file the whole time; this loop
    only adds markers.
    """
    last_space = 0.0
    last_status = time.monotonic()

    with KeyReader() as keyboard:
        while True:
            for key in keyboard.poll():

                if key == " ":
                    now = time.monotonic()

                    # A key held down repeats: one marker per press.
                    if now - last_space < SPACE_DEBOUNCE_S:
                        continue

                    last_space = now

                    event, movement_id, sample_index = recorder.record_marker()

                    log(
                        "%-5s movement %d at sample_index %d"
                        % (event, movement_id, sample_index)
                    )
                    continue

                if key in ("q", "Q", "\x1b", "\x03"):
                    log("stopping the session")
                    return

            now = time.monotonic()

            if now - last_status >= STATUS_PERIOD_S:
                last_status = now
                print_status(recorder, client.is_connected())

            time.sleep(KEY_POLL_PERIOD_S)


def main():
    os.makedirs(RECORDINGS_DIR, exist_ok=True)

    path = unique_csv_path(RECORDINGS_DIR)
    recorder = Recorder(path)
    client = create_mqtt_client(recorder)

    print_banner(path)

    # connect_async + loop_start: the program starts even if the broker
    # is not reachable yet, and connects as soon as it becomes available.
    client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE_S)
    client.loop_start()

    try:
        run_session(recorder, client)
    except KeyboardInterrupt:
        print()
        log("interrupted (Ctrl+C)")
    finally:
        client.disconnect()
        client.loop_stop()
        recorder.close()
        print_summary(recorder)

    return 0


if __name__ == "__main__":
    sys.exit(main())
