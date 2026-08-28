# Python Motion Recorder

Records the motion of the ESP32 Motion Suit **continuously** into a CSV
file, and lets you mark the beginning and the end of every movement of a
choreography by pressing **SPACE**.

```
ESP32 suit (8 IMUs)          V4/Python_MQTT_Bridge          this program
+------------------+  HTTP   +-------------------+  MQTT   +---------------+
| Arduino_Suit_    | ------> | main.py           | ------> | main.py       |
| ESP32_Get_Data_V4|  /data  | (republishes the  |         | (records)     |
+------------------+         |  JSON unchanged)  |         +-------+-------+
                             +-------------------+                 |
                                                                   v
                                                       recordings/session_*.csv
```

The recording never stops: SPACE only writes a marker line inside the
stream of data.

```
data  data  data  START  data  data  END  data  data  START  data  END  data
                  ^                  ^                ^            ^
                  1st SPACE          2nd SPACE        3rd SPACE    4th SPACE
```

This project **only records and segments**. Movement recognition,
movement comparison, machine learning, wheelchair control and vibration
feedback are *not* part of it; they belong to a future project.

---

## 1. Where the settings come from

Nothing here is invented: every value was read in the existing V4
project, which sits next to this folder.

| Setting | Value | Read in |
| --- | --- | --- |
| MQTT broker | `192.168.56.1` | `V4/Python_MQTT_Bridge/main.py`, line 64 |
| MQTT port | `1883` | `V4/Python_MQTT_Bridge/main.py`, line 65 |
| MQTT topic | `motion_suit/data` | `V4/Python_MQTT_Bridge/main.py`, line 66 |
| Authentication | none (no user, no password, no TLS) | the bridge calls neither `username_pw_set()` nor `tls_set()` |
| QoS | 0 | `V4/Python_MQTT_Bridge/main.py`, line 70 |
| Message rate | ~10 messages per second | bridge `POLL_INTERVAL_S = 0.1` |
| IMU scan rate inside the suit | 100 Hz | `Arduino_Suit_ESP32_Get_Data_V4/config.h`, `IMU_SCAN_PERIOD_MS = 10` |
| Number of IMUs | 8 | `config.h`, `NUM_IMUS = 8` |
| JSON structure | protocol `v2` | `Arduino_Suit_ESP32_Get_Data_V4/json.cpp` |
| Timestamp | `timestamp` = milliseconds since the ESP32 booted (`esp_timer_get_time() / 1000`) | `snapshot.cpp` |

> The bridge README mentions `test.mosquitto.org`, but its **code** uses
> `192.168.56.1`. The code is what actually publishes, so the recorder
> follows the code. Change it with the `MQTT_BROKER_HOST` environment
> variable if your broker is elsewhere (see *Configuration*).

### The message sent by the suit

One MQTT message = one complete snapshot of the suit:

```json
{"v":2,"seq":15873,"timestamp":158730,"system":"ready",
 "piezo":{"left":{"peak":0,"hits":3,"hit_peak":1024},
          "right":{"peak":0,"hits":1,"hit_peak":768}},
 "imu_data":[
   {"body":"back_upper","ok":true,"cal":true,
    "qw":0.9986,"qx":0.0121,"qy":-0.0442,"qz":0.0271,
    "heading":3.15,"pitch":-1.20,"roll":0.55,
    "accel":{"x":0.12,"y":0.03,"z":9.79},
    "total_accel":{"x":0.12,"y":0.03,"z":9.79},
    "lin_accel":{"x":0.01,"y":0.00,"z":-0.02},
    "gravity":{"x":0.11,"y":0.03,"z":9.81},
    "gyro":{"x":0.06,"y":-0.12,"z":0.00},
    "mag":{"x":0.00,"y":0.00,"z":0.00},
    "temp":31,
    "calib":{"sys":3,"gyro":3,"accel":2,"mag":0},
    "status":{"system":5,"self_test":15,"error":0}},
   ... 7 more IMUs ...
 ]}
```

The 8 IMUs are always sent in this order (`BODY_NAMES` in `json.cpp`),
and each one also carries its own `body` name:

