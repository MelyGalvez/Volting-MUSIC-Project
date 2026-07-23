#!/usr/bin/env python3
"""ESP32 Motion Suit -> MQTT bridge.

Continuously downloads the acquisition snapshot JSON from the
suit's HTTP endpoint, validates it, and republishes the exact
same payload (byte for byte) to a public MQTT broker:

    ESP32  (http://192.168.4.1/data)
      |
      |  HTTP GET (requests, retried with backoff)
      v
    this bridge
      |
      |  MQTT publish (paho-mqtt, automatic reconnection)
      v
    mqtt://test.mosquitto.org:1883   topic: motion_suit/data

The bridge never alters the payload: the raw HTTP body is
published as-is, and JSON parsing is used for validation only.
Stop it any time with Ctrl+C; it shuts down cleanly.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time

import paho.mqtt.client as mqtt
import requests


# ----------------------------------------------------------------------
# Configuration
#
# The constants below are the operational defaults. Each one can be
# overridden through an environment variable of the same name, which is
# handy for testing against a mock endpoint or a private broker without
# editing the code.
# ----------------------------------------------------------------------

#: HTTP endpoint of the ESP32 suit (WiFi AP "ESP32_Test").
ESP32_DATA_URL = os.environ.get(
    "ESP32_DATA_URL", "http://192.168.4.1/data"
)

#: Seconds between two polls while the suit is reachable. 0.1 s = 10 Hz,
#: a polite publish rate for a shared public broker while still tracking
#: the suit closely (the firmware refreshes its snapshot every scan).
POLL_INTERVAL_S = float(os.environ.get("POLL_INTERVAL_S", "0.1"))

#: Timeout of a single HTTP request (connect + read).
HTTP_TIMEOUT_S = float(os.environ.get("HTTP_TIMEOUT_S", "2.0"))

#: Exponential backoff bounds applied between failed HTTP attempts, so a
#: powered-off suit is retried forever without hammering the network.
HTTP_BACKOFF_MIN_S = 0.5
HTTP_BACKOFF_MAX_S = 10.0

#: Public test broker: no authentication, no TLS.
MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "192.168.56.1")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "motion_suit/data")

#: Fire-and-forget delivery: live motion data is only useful fresh, so a
#: lost sample is preferable to a delayed one.
MQTT_QOS = 0
MQTT_RETAIN = False

MQTT_KEEPALIVE_S = 30

#: Bounds of paho's built-in reconnect backoff (seconds).
MQTT_RECONNECT_MIN_S = 1
MQTT_RECONNECT_MAX_S = 30

#: Top-level keys every valid suit snapshot carries (wire protocol v2).
REQUIRED_SNAPSHOT_KEYS = ("seq", "timestamp", "system", "imu_data")

#: Period of the aggregated statistics log line.
STATS_PERIOD_S = 10.0

#: Longest single wait: waiting in short slices keeps Ctrl+C responsive
#: on every platform (Windows delivers signals between waits).
MAX_WAIT_SLICE_S = 0.5


LOGGER = logging.getLogger("bridge")


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------


def configure_logging() -> None:
    """Configure a timestamped console logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(message)s",
        datefmt="%H:%M:%S",
    )


# ----------------------------------------------------------------------
# Shutdown handling
# ----------------------------------------------------------------------


def install_signal_handlers(stop_event: threading.Event) -> None:
    """Translate SIGINT/SIGTERM into a stop request.

    The handlers only set an event; the main loop notices it at its
    next wait slice and unwinds through the normal cleanup path.
    """

    def _handle(signum: int, _frame) -> None:
        LOGGER.info(
            "Received %s, shutting down...",
            signal.Signals(signum).name,
        )
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            # Not the main thread or unsupported on this platform;
            # KeyboardInterrupt still covers Ctrl+C.
            pass


