import csv
import time
import threading

from config import RECORDER_FLUSH_PERIOD_S


# ================================================
# RECORDER
# ================================================


class Recorder:
    """
    CSV recorder for motion capture sessions.

    Records all IMU data received from the ESP32 into a CSV file.
    One row is written for each IMU at every acquisition frame.
    Duplicate frames (same sequence number) are skipped so the
    recording reflects the true sensor rate, not the render rate.

    """


# ----------------- Initialization ----------------


    def __init__(self):
        """
        Initialize the recorder.

        Creates an inactive recorder and initializes the internal
        CSV writer, file handle and thread lock.

        """

        self.file = None
        self.writer = None
        self.recording = False
        self._lock = threading.Lock()
        self._last_seq = None
        self._last_flush = 0.0


# ------------------- Recording -------------------


    def start(self):
        """
        Start a new CSV recording.

        Creates a new CSV file named with the current local time,
        writes the column headers and enables recording.

        """

        filename = time.strftime("capture_%Y%m%d_%H%M%S.csv")

        with self._lock:
            if self.recording:
                return

            try:
                self.file = open(filename, "w", newline="")
            except OSError as exc:
                print(f"Recording failed to start: {exc}")
                return

            self.writer = csv.writer(self.file)
            self.writer.writerow(
                [
                    "seq",
                    "timestamp",

                    "body",
                    "ok",

                    "qw",
                    "qx",
                    "qy",
                    "qz",

                    "heading",
                    "pitch",
                    "roll",
                ]
            )
            self.recording = True
            self._last_seq = None
            self._last_flush = time.monotonic()

        print("Recording:", filename)

    def add(self, data):
        """
        Append one acquisition frame to the recording.

        Ignores empty, malformed and duplicated frames. The file
        is flushed at most once per RECORDER_FLUSH_PERIOD_S: the
        previous per-frame flush forced a syscall on the render
        thread for every frame.

        """

        if not self.recording:
            return

        if not isinstance(data, dict):
            return

        if "imu_data" not in data:
            return

        seq = data.get("seq", data.get("timestamp"))
        timestamp = data.get("timestamp", 0)

        with self._lock:

            if not self.recording or self.writer is None:
                return

            if seq is not None and seq == self._last_seq:
                return
            self._last_seq = seq

            for imu in data["imu_data"]:
                self.writer.writerow(
                    [
                        seq,
                        timestamp,
                        imu.get("body", ""),
                        imu.get("ok", ""),
                        imu.get("qw", ""),
                        imu.get("qx", ""),
                        imu.get("qy", ""),
                        imu.get("qz", ""),
                        imu.get("heading", ""),
                        imu.get("pitch", ""),
                        imu.get("roll", ""),
                    ]
                )

            now = time.monotonic()
            if now - self._last_flush >= RECORDER_FLUSH_PERIOD_S:
                self._last_flush = now
                self.file.flush()


# ----------------- Stop Recording ----------------


    def stop(self):
        """
        Stop the current recording.

        Flushes remaining data, closes the CSV file and disables
        recording. Does nothing when no recording is active.

        """
        with self._lock:
            was_recording = self.recording
            self.recording = False

            if self.file:
                self.file.close()
                self.file = None
                self.writer = None

        if was_recording:
            print("Recording stopped")
