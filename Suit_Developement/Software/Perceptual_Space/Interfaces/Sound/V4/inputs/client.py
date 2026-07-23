# =================================================
# SUIT CLIENT
#
# Background HTTP acquisition of the ESP32 /data
# endpoint (PROTOCOL.md v2). Same proven shape as
# the Sound_V2 client — keep-alive session, timeout,
# exponential backoff, structural validation — plus
# one addition that Sound_Track's latency depends
# on: a callback invoked from the polling thread the
# moment a *new* frame (fresh seq) arrives, so
# gesture detection runs immediately instead of
# waiting for a UI tick.
# =================================================

import threading
import time

import requests


class SuitClient:
    """
    Threaded poller. on_frame(packet, mono_received) fires
    once per new sensor frame, in the polling thread —
    keep the handler fast (gesture detection + engine
    dispatch are sub-millisecond). Exceptions raised by
    the handler are contained and rate-limit logged: the
    acquisition loop must survive anything.
    """

    def __init__(
        self,
        base_url,
        *,
        timeout_s,
        poll_hz,
        backoff_min_s,
        backoff_max_s,
        on_frame=None,
    ):
        self._url = base_url.rstrip("/") + "/data"
        self._timeout = timeout_s
        self._poll_interval = 1.0 / poll_hz
        self._backoff_min = backoff_min_s
        self._backoff_max = backoff_max_s
        self._on_frame = on_frame

        self._session = requests.Session()

        self._lock = threading.Lock()
        self._latest = None
        self._last_success = None      # time.monotonic()
        self._connected = False

        self._last_frame_id = None
        self._last_handler_log = 0.0

        self._running = False
        self._thread = None


# ------------------ Validation -------------------


    @staticmethod
    def _validate(data):
        """
        Structural validation: malformed payloads are
        dropped here so downstream code never sees them.
        """

        return isinstance(data, dict) and \
            isinstance(data.get("imu_data"), list)


# --------------- Thread management ----------------


    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="suit-client"
        )
        self._thread.start()

    def stop(self):
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        self._session.close()

    def _loop(self):
        backoff = self._backoff_min

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
                        now = time.monotonic()

                        with self._lock:
                            self._latest = data
                            self._last_success = now
                            self._connected = True

                        self._deliver(data, now)

            except Exception:
                pass

            if ok:
                backoff = self._backoff_min
                time.sleep(self._poll_interval)
            else:
                with self._lock:
                    self._connected = False

                time.sleep(backoff)
                backoff = min(backoff * 2.0, self._backoff_max)

    def _deliver(self, data, now):
        """
        Invoke on_frame exactly once per sensor frame:
        polling faster than the ~100 Hz scan rate must not
        re-run detection on duplicate data.
        """

        if self._on_frame is None:
            return

        frame_id = data.get("seq", data.get("timestamp"))

        if frame_id is not None and \
                frame_id == self._last_frame_id:
            return

        self._last_frame_id = frame_id

        try:
            self._on_frame(data, now)
        except Exception as exc:
            if now - self._last_handler_log > 1.0:
                self._last_handler_log = now
                print(f"[frame handler error] {exc!r}")


# ------------------ Data access -------------------


    def get(self):
        """
        Return (data, age_seconds, connected) — the latest
        valid packet (or None) and how long ago it arrived.
        For the UI and the staleness watchdog.
        """

        with self._lock:
            if self._last_success is None:
                age = float("inf")
            else:
                age = time.monotonic() - self._last_success

            return self._latest, age, self._connected
