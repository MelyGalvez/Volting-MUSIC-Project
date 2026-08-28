import json
import threading
import time

import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TOPIC,
    MQTT_QOS,
    MQTT_KEEPALIVE_S,
    MQTT_RECONNECT_MIN_S,
    MQTT_RECONNECT_MAX_S,
)


# ==========================================
# NETWORK
# ==========================================


OK = "ok"
ERROR = "error"
REBOOT = "reboot"


# -------- MQTT Acquisition Client ---------


class AsyncMQTTClient:
    """
    Asynchronous MQTT acquisition client.

    Subscribes to the topic the bridge publishes the suit
    snapshots on and keeps the latest packet available to
    the rendering thread. paho runs its network loop in a
    dedicated thread, so the render loop never blocks on
    the broker, and reconnection is automatic.

    Structurally invalid payloads are rejected so malformed
    data never reaches the pipeline.

    A reboot is automatically detected when the ESP32
    timestamp becomes smaller than the previously received
    timestamp.

    """


# ------------- Initialization -------------


    def __init__(self, host=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT,
                 topic=MQTT_TOPIC):
        self.host = host
        self.port = port
        self.topic = topic

        self._lock = threading.Lock()
        self._latest = None
        self._status = ERROR
        self._reboot_pending = False
        self._last_timestamp = None

        self._last_success = None

        self._running = False
        self._client = self._create_client()

    def _create_client(self):
        """
        Create the paho client with automatic reconnection.

        An empty client id lets the broker assign a unique one,
        so several viewers never kick each other off the topic.

        """

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="",
            protocol=mqtt.MQTTv311,
        )

        client.reconnect_delay_set(
            min_delay=MQTT_RECONNECT_MIN_S,
            max_delay=MQTT_RECONNECT_MAX_S,
        )

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        return client


# ------------ Broker Callbacks ------------


    def _on_connect(self, client, userdata, flags, reason_code,
                    properties):
        """
        Subscribe once the broker has accepted the connection.

        Subscribing from this callback rather than once at
        startup is what makes the subscription survive every
        later reconnection.

        """

        if reason_code.is_failure:
            print(
                f"MQTT connection to {self.host}:{self.port} "
                f"refused: {reason_code}"
            )
            return

        client.subscribe(self.topic, qos=MQTT_QOS)

        print(
            f"Connected to mqtt://{self.host}:{self.port} "
            f"(topic '{self.topic}')"
        )

    def _on_disconnect(self, client, userdata, flags, reason_code,
                       properties):
        """
        Flag the loss; paho reconnects on its own.

        The last packet is deliberately kept: the age returned
        by get() keeps growing, so the caller sees the data go
        stale and holds the last pose instead of the skeleton
        snapping back to the T-pose.

        """

        with self._lock:
            self._status = ERROR

        if reason_code != 0:
            print(
                f"MQTT connection lost ({reason_code}); "
                "reconnecting automatically"
            )

    def _on_message(self, client, userdata, message):
        """
        Store one snapshot received from the broker.

        Runs on paho's network thread, so every access to the
        shared state is guarded by the lock the render thread
        uses in get().

        """

        try:
            data = json.loads(message.payload)
        except (ValueError, UnicodeDecodeError):
            with self._lock:
                self._status = ERROR
            return

        if not isinstance(data, dict) or \
                not isinstance(data.get("imu_data"), list):
            with self._lock:
                self._status = ERROR
            return

        status = OK
        ts = data.get("timestamp")

        with self._lock:
            if ts is not None:
                if self._last_timestamp is not None and \
                        ts < self._last_timestamp:
                    status = REBOOT
                    self._reboot_pending = True
                self._last_timestamp = ts

            self._latest = data
            self._status = status
            self._last_success = time.monotonic()


# ----------- Thread Management ------------


    def start(self):
        """
        Start the acquisition.

        connect_async() plus loop_start(): the background
        thread performs the initial connection and every later
        reconnection, so startup never blocks on an absent
        broker.

        """

        if self._running:
            return

        self._running = True

        self._client.connect_async(
            self.host, self.port, MQTT_KEEPALIVE_S
        )
        self._client.loop_start()


# -------------- Data Access ---------------


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


# ---------------- Shutdown ----------------


    def stop(self):
        if not self._running:
            return

        self._running = False

        self._client.disconnect()
        self._client.loop_stop()