def interruptible_wait(stop_event: threading.Event, seconds: float) -> None:
    """Sleep up to `seconds`, returning early when a stop is requested.

    Waits in short slices so pending signals are serviced promptly even
    on platforms that cannot interrupt a long blocking wait.
    """
    deadline = time.monotonic() + seconds

    while not stop_event.is_set():
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            return

        stop_event.wait(min(remaining, MAX_WAIT_SLICE_S))


# ----------------------------------------------------------------------
# HTTP side (ESP32)
# ----------------------------------------------------------------------


def create_http_session() -> requests.Session:
    """Create the pooled HTTP session used for every poll.

    A single session reuses the TCP connection to the ESP32, which
    matters at 10 Hz against a small embedded web server.
    """
    return requests.Session()


def fetch_snapshot(session: requests.Session) -> bytes | None:
    """Fetch one snapshot from the ESP32.

    Returns the raw response body on success, None on any failure
    (network error, timeout, or non-200 status). Never raises: the
    caller decides how to back off.
    """
    try:
        response = session.get(ESP32_DATA_URL, timeout=HTTP_TIMEOUT_S)
        response.raise_for_status()
        return response.content
    except requests.RequestException as exc:
        LOGGER.debug("HTTP request failed: %s", exc)
        return None


def validate_snapshot(payload: bytes) -> dict | None:
    """Parse and structurally validate one snapshot payload.

    Returns the parsed document (used for logging/statistics only —
    the published payload stays the original bytes), or None when the
    payload is not a plausible suit snapshot.
    """
    try:
        snapshot = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        LOGGER.warning("Discarding payload: invalid JSON (%s)", exc)
        return None

    if not isinstance(snapshot, dict):
        LOGGER.warning("Discarding payload: root is not an object")
        return None

    missing = [
        key for key in REQUIRED_SNAPSHOT_KEYS if key not in snapshot
    ]

    if missing:
        LOGGER.warning(
            "Discarding payload: missing keys %s", ", ".join(missing)
        )
        return None

    if not isinstance(snapshot["imu_data"], list):
        LOGGER.warning("Discarding payload: imu_data is not a list")
        return None

    return snapshot


# ----------------------------------------------------------------------
# MQTT side (broker)
# ----------------------------------------------------------------------


def create_mqtt_client() -> mqtt.Client:
    """Create the MQTT client with automatic reconnection enabled.

    The network loop runs in paho's background thread; once started it
    keeps retrying the connection (with bounded exponential backoff)
    for the whole lifetime of the bridge.
    """
    # Empty client id: the broker assigns a unique one, so several
    # bridge instances never kick each other off the shared broker.
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="",
        protocol=mqtt.MQTTv311,
    )

    client.reconnect_delay_set(
        min_delay=MQTT_RECONNECT_MIN_S,
        max_delay=MQTT_RECONNECT_MAX_S,
    )

    client.on_connect = _on_mqtt_connect
    client.on_disconnect = _on_mqtt_disconnect

    return client


def _on_mqtt_connect(client, userdata, flags, reason_code, properties):
    """Log the outcome of every (re)connection attempt."""
    if reason_code.is_failure:
        LOGGER.warning(
            "MQTT connection to %s:%d refused: %s",
            MQTT_BROKER_HOST, MQTT_BROKER_PORT, reason_code,
        )
    else:
        LOGGER.info(
            "Connected to mqtt://%s:%d (topic '%s', QoS %d)",
            MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC, MQTT_QOS,
        )


def _on_mqtt_disconnect(client, userdata, flags, reason_code, properties):
    """Log unexpected drops; paho reconnects on its own."""
    if reason_code != 0:
        LOGGER.warning(
            "MQTT connection lost (%s); reconnecting automatically",
            reason_code,
        )


def publish_snapshot(client: mqtt.Client, payload: bytes) -> bool:
    """Publish one raw payload to the bridge topic.

    Returns True when the message was handed to the network layer.
    With QoS 0 a publish while disconnected is dropped by design;
    that shows up as False and is counted by the caller.
    """
    result = client.publish(
        MQTT_TOPIC, payload, qos=MQTT_QOS, retain=MQTT_RETAIN
    )

    return result.rc == mqtt.MQTT_ERR_SUCCESS