| Index | `body` name | Index | `body` name |
| --- | --- | --- | --- |
| 0 | `back_upper` | 4 | `left_forearm` |
| 1 | `back_lower` | 5 | `right_forearm` |
| 2 | `left_arm` | 6 | `left_hand` |
| 3 | `right_arm` | 7 | `right_hand` |

The quaternion `qw, qx, qy, qz` is the orientation **relative to the
T-pose** captured at boot, and `heading, pitch, roll` (degrees) are the
Euler angles derived from that same quaternion (`types.h`).

---

## 2. Installation

Python 3.10 or newer.

```bash
cd Python_Motion_Recorder
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

The only dependency is `paho-mqtt` (MQTT client). Everything else comes
from the Python standard library.

---

## 3. Running a session

Start the suit, start `V4/Python_MQTT_Bridge/main.py`, then:

```bash
python main.py
```

```
====================================================================
  ESP32 Motion Suit - continuous motion recorder
====================================================================
  broker    : mqtt://192.168.56.1:1883  (no authentication, no TLS)
  topic     : motion_suit/data  (QoS 0)
  IMUs      : 8  (back_upper, back_lower, left_arm, ...)
  file      : ...\recordings\session_20260825_183947.csv
--------------------------------------------------------------------
  SPACE     : start / end a movement (recording never stops)
  Q or ESC  : stop the session
====================================================================

18:39:47  connected to mqtt://192.168.56.1:1883 -- listening on 'motion_suit/data'
18:39:49  samples=21 markers=0 movements=0 invalid=0 mqtt=online last_seq=214 suit=ready | waiting for SPACE
18:39:51  START movement 1 at sample_index 38
18:39:53  samples=59 markers=1 movements=1 invalid=0 mqtt=online last_seq=252 suit=ready | RECORDING movement 1
18:39:55  END   movement 1 at sample_index 78
```

### Keys

| Key | Effect |
| --- | --- |
| `SPACE` | 1st press: start of movement 1. 2nd: end of movement 1. 3rd: start of movement 2. 4th: end of movement 2, and so on. |
| `Q` or `ESC` | stop the session and close the file |
| `Ctrl+C` | same as `Q` |

The keyboard is read without ever blocking, in the main thread, while
the MQTT messages are received in a separate thread. **SPACE never
interrupts the reception**: it only appends one line to the file.

A key that stays pressed repeats itself in every operating system, so
two SPACE events less than `SPACE_DEBOUNCE_S` (0.25 s) apart count as
one press: one physical press always gives exactly one marker.

---

## 4. The CSV file

One file per session in `recordings/`, named
`session_YYYYMMDD_HHMMSS.csv` (a `_2`, `_3`... suffix is added if that
name already exists).

Each line is one record and the first column says which kind:

| `record_type` | written when | contains |
| --- | --- | --- |
| `sample` | an MQTT message arrives (~10 per second) | all the sensor data of the message |
| `marker` | you press SPACE | `event`, timestamps, `sample_index`, `movement_id`; the sensor columns stay **empty** |

### Common columns (15)

| Column | Meaning |
| --- | --- |
| `record_type` | `sample` or `marker` |
| `sample_index` | 0, 1, 2, 3... one per sample, always increasing, never reset |
| `event` | empty on samples, `START` or `END` on markers |
| `movement_id` | 1, 2, 3... ; also filled on the samples belonging to a movement, empty outside |
| `pc_time_iso` | clock of the PC, readable (`2026-08-25T18:39:51.244`) |
| `pc_time_unix` | clock of the PC, seconds since 1970 |
| `esp_timestamp_ms` | clock of the suit: milliseconds since the ESP32 booted |
| `esp_seq` | scan counter of the suit (a decrease means the suit rebooted) |
| `system` | `boot`, `calibration`, `ready`, `degraded` or `error` |
| `piezo_left_peak`, `piezo_left_hits`, `piezo_left_hit_peak` | left piezo |
| `piezo_right_peak`, `piezo_right_hits`, `piezo_right_hit_peak` | right piezo |

### IMU columns (32 per IMU, 8 IMUs = 256)

Every column is prefixed with the body name, so the 8 sensors always
stay distinguishable: `left_arm_qw`, `right_hand_gyro_z`, ...

| Suffix | Meaning |
| --- | --- |
| `_ok` | 1 = the last read of this sensor succeeded (`ok` in the JSON) |
| `_calibrated` | 1 = the T-pose reference was captured (`cal` in the JSON) |
| `_qw`, `_qx`, `_qy`, `_qz` | quaternion relative to the T-pose |
| `_heading`, `_pitch`, `_roll` | Euler angles in degrees, derived from that quaternion |
| `_accel_x/y/z` | accelerometer (gravity + movement), m/s² |
| `_lin_accel_x/y/z` | linear acceleration, m/s² |
| `_gravity_x/y/z` | gravity vector, m/s² |
| `_gyro_x/y/z` | angular velocity, °/s |
| `_mag_x/y/z` | magnetic field, µT (always 0 in IMUPLUS mode) |
| `_temp` | temperature of the chip, °C |
| `_calib_sys`, `_calib_gyro`, `_calib_accel`, `_calib_mag` | BNO055 calibration levels, 0 to 3 |
| `_status_system`, `_status_self_test`, `_status_error` | BNO055 diagnostic registers |

Total: 15 + 8 × 32 = **271 columns**.

> `json.cpp` exports the accelerometer twice, as `accel` and as
> `total_accel`, with exactly the same numbers (its own comment says
> so). The CSV therefore stores that measurement once, in the
> `..._accel_*` columns.

### Where a movement starts and ends

A marker stores in `sample_index` the index that the **next** sample
will receive. So movement *n* is made of the samples such that:

```
sample_index of the START  <=  sample_index  <  sample_index of the END
```

Example with the markers `START 38`, `END 78`: movement 1 is made of the
samples 38 to 77. Those samples also carry `movement_id = 1`, so you can
find them without looking at the markers at all.

### Reading a recording

Without any library:

```python
import csv

