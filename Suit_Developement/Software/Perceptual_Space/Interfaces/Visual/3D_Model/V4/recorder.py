import csv
import datetime
import json
import time
import threading

from config import RECORDER_FLUSH_PERIOD_S


# ================================================
# RECORDER
# ================================================


CSV_COLUMNS = (
    "datetime",
    "epoch",
    "arduino_timestamp",
    "system",
    "json",
)


IMU_FIELDS = (
    "body",
    "ok",
    "cal",
    "heading",
    "pitch",
    "roll",
)


def _format_datetime(epoch):
    """
    Local wall-clock stamp with milliseconds.

    Same shape as imu_log.csv ("2026-07-10 11:25:48.781"):
    strftime has no millisecond directive, so the six digits
    of %f are truncated to three.

    """

    return datetime.datetime.fromtimestamp(epoch).strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]


class Recorder:
    """
    CSV recorder for motion capture sessions.

    Records the session as a CSV file laid out like
    imu_log.csv: one row per acquisition frame, carrying the
    host wall-clock (readable and as an epoch), the firmware
    timestamp, the system state, and a `json` column holding
    the complete body for that frame.

    Keeping the pose as JSON inside one column is what allows
    a row to describe the whole body at once — sequence
    number, timestamp and every segment with its orientation —
    while the file stays a plain CSV any spreadsheet opens.

    Duplicate frames (same sequence number) are skipped so the
    recording reflects the true sensor rate, not the render
    rate.

    The orientation is the Euler triplet the ESP32 transmits,
    next to the calibration flag that tells a T-pose-relative
    reading apart from an absolute one. A field missing from
    the packet is recorded as null.

    """


# ----------------- Initialization ----------------


    def __init__(self):
        """
        Initialize the recorder.

        Creates an inactive recorder and initializes the
        internal CSV writer, file handle and thread lock.

        """

        self.file = None
        self.writer = None
        self.recording = False
        self._lock = threading.Lock()
        self._last_seq = None
        self._last_flush = 0.0
        self._frame_count = 0


# ------------------- Recording -------------------


    def start(self):
        """
        Start a new CSV recording.

        Creates a new CSV file named with the current local
        time, writes the column headers and enables recording.

        """

        filename = time.strftime("capture_%Y%m%d_%H%M%S.csv")

        with self._lock:
            if self.recording:
                return

            try:
                self.file = open(filename, "w", newline="",
                                 encoding="utf-8")
            except OSError as exc:
                print(f"Recording failed to start: {exc}")
                return

            self.writer = csv.writer(self.file)
            self.writer.writerow(list(CSV_COLUMNS))

            self.recording = True
            self._last_seq = None
            self._frame_count = 0
            self._last_flush = time.monotonic()

        print("Recording:", filename)

    def add(self, data):
        """
        Append one acquisition frame to the recording.

        Ignores empty, malformed and duplicated frames. The
        file is flushed at most once per RECORDER_FLUSH_PERIOD_S:
        flushing after every frame forces a syscall on the
        render thread.

        """

        if not self.recording:
            return

        if not isinstance(data, dict):
            return

        if not isinstance(data.get("imu_data"), list):
            return

        seq = data.get("seq", data.get("timestamp"))
        timestamp = data.get("timestamp", 0)
        system = data.get("system", "")

        with self._lock:

            if not self.recording or self.writer is None:
                return

            if seq is not None and seq == self._last_seq:
                return
            self._last_seq = seq

            frame = {
                "seq": seq,
                "timestamp": timestamp,
                "system": system,
                "imu_data": [
                    {field: imu.get(field) for field in IMU_FIELDS}
                    for imu in data["imu_data"]
                    if isinstance(imu, dict)
                ],
            }

            epoch = time.time()

            self.writer.writerow(
                [
                    _format_datetime(epoch),
                    epoch,
                    timestamp,
                    system,

                    json.dumps(frame, separators=(",", ":")),
                ]
            )

            self._frame_count += 1

            now = time.monotonic()
            if now - self._last_flush >= RECORDER_FLUSH_PERIOD_S:
                self._last_flush = now
                self.file.flush()


# ----------------- Stop Recording ----------------


    def stop(self):
        """
        Stop the current recording.

        Flushes remaining data, closes the CSV file and
        disables recording. Does nothing when no recording is
        active.

        """
        with self._lock:
            was_recording = self.recording
            frames = self._frame_count
            self.recording = False

            if self.file:
                self.file.close()
                self.file = None
                self.writer = None

        if was_recording:
            print(f"Recording stopped ({frames} frames)")