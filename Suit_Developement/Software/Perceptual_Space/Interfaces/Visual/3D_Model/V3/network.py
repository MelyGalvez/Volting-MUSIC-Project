import time
import threading
import requests

from config import (
    ESP32_IP,
    NETWORK_TIMEOUT,
    POLL_HZ,
    ERROR_BACKOFF_MIN_S,
    ERROR_BACKOFF_MAX_S,
)


# ================================================
# NETWORK
# ================================================


OK = "ok"
TIMEOUT = "timeout"
ERROR = "error"
REBOOT = "reboot"


# ------------ ESP32 Synchronous Client -----------


class ESP32Client:
    """
    Synchronous ESP32 communication client.

    Performs a single HTTP request to retrieve the latest
    motion capture data from the ESP32 over a persistent
    keep-alive session.

    A reboot is automatically detected when the ESP32
    timestamp becomes smaller than the previously received
    timestamp.

    """


# ---------------- Initialization -----------------


    def __init__(self, ip=ESP32_IP, timeout=NETWORK_TIMEOUT):
        self.url = "http://" + ip + "/data"
        self.timeout = timeout
        self._session = requests.Session()
        self._last_timestamp = None

    def close(self):
        self._session.close()


# ------------------ Acquisition ------------------


    def poll(self):
        """
        Poll one packet from the ESP32.

        Sends one HTTP request to the ESP32 and retrieves the
        latest acquisition packet. Structurally invalid
        payloads are reported as errors so malformed data
        never reaches the pipeline.

        The function also detects an ESP32 reboot by checking
        whether the internal timestamp decreased.

        """

        try:
            response = self._session.get(self.url, timeout=self.timeout)

            if not response.ok:
                return None, ERROR

            data = response.json()
        except requests.exceptions.Timeout:
            return None, TIMEOUT
        except Exception:
            return None, ERROR

        if not isinstance(data, dict) or \
                not isinstance(data.get("imu_data"), list):
            return None, ERROR

        status = OK

        ts = data.get("timestamp")
        if ts is not None:
            if self._last_timestamp is not None and ts < self._last_timestamp:
                status = REBOOT
            self._last_timestamp = ts

        return data, status


# ----------- ESP32 Asynchronous Client -----------


class AsyncESP32Client:
    """
    Asynchronous ESP32 communication client.

    Runs the synchronous client inside a dedicated thread
    to prevent the rendering loop from blocking during
    network communication.

    The latest acquisition packet is stored internally
    and can be accessed safely from the rendering thread.

    """


# ---------------- Initialization -----------------


    def __init__(self, ip=ESP32_IP, timeout=NETWORK_TIMEOUT,
                 poll_hz=POLL_HZ):
        self._client = ESP32Client(ip, timeout)
        self._poll_interval = 1.0 / poll_hz

        self._lock = threading.Lock()
        self._latest = None
        self._status = ERROR
        self._reboot_pending = False

        # time.monotonic(): wall-clock (time.time) can jump
        # with NTP adjustments and corrupt age computations.
        self._last_success = None

        self._running = False
        self._thread = None


# --------------- Thread Management ---------------


    def start(self):
        """
        Start the acquisition thread.

        Launches the background thread responsible for
        continuously polling the ESP32.

        """

        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        """
        Background acquisition loop.

        Continuously polls the ESP32 and updates the latest
        acquisition packet. Failed requests back off
        exponentially so a rebooting ESP32 is not hammered
        while it recovers.

        """

        backoff = ERROR_BACKOFF_MIN_S

        while self._running:
            try:
                data, status = self._client.poll()
            except Exception:
                data, status = None, ERROR

            with self._lock:
                self._status = status
                if status in (OK, REBOOT):
                    self._latest = data
                    self._last_success = time.monotonic()
                    if status == REBOOT:
                        self._reboot_pending = True

            if status in (OK, REBOOT):
                backoff = ERROR_BACKOFF_MIN_S
                time.sleep(self._poll_interval)
            else:
                time.sleep(backoff)
                backoff = min(backoff * 2.0, ERROR_BACKOFF_MAX_S)


# ------------------ Data Access ------------------


    def get(self):
        """
        Return the latest acquisition packet.

        Returns the most recent successfully received packet,
        its communication status and the age of the data.

        """

        with self._lock:
            if self._last_success is not None:
                age = time.monotonic() - self._last_success
            else:
                age = float("inf")
            return self._latest, self._status, age

    def take_reboot(self):
        """
        Check whether a reboot occurred.

        Returns True exactly once after an ESP32 reboot has
        been detected, then clears the internal reboot flag.

        """
        with self._lock:
            if self._reboot_pending:
                self._reboot_pending = False
                return True
            return False


# ------------------- Shutdown --------------------


    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._client.close()