with open("recordings/session_20260825_183947.csv", newline="") as f:
    rows = list(csv.DictReader(f))

movement_1 = [r for r in rows
              if r["record_type"] == "sample" and r["movement_id"] == "1"]

print(len(movement_1), "samples")
print(movement_1[0]["left_arm_qw"], movement_1[0]["left_arm_heading"])
```

With pandas:

```python
import pandas as pd

data = pd.read_csv("recordings/session_20260825_183947.csv")
samples = data[data.record_type == "sample"]
markers = data[data.record_type == "marker"]

movement_2 = samples[samples.movement_id == 2]
```

---

## 5. Configuration

The constants at the top of `main.py` are the defaults; each one can be
overridden with an environment variable of the same name (same
convention as the V4 bridge).

| Variable | Default | Meaning |
| --- | --- | --- |
| `MQTT_BROKER_HOST` | `192.168.56.1` | broker address |
| `MQTT_BROKER_PORT` | `1883` | broker port |
| `MQTT_TOPIC` | `motion_suit/data` | topic to record |

Example, to record from another broker:

```bash
set MQTT_BROKER_HOST=192.168.1.50
```

---

## 6. What happens when something goes wrong

| Situation | Behaviour |
| --- | --- |
| The broker is not reachable when the program starts | it starts anyway and connects as soon as the broker answers |
| The broker or the network disappears during a session | the program keeps running, reconnects on its own (1 s to 30 s backoff) and resubscribes; the recording simply has a hole, `sample_index` continues without a reset |
| A message is not JSON, is truncated, or misses a key | it is counted in `invalid=` and skipped; the recording continues |
| A field is missing in a message | the corresponding cell stays **empty** — no value is ever invented |
| An IMU is disconnected (`ok:false`) | its data is written exactly as sent, with `_ok = 0` |
| You stop while a movement is still open | the file keeps the `START` without an `END` and the summary warns you |

---

## 7. Files

```
Python_Motion_Recorder/
├── main.py            the whole program (one file)
├── requirements.txt   paho-mqtt
├── README.md          this file
└── recordings/        the CSV files are written here
```

Inside `main.py`:

| Part | Role |
| --- | --- |
| *Configuration* | the values read in the V4 project |
| *The 8 IMUs of the suit* | names and fields of the sensors |
| *CSV layout* | the 271 columns, built once |
| *Recorder* | writes the samples and the markers (protected by a lock, because two threads write) |
| *MQTT* | client, subscription, reconnection, message handling |
| *Non blocking keyboard* | reads the keys already pressed, without ever waiting |
| *Session* | the main loop: keyboard + status line |
