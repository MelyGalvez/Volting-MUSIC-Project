# Python MQTT Bridge

Relays the Volting Motion Suit's sensor snapshots from the ESP32's HTTP
endpoint to a public MQTT broker, byte for byte.

```
ESP32 suit                      this bridge                     MQTT broker
+-----------------+   HTTP GET  +-------------+   publish   +-------------------------+
| 8x BNO055 + 2   | ----------> | main.py     | ----------> | test.mosquitto.org:1883 |
| piezo triggers  |  /data JSON | (validate,  |  QoS 0      | topic: motion_suit/data |
| 192.168.4.1     |             |  republish) |             |                         |
+-----------------+             +-------------+             +-------------------------+
```

The published payload is the exact JSON returned by the suit — the bridge
parses it only to validate it, then forwards the original bytes unmodified.

## Requirements

- Python 3.10 or newer
- Network access to **both** sides at the same time:
  - the suit's WiFi access point `ESP32_Test` (the suit lives at
    `http://192.168.4.1`), and
  - the internet, to reach `test.mosquitto.org`.

  The ESP32 access point provides no internet, so in practice the machine
  needs two interfaces (for example Ethernet or a second WiFi adapter for
  the internet, plus WiFi to the suit).

## Installation

```
cd Python_MQTT_Bridge
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Dependencies (pinned in `requirements.txt`):

| Package     | Purpose                          |
| ----------- | -------------------------------- |
| `requests`  | HTTP polling of the ESP32        |
| `paho-mqtt` | MQTT publishing (v2 API)         |

## Running

```
python main.py
```

Typical output:

```
12:00:01 [INFO   ] Motion Suit MQTT bridge starting
12:00:01 [INFO   ]   source : GET http://192.168.4.1/data
12:00:01 [INFO   ]   sink   : mqtt://test.mosquitto.org:1883  topic 'motion_suit/data'
12:00:01 [INFO   ] Connected to mqtt://test.mosquitto.org:1883 (topic 'motion_suit/data', QoS 0)
12:00:11 [INFO   ] published=98 (9.8/s) http_failures=0 mqtt_drops=0 invalid=0 last_seq=15873 system=ready
```

Stop with **Ctrl+C**; the bridge disconnects from the broker and exits
cleanly.

To watch the relayed data from anywhere:

```
mosquitto_sub -h test.mosquitto.org -t motion_suit/data
```

## Broker and topic

| Setting  | Value                        |
| -------- | ---------------------------- |
| Broker   | `mqtt://test.mosquitto.org`  |
| Port     | `1883`                       |
| Topic    | `motion_suit/data`           |
| Auth     | none                         |
| TLS      | none                         |
| QoS      | `0`                          |
| Retain   | `False`                      |

> `test.mosquitto.org` is a shared, public, unauthenticated broker:
> anything published there is visible to anyone and delivery is best
> effort. Use it for development and demos, not for anything sensitive.

## Configuration

Defaults live as constants at the top of `main.py`. Each can be
overridden with an environment variable of the same name, e.g.:

| Variable           | Default                       | Meaning                        |
| ------------------ | ----------------------------- | ------------------------------ |
| `ESP32_DATA_URL`   | `http://192.168.4.1/data`     | Suit snapshot endpoint         |
| `POLL_INTERVAL_S`  | `0.1`                         | Delay between polls (seconds)  |
| `HTTP_TIMEOUT_S`   | `2.0`                         | Per-request HTTP timeout       |
| `MQTT_BROKER_HOST` | `test.mosquitto.org`          | Broker hostname                |
| `MQTT_BROKER_PORT` | `1883`                        | Broker port                    |
| `MQTT_TOPIC`       | `motion_suit/data`            | Publish topic                  |

## Architecture

`main.py` is a single-file application built from small functions:

- **Polling loop** (`run_bridge`) — fetch, validate, publish, repeat.
  Runs on the main thread and reacts to a shared stop event.
- **HTTP retries** (`fetch_snapshot`) — every network error, timeout or
  non-200 response is caught and answered with exponential backoff
  (0.5 s doubling up to 10 s), forever. Link-down and link-up
  transitions are logged once instead of flooding the console.
- **Validation** (`validate_snapshot`) — the payload must parse as a
  JSON object carrying the protocol v2 keys (`seq`, `timestamp`,
  `system`, `imu_data`). Invalid payloads are counted and skipped; the
  original bytes, not a re-serialization, are what gets published.
- **MQTT reconnection** (`create_mqtt_client`) — paho's background
  network thread (`connect_async` + `loop_start`) performs the initial
  connection and every reconnection with bounded backoff (1-30 s).
  While disconnected, QoS 0 publishes are dropped and counted rather
  than queued, because stale motion data is worthless.
- **Graceful shutdown** — SIGINT/SIGTERM set a stop event checked by
  every wait; the `finally` block disconnects the client, stops the
  network thread and closes the HTTP session.
- **Statistics** — one aggregated log line every 10 s (publish rate,
  failure counters, last `seq`, suit system state) plus a notice when
  a suit reboot is detected (`seq` decreased).

## Troubleshooting

| Symptom                          | Likely cause / fix                                      |
| -------------------------------- | ------------------------------------------------------- |
| `ESP32 unreachable` warnings     | Not connected to the `ESP32_Test` WiFi, or suit off.    |
| `MQTT connection refused/lost`   | No internet route, or the public broker is overloaded — the bridge keeps retrying on its own. |
| Publishes but no data on `mosquitto_sub` | Confirm the exact topic `motion_suit/data` (case-sensitive). |
| `invalid=` counter growing       | Endpoint answered non-snapshot JSON — check that `ESP32_DATA_URL` points at `/data`. |
