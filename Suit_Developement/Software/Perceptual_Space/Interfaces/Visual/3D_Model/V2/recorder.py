import csv
import time
import threading


# ================================================
# RECORDER
# ================================================


class Recorder:
    """
    CSV recorder for motion capture sessions.

    Records all IMU data received from the ESP32 into a CSV file.
    One row is written for each IMU at every acquisition frame.

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


# ------------------- Recording -------------------


    def start(self):
        filename = "capture_" + str(int(time.time())) + ".csv"

        with self._lock:
            self.file = open(filename, "w", newline="")
            self.writer = csv.writer(self.file)
            self.writer.writerow(
                [
                    "timestamp",
                    
                    "body",
                    "qw",
                    "qx",
                    "qy",
                    "qz",
                    
                    "pitch",
                    "roll",
                    "heading",
                ]
            )
            self.recording = True

        print("Recording:", filename)

    def add(self, data):
        """
        Start a new CSV recording.
    
        Creates a new CSV file named with the current Unix timestamp,
        writes the column headers and enables recording.
    
        """
        
        if not self.recording:
            return

        if data is None:
            return

        if "imu_data" not in data:
            return

        timestamp = data.get("timestamp", 0)

        with self._lock:

            if not self.recording or self.writer is None:
                return

            for imu in data["imu_data"]:
                self.writer.writerow(
                    [
                        timestamp,
                        imu.get("body", ""),
                        imu.get("qw", ""),
                        imu.get("qx", ""),
                        imu.get("qy", ""),
                        imu.get("qz", ""),
                        imu.get("pitch", ""),
                        imu.get("roll", ""),
                        imu.get("heading", ""),
                    ]
                )

            self.file.flush()
            
       
# ----------------- Stop Recording ----------------


    def stop(self):
        """
        Stop the current recording.
    
        Flushes remaining data, closes the CSV file and disables
        recording.
    
        """
        with self._lock:
            self.recording = False

            if self.file:
                self.file.close()
                self.file = None
                self.writer = None

        print("Recording stopped")