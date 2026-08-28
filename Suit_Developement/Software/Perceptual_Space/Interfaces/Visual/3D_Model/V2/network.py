import time
import threading
import requests

from config import ESP32_IP, NETWORK_TIMEOUT


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
    motion capture data from the ESP32.

    A reboot is automatically detected when the ESP32
    timestamp becomes smaller than the previously received
    timestamp.

    """
    
    
# ---------------- Initialization -----------------


    def __init__(self, ip=ESP32_IP, timeout=NETWORK_TIMEOUT):
        """
        Poll one packet from the ESP32.
        
        Sends one HTTP request to the ESP32 and retrieves the
        latest acquisition packet.
        
        The function also detects an ESP32 reboot by checking
        whether the internal timestamp decreased.

        """
        
        self.url = "http://" + ip + "/data"
        self.timeout = timeout
        self._session = requests.Session()
        self._last_timestamp = None


# ------------------ Acquisition ------------------


    def poll(self):
        """
        Poll one packet from the ESP32.

        Sends one HTTP request to the ESP32 and retrieves the
        latest acquisition packet.
        
        The function also detects an ESP32 reboot by checking
        whether the internal timestamp decreased.
        
        """
        
        try:
            response = self._session.get(self.url, timeout=self.timeout)
            data = response.json()
        except requests.exceptions.Timeout:
            return None, TIMEOUT
        except Exception:
            return None, ERROR

        status = OK

        ts = data.get("timestamp") if isinstance(data, dict) else None
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
                 poll_interval=0.005):
        self._client = ESP32Client(ip, timeout)
        self._poll_interval = poll_interval

        self._lock = threading.Lock()
        self._latest = None
        self._status = ERROR
        self._reboot_pending = False
        self._last_success = 0.0

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
        
        Continuously polls the ESP32, updates the latest
        acquisition packet and monitors the communication
        status until the thread is stopped.

        """
        
        while self._running:
            try:
                data, status = self._client.poll()
            except Exception:
                data, status = None, ERROR

            with self._lock:
                self._status = status
                if status in (OK, REBOOT):
                    self._latest = data
                    self._last_success = time.time()
                    if status == REBOOT:
                        self._reboot_pending = True

            time.sleep(self._poll_interval)
            
            
# ------------------ Data Access ------------------


    def get(self):
        """
        Return the latest acquisition packet.
    
        Returns the most recent successfully received packet,
        its communication status and the age of the data.
    
        """
        
        with self._lock:
            if self._last_success:
                age = time.time() - self._last_success
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