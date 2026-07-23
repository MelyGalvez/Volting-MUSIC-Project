# =================================================
# CLIENT
#
# Background HTTP acquisition. The main (Tk) thread
# never blocks on the network: it only reads the
# latest snapshot under a lock. A requests.Session
# keeps one TCP connection alive; the previous
# per-poll connection churn exhausted the ESP32's
# small LWIP socket pool during long sessions.
# =================================================

import threading
import time

import requests

import config


class SuitClient:
    """
    Threaded poller of the ESP32 /data endpoint.

    Exposes the latest validated packet, its age and the
    connection status. Failed requests back off
    exponentially so a rebooting ESP32 is not hammered.
    """

    def __init__(
        self,
        base_url=config.ESP32_BASE_URL,
        timeout=config.HTTP_TIMEOUT_S,
        poll_hz=config.POLL_HZ,
    ):
        self._url = base_url.rstrip("/") + "/data"
        self._timeout = timeout
        self._poll_interval = 1.0 / poll_hz

        self._session = requests.Session()

        self._lock = threading.Lock()
        self._latest = None
        self._last_success = None    # time.monotonic()
        self._connected = False

        self._running = False
        self._thread = None


# ------------------ Validation -------------------


    @staticmethod
    def _validate(data):
        """
        Structural validation: a packet must be a dict with
        an imu_data list. Malformed payloads are dropped
        here so downstream code never sees them.
        """

        if not isinstance(data, dict):
            return False

        if not isinstance(data.get("imu_data"), list):
            return False

        return True


# --------------- Thread management ----------------


    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        self._session.close()

    def _loop(self):
        backoff = config.ERROR_BACKOFF_MIN_S

        while self._running:
            ok = False

            try:
                response = self._session.get(
                    self._url, timeout=self._timeout
                )

                if response.ok:
                    data = response.json()

                    if self._validate(data):
                        ok = True

                        with self._lock:
                            self._latest = data
                            self._last_success = time.monotonic()
                            self._connected = True

            except Exception:
                pass

            if ok:
                backoff = config.ERROR_BACKOFF_MIN_S
                time.sleep(self._poll_interval)
            else:
                with self._lock:
                    self._connected = False

                time.sleep(backoff)
                backoff = min(
                    backoff * 2.0,
                    config.ERROR_BACKOFF_MAX_S,
                )


# ------------------ Data access -------------------


    def get(self):
        """
        Return (data, age_seconds, connected).

        data is the most recent valid packet (or None),
        age_seconds how long ago it was received.
        """

        with self._lock:
            if self._last_success is None:
                age = float("inf")
            else:
                age = time.monotonic() - self._last_success

            return self._latest, age, self._connected
