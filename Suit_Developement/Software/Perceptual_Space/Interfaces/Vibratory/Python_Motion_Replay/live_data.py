"""Live link with the suit: one MQTT connection, both directions.

    motion_suit/data    <-- the V4 bridge publishes the suit snapshots
    motion_suit/haptic  --> this program publishes vibration commands

Everything network related runs in the paho background thread. The
main thread only reads the last known state, under a lock, so the
terminal interface can never slow the reception down.

The parser accepts exactly the packet the firmware builds
(Arduino_Suit_ESP32_Get_Data_V4/json.cpp, protocol v2). Anything else -
truncated JSON, wrong encoding, missing keys, a quaternion of four
zeros - is counted and dropped: no value is ever invented.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field

import numpy as np
import paho.mqtt.client as mqtt

import config
import orientation
from choreography import IMU_NAMES

#: Top level keys of a valid snapshot (same test as the V4 bridge).
REQUIRED_KEYS = ("seq", "timestamp", "system", "imu_data")


@dataclass
class LiveImu:
    """Last known state of one sensor."""

    quaternion: np.ndarray          # filtered orientation
    raw: np.ndarray                 # unfiltered, as received
    gravity: np.ndarray | None      # smoothed gravity, sensor frame
    updated_s: float                # local time of the last valid read


@dataclass
class LiveState:
    """Snapshot of the suit as this program currently knows it."""

    received_s: float
    esp_timestamp_ms: float | None
    seq: float | None
    system: str
    imus: dict[str, LiveImu] = field(default_factory=dict)

    def age_s(self, now: float | None = None) -> float:
        return (time.monotonic() if now is None else now) - self.received_s

    def fresh_imus(self, now: float | None = None) -> dict[str, LiveImu]:
        """IMUs whose last valid reading is recent enough to be trusted."""
        moment = time.monotonic() if now is None else now

        return {
            name: imu
            for name, imu in self.imus.items()
            if moment - imu.updated_s <= config.STALE_DATA_TIMEOUT_S
        }


class MqttLink:
    """Subscribes to the data topic and publishes haptic commands."""

    def __init__(
        self,
        host: str = config.MQTT_BROKER_HOST,
        port: int = config.MQTT_BROKER_PORT,
        data_topic: str = config.MQTT_DATA_TOPIC,
    ) -> None:
        self.host = host
        self.port = port
        self.data_topic = data_topic

        self.message_count = 0
        self.invalid_count = 0
        self.published_count = 0
        self.last_message_s: float | None = None

        self._lock = threading.Lock()
        self._state: LiveState | None = None
        self._filtered: dict[str, LiveImu] = {}

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="",
            clean_session=True,
        )

        self._client.reconnect_delay_set(
            min_delay=config.MQTT_RECONNECT_MIN_S,
            max_delay=config.MQTT_RECONNECT_MAX_S,
        )

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    # -- lifecycle -----------------------------------------------------

    def start(self) -> None:
        """Connect in the background; never blocks, never raises."""
        self._client.connect_async(
            self.host, self.port, config.MQTT_KEEPALIVE_S
        )
        self._client.loop_start()

    def stop(self) -> None:
        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()

    @property
    def connected(self) -> bool:
        return bool(self._client.is_connected())

    # -- reading -------------------------------------------------------

    def state(self) -> LiveState | None:
        """Last known suit state (or None while nothing has arrived)."""
        with self._lock:
            return self._state

    def reset_filter(self) -> None:
        """Forget the filtered orientations (after a long interruption)."""
        with self._lock:
            self._filtered = {}

    # -- writing -------------------------------------------------------

    def publish(self, topic: str, payload: str) -> bool:
        """Send one message; returns False when it could not be queued."""
        try:
            result = self._client.publish(
                topic, payload, qos=config.MQTT_QOS, retain=False
            )
        except Exception:
            return False

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.published_count += 1
            return True

        return False

    # -- callbacks (paho thread) ---------------------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            # Subscribing on every connect restores the subscription
            # after an automatic reconnection.
            client.subscribe(self.data_topic, qos=config.MQTT_QOS)

    def _on_message(self, client, userdata, message):
        # Runs in the network thread: no exception may escape, or the
        # loop would die and the suit data would stop arriving.
        try:
            self._handle_payload(message.payload)
        except Exception:
            self.invalid_count += 1

    # -- parsing -------------------------------------------------------

    def _handle_payload(self, payload: bytes) -> None:
        snapshot = _parse_snapshot(payload)

        if snapshot is None:
            self.invalid_count += 1
            return

        now = time.monotonic()

        with self._lock:
            for frame in snapshot.get("imu_data", []):
                self._update_imu(frame, now)

            state = LiveState(
                received_s=now,
                esp_timestamp_ms=_number(snapshot.get("timestamp")),
                seq=_number(snapshot.get("seq")),
                system=str(snapshot.get("system") or ""),
                imus=dict(self._filtered),
            )

            self._state = state
            self.message_count += 1
            self.last_message_s = now

    def _update_imu(self, frame, now: float) -> None:
        if not isinstance(frame, dict):
            return

        name = frame.get("body")

        if name not in IMU_NAMES:
            return

        # A sensor the firmware could not read keeps its previous
        # entry, which then simply ages out of fresh_imus().
        if frame.get("ok") is not True:
            return

        values = [
            frame.get("qw"), frame.get("qx"),
            frame.get("qy"), frame.get("qz"),
        ]

        if not orientation.is_valid(values):
            return

        raw = orientation.canonical(orientation.normalize(values))

        previous = self._filtered.get(name)

        if previous is None:
            filtered = raw
        else:
            filtered = orientation.slerp(
                previous.quaternion, raw, config.FILTER_ALPHA
            )

        self._filtered[name] = LiveImu(
            quaternion=filtered,
            raw=raw,
            gravity=_smooth_gravity(frame.get("gravity"), previous),
            updated_s=now,
        )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _parse_snapshot(payload: bytes):
    """Return the snapshot object, or None when the payload is unusable."""
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

    if not isinstance(snapshot.get("imu_data"), list):
        return None

    return snapshot


def _number(value):
    if isinstance(value, bool):
        return None

    return value if isinstance(value, (int, float)) else None


def _smooth_gravity(measurement, previous: LiveImu | None):
    """Light averaging of the gravity vector, for a steady direction."""
    if not isinstance(measurement, dict):
        return previous.gravity if previous is not None else None

    values = [
        _number(measurement.get("x")),
        _number(measurement.get("y")),
        _number(measurement.get("z")),
    ]

    if any(value is None for value in values):
        return previous.gravity if previous is not None else None

    vector = np.array(values, dtype=float)

    if previous is None or previous.gravity is None:
        return vector

    alpha = config.FILTER_ALPHA

    return (1.0 - alpha) * previous.gravity + alpha * vector
