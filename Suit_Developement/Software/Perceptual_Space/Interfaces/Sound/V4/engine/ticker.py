# =================================================
# TICKER
#
# One background thread with two jobs, both off the
# UI thread so a frozen window can never delay a
# note-off or leave notes ringing after data loss:
#
#   1. engine.process() — executes the release
#      mode's scheduled note-offs (2.5 ms resolution,
#      inaudible jitter)
#   2. a housekeeping callback wired by main.py —
#      the staleness/system watchdog that suspends
#      the engine when suit data stops flowing
# =================================================

import threading
import time


class Ticker:

    def __init__(self, engine, period_s=0.0025, housekeeping=None):
        self._engine = engine
        self._period = period_s
        self._housekeeping = housekeeping

        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="ticker"
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._engine.process()

                if self._housekeeping is not None:
                    self._housekeeping()
            except Exception as exc:
                # The ticker must survive anything: it is
                # the safety net that silences stuck notes.
                print(f"[ticker error] {exc!r}")

            self._stop.wait(self._period)