# ----------------------------------------------------------------------
# Bridge loop
# ----------------------------------------------------------------------


def run_bridge(
    session: requests.Session,
    client: mqtt.Client,
    stop_event: threading.Event,
) -> None:
    """Poll the suit and republish until a stop is requested."""
    esp32_online = False
    consecutive_failures = 0
    backoff_s = HTTP_BACKOFF_MIN_S

    published = 0
    http_failures = 0
    invalid_payloads = 0
    mqtt_drops = 0

    last_seq: int | None = None
    last_system = "unknown"
    stats_started = time.monotonic()
    stats_published = 0

    while not stop_event.is_set():
        payload = fetch_snapshot(session)

        # ---------------- HTTP failure path ----------------

        if payload is None:
            http_failures += 1
            consecutive_failures += 1

            if esp32_online or consecutive_failures == 1:
                LOGGER.warning(
                    "ESP32 unreachable at %s; retrying every %.1f-%.1f s",
                    ESP32_DATA_URL, backoff_s, HTTP_BACKOFF_MAX_S,
                )

            esp32_online = False

            interruptible_wait(stop_event, backoff_s)
            backoff_s = min(backoff_s * 2.0, HTTP_BACKOFF_MAX_S)
            continue

        if not esp32_online:
            if consecutive_failures:
                LOGGER.info(
                    "ESP32 link up after %d failed attempt(s)",
                    consecutive_failures,
                )
            else:
                LOGGER.info("ESP32 link established")

        esp32_online = True
        consecutive_failures = 0
        backoff_s = HTTP_BACKOFF_MIN_S

        # ---------------- Validate and publish -------------

        snapshot = validate_snapshot(payload)

        if snapshot is None:
            invalid_payloads += 1
        else:
            seq = snapshot.get("seq")
            last_system = snapshot.get("system", "unknown")

            # Protocol v2: a decreasing seq means the suit rebooted.
            if (
                isinstance(seq, int)
                and isinstance(last_seq, int)
                and seq < last_seq
            ):
                LOGGER.info(
                    "ESP32 reboot detected (seq %d -> %d)", last_seq, seq
                )

            last_seq = seq if isinstance(seq, int) else last_seq

            if publish_snapshot(client, payload):
                published += 1
                stats_published += 1
            else:
                mqtt_drops += 1

        # ---------------- Periodic statistics ---------------

        elapsed = time.monotonic() - stats_started

        if elapsed >= STATS_PERIOD_S:
            LOGGER.info(
                "published=%d (%.1f/s) http_failures=%d "
                "mqtt_drops=%d invalid=%d last_seq=%s system=%s",
                published,
                stats_published / elapsed,
                http_failures,
                mqtt_drops,
                invalid_payloads,
                last_seq,
                last_system,
            )
            stats_started = time.monotonic()
            stats_published = 0

        interruptible_wait(stop_event, POLL_INTERVAL_S)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def main() -> int:
    """Run the bridge until interrupted; always clean up."""
    configure_logging()

    LOGGER.info("Motion Suit MQTT bridge starting")
    LOGGER.info("  source : GET %s", ESP32_DATA_URL)
    LOGGER.info(
        "  sink   : mqtt://%s:%d  topic '%s'",
        MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC,
    )

    stop_event = threading.Event()
    install_signal_handlers(stop_event)

    session = create_http_session()
    client = create_mqtt_client()

    # connect_async + loop_start: the background thread performs the
    # initial connection and every later reconnection, so the polling
    # loop never blocks on broker availability.
    client.connect_async(
        MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE_S
    )
    client.loop_start()

    try:
        run_bridge(session, client, stop_event)
    except KeyboardInterrupt:
        LOGGER.info("Interrupted, shutting down...")
    finally:
        client.disconnect()
        client.loop_stop()
        session.close()
        LOGGER.info("Bridge stopped cleanly.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
