# Python Motion Replay

Loads a choreography recorded by **Python_Motion_Recorder**, cuts it
into movements, and guides the user through them one by one: perform
the movement, reach the recorded final position, hold it five seconds,
next movement. While the user is off target the ESP32 vibrates the left
or the right motor to say which way to turn.

```
recordings/session_*.csv                      live suit
        |                                         |
        |  START/END markers                      |  MQTT motion_suit/data
        v                                         v
  choreography.py  ---- target poses ---->   guidance.py
  (one target per movement)                  (error, tolerance, 5 s hold)
                                                  |
                                    +-------------+-------------+
                                    v                           v
                                  ui.py                    haptics.py
                            (terminal screen)     MQTT motion_suit/haptic
                                                              |
                                                              v
                                                    ESP32  D12 / D13
```

This system only guides. It does not drive a wheelchair, and it does
not command anything other than the two vibration motors.

---

## 1. What it relies on (all read in V4, nothing guessed)

| Item | Value | Where it comes from |
| --- | --- | --- |
| Broker / port | `192.168.56.1` : `1883` | `V4/Python_MQTT_Bridge/main.py` line 64 |
| Data topic | `motion_suit/data` | `V4/Python_MQTT_Bridge/main.py` line 66 |
| Haptic topic | `motion_suit/haptic` | `MQTT_HAPTIC_TOPIC` in `V4/Arduino_Suit_ESP32_Get_Data_V4/config.h` |
| Authentication | none, no TLS | neither the bridge nor the firmware sets any |
| Message rate | ~10 per second | bridge `POLL_INTERVAL_S = 0.1` |
| IMUs | 8, named `back_upper, back_lower, left_arm, right_arm, left_forearm, right_forearm, left_hand, right_hand` | `BODY_NAMES` in `json.cpp` |
| Quaternion | Hamilton product, order **(w, x, y, z)**, unit | `quat.h` |
| What the quaternion means | `conj(T-pose reference) * raw`, i.e. the rotation **relative to the T-pose**, expressed in the sensor frame at calibration time | `quatDeltaLocal()` in `quat.h`, used in `acquisition.cpp` line 199 |
| Euler angles | aerospace Z-Y-X **derived from that quaternion** | `quatToEuler()` in `quat.h` |
| Gravity vector | m/s², in the sensor frame, accelerometer sign convention (`ACC = LIA + GRV`), so it points **up** | `types.h`, `json.cpp` |
| Magnetometer | always 0: the suit runs in IMUPLUS mode | `BNO_OPERATION_MODE` in `config.h` |

The CSV read by this project is the one described in
`Python_Motion_Recorder/README.md`: one row per record, `record_type` =
`sample` or `marker`, and a movement is made of the samples such that
`START.sample_index <= sample_index < END.sample_index`.

---

## 2. How it works

### 2.1 Extracting the movements

`choreography.py` pairs the `START` / `END` markers in order. Markers
that do not pair (an `END` alone, a recording that stops in the middle
of a movement) are reported as warnings and their segment is skipped -
the rest of the choreography still loads.

### 2.2 The target of a movement

The target is the orientation of each IMU at the **end** of the
recorded movement. It is not the last sample: one sample carries all
the sensor noise of that instant. The program takes the last
`REFERENCE_WINDOW_S` seconds (0.5 s, about 5 samples at 10 Hz) and
averages them with **Markley's method** - the mean rotation is the
eigenvector of `M = Σ q qᵀ` for the largest eigenvalue.

That method is used rather than a component-wise average because `q`
and `-q` are the same rotation: a plain average of quaternions that do
not share the same sign partially cancels itself. In the test suite the
eigenvector average lands 0.6° from the true pose where the naive
average is 8.3° away.

The **dispersion** of that window (mean angular distance to the
average) is also computed and displayed: a few degrees means the body
was still, twenty degrees means the user was still moving when they
pressed SPACE, and the program says so.

### 2.3 The orientation error

For each compared sensor:

```
q_error = conj(q_live) * q_target
error   = 2 * atan2(|vector part of q_error|, |w of q_error|)
```

This is the **geodesic distance on the rotation group**: the angle of
the single rotation that would bring the user exactly onto the
reference. Euler angles are deliberately *not* compared one by one -
three angles compared separately have no meaningful "total error", they
suffer from gimbal lock and from the 0/360 wrap, and the same physical
orientation can be written with different triplets.

The per-sensor errors become one number through `ERROR_AGGREGATION`:

* `max` (default): the worst body segment decides, so no sensor can be
  far from the target while the movement is validated;
* `mean`: the average error, more forgiving.

The live quaternions are smoothed by a SLERP low pass filter
(`FILTER_ALPHA`), which stays on the unit sphere and therefore always
produces a real rotation.

### 2.4 Reaching the target and holding it

```
error <= POSITION_TOLERANCE_DEG   ->  the timer starts
error >  EXIT_TOLERANCE_DEG       ->  the timer is reset to zero
timer >= HOLD_DURATION_S          ->  next movement
```

The two different tolerances are the hysteresis: with a single
threshold an error hovering around it would start and reset the timer
several times per second. The timer is also reset when the live data
becomes stale (`STALE_DATA_TIMEOUT_S`), so a broken MQTT link can never
let a hold complete on a frozen orientation.

### 2.5 Which motor should vibrate

The error rotation is turned into a **rotation vector** `r` (axis
multiplied by angle). Because of the convention used
(`q_error = conj(q_live) * q_target`, a body-frame correction), the
axis of `r` is expressed in the sensor's own frame - the same frame in
which the BNO055 reports its gravity vector.

So the program projects one onto the other:

```
up        = gravity / |gravity|          (points up, see the table above)
turn      = r · up                       (degrees around the vertical)
residual  = |r - turn * up|              (everything that is not a turn)
```

* `turn > 0` : a positive rotation around "up" is counter-clockwise
  seen from above, which for a standing person is a turn **to the
  left** -> left motor;
* `turn < 0` : right motor;
* `|turn|` below `DIRECTION_DEADBAND_DEG`, or smaller than
  `DIRECTION_DOMINANCE` of the total error: the correction is mostly a
  bend or a lift, which has no left/right meaning, so **both** motors
  pulse together rather than pointing at a side that would be wrong;
* gravity missing or of an implausible magnitude: both motors again -
  no direction is ever invented.

Nothing here reads a Euler angle or assumes how a sensor is glued on
the body: the vertical axis is *measured*, not assumed. The test suite
checks exactly that, by running the same physical turn on a sensor
mounted upright, on its side, and upside down - all three give the same
side.

### 2.6 Optional: neutral alignment

The recorded and the live quaternions are both relative to a T-pose
calibration, but not necessarily *the same* one (the suit is
recalibrated at every boot). Pressing **N** captures the live neutral
pose for `NEUTRAL_CAPTURE_S` seconds and compares it with the neutral
pose of the recording (the rest posture before the first `START`):

```
A = q_reference_neutral * conj(q_live_neutral)     (per IMU)
```

Every live orientation is then compared as `A * q_live`, which cancels
the difference between the two calibrations. Set `NEUTRAL_ALIGNMENT` or
just press **N** while standing in the posture the recording starts
from.

### 2.7 Optional: trajectory score

After a movement is validated, `trajectory.py` compares the whole path
the user followed with the recorded one using **dynamic time warping**
on the quaternion geodesic distance. DTW is the standard way to compare
two gestures performed at different speeds: a slower user is not
penalised for the delay, only for the shape.

The result is shown in the final report as an average angular distance.
**It never gates the progression** - the criterion stays the final
position plus the five second hold.

---

## 3. Installation

Python 3.10 or newer, on the PC:

```bash
cd Python_Motion_Replay
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

(`paho-mqtt` for MQTT, `numpy` for the quaternion algebra.)

For the ESP32, one library must be installed in the Arduino IDE:
**PubSubClient** by Nick O'Leary (Tools -> Manage Libraries -> search
"PubSubClient"). Then flash the V4 sketch as usual.

---

## 4. Running a session

1. Power the suit, connect the PC to its WiFi access point
   (`ESP32_Test`).
2. Start the MQTT broker on the PC (see section 6 about the address).
3. Start `V4/Python_MQTT_Bridge/main.py` - the suit data must be
   flowing on `motion_suit/data`.
4. Then:

```bash
python main.py
```

The program lists the recordings, loads the one you pick (or the one
given on the command line: `python main.py path\to\session.csv`), shows
what it found, and waits for ENTER.

```
======================================================================
  MOTION REPLAY  -  guided choreography
======================================================================
  recording : session_20260825_183947.csv
  movement  : 2 / 5   (48 recorded samples, 4.8 s)
  MQTT      : connected        data  10.1 msg/s   invalid 0
----------------------------------------------------------------------
  STATE     : PERFORM THE MOVEMENT

  ERROR     :   38.4 deg      tolerance 12.0 deg (exit 18.0)
                #########################---------------  out
                worst sensor: left_arm

  HOLD      :  0.0 / 5.0 s
                ----------------------------------------

  VIBRATION : LEFT  [##]   RIGHT [  ]    pulse 4.5 Hz, 80 ms, power 0.62
                direction: left   commands sent: 214
----------------------------------------------------------------------
  per sensor (deg, and the turn part of the correction):
     left_arm         38.4    turn +38.4   other   0.0
     right_arm         2.1    turn  +1.8   other   1.1
----------------------------------------------------------------------
  [N] capture neutral pose   [S] skip movement   [Q] quit
======================================================================
```

| Key | Effect |
| --- | --- |
| `N` | capture the neutral pose and align the calibrations |
| `S` | skip the current movement (recorded as skipped) |
| `Q`, `ESC`, `Ctrl+C` | stop the session and print the report |

At the end the program prints, per movement, how long it took, the
final error and the trajectory score.

---

## 5. Configuration

Everything lives in `config.py`, and every value can be overridden by
an environment variable of the same name:

```bash
set POSITION_TOLERANCE_DEG=18
```

| Parameter | Default | Meaning |
| --- | --- | --- |
| `MQTT_BROKER_HOST` / `MQTT_BROKER_PORT` | `192.168.56.1` / `1883` | broker |
| `MQTT_DATA_TOPIC` | `motion_suit/data` | where the suit data arrives |
| `MQTT_HAPTIC_TOPIC` | `motion_suit/haptic` | where the commands are sent |
| `STALE_DATA_TIMEOUT_S` | `1.0` | older data counts as "no data" |
| `RECORDINGS_DIR` | `../Python_Motion_Recorder/recordings` | where the CSV files are |
| `REFERENCE_WINDOW_S` | `0.5` | window averaged at the END of a movement |
| `REFERENCE_MIN_SAMPLES` | `3` | minimum samples for a target |
| `REFERENCE_MAX_DISPERSION_DEG` | `8.0` | above this the target is reported unstable |
| `NEUTRAL_WINDOW_S` | `1.0` | window used for the recorded neutral pose |
| `COMPARE_IMUS` | all | e.g. `left_arm,right_arm` |
| `ERROR_AGGREGATION` | `max` | `max` or `mean` |
| `FILTER_ALPHA` | `0.35` | SLERP low pass on the live orientation |
| `NEUTRAL_ALIGNMENT` | `false` | align on the neutral pose |
| `NEUTRAL_CAPTURE_S` | `2.0` | duration of the N capture |
| **`POSITION_TOLERANCE_DEG`** | `12.0` | error below which the pose is reached |
| **`EXIT_TOLERANCE_DEG`** | `18.0` | error above which the hold is lost |
| **`HOLD_DURATION_S`** | `5.0` | how long the pose must be held |
| `HAPTIC_UPDATE_HZ` | `10.0` | command rate |
| `HAPTIC_PULSE_MS` | `80` | ON time of one pulse |
| `HAPTIC_PULSE_HZ_MIN` / `MAX` | `2.0` / `8.0` | pulse rate, far from / close to the target |
| `HAPTIC_INTENSITY_MIN` / `MAX` | `0.35` / `1.0` | motor power |
| `HAPTIC_FULL_INTENSITY_DEG` | `60.0` | error at which the power is maximal |
| `HAPTIC_HOLD_MS` | `800` | lifetime of a command (watchdog) |
| `DIRECTION_DEADBAND_DEG` | `3.0` | below this, no side is claimed |
| `DIRECTION_DOMINANCE` | `0.5` | share of the error that must be a turn |
| `GRAVITY_VECTOR_POINTS_UP` | `true` | sign convention of the gravity output |
| `GRAVITY_MIN/MAX_MAGNITUDE` | `7.0` / `12.0` | plausible gravity, m/s² |
| `HAPTICS_ENABLED` | `true` | `false` disables all vibration |
| `ENABLE_TRAJECTORY_SCORE` | `true` | compute the DTW score |
| `DTW_MAX_POINTS` | `120` | resampling before the DTW |
| `UI_REFRESH_HZ` | `10.0` | screen refresh |

---

## 6. The ESP32 side

### 6.1 What was added to V4

The original project is untouched in its behaviour: the IMU scan, the
piezo task, the JSON packet and the HTTP server are exactly as before.
Four files were added and two were modified, additively:

| File | Change |
| --- | --- |
| `haptic.h` / `haptic.cpp` | **new** - PWM driver with non-blocking pulse timing |
| `haptic_mqtt.h` / `haptic_mqtt.cpp` | **new** - MQTT subscriber, in its own FreeRTOS task |
| `config.h` | 97 lines **appended** (a "Haptic feedback" section), nothing removed |
| `Arduino_Suit_ESP32_Get_Data_V4.ino` | 11 lines **added**: two includes and two calls in `setup()` |

Nothing calls into the acquisition path, and `loop()` is unchanged: the
haptic task runs on core 1 at priority 1, while acquisition and piezo
keep core 0 to themselves. There is no `delay()` anywhere in the added
code - the pulses are produced by comparing `millis()` with the start
of the current pulse train.

### 6.2 Wiring

| Motor | Pin |
| --- | --- |
| LEFT | **GPIO12** (D12) |
| RIGHT | **GPIO13** (D13) |

A vibration motor cannot be driven directly by a GPIO: use a transistor
(or a small motor driver) plus a flyback diode across the motor.

> **Important - GPIO12 is a strapping pin (MTDI).** If it is held HIGH
> while the ESP32 boots, the chip selects the wrong flash voltage and
> may fail to start. Make sure the transistor's gate/base has a pull
> **down** resistor so the pin stays low during boot. GPIO13 has no
> such constraint.

PWM is 20 kHz (above hearing, so the motors do not whistle) with 8 bits
of resolution. Intensities above zero are mapped into
`[HAPTIC_MIN_DUTY_PERCENT, 100]` because an ERM motor does not turn
below its start voltage.

At boot both motors buzz for 250 ms (`HAPTIC_BOOT_TEST`), which
immediately reveals a wiring mistake.

### 6.3 Network: where the broker must run

The suit is a WiFi **access point** (`WiFi.mode(WIFI_AP)` in
`wifi_manager.cpp`), so the ESP32 has no route to the internet. The
broker must therefore run on a machine joined to `ESP32_Test`, which in
practice is the PC that runs the bridge and this program. The ESP32
gives `192.168.4.2` to its first client, and that is the default
`MQTT_BROKER_IP` in `config.h`.

```
        ESP32 (AP, 192.168.4.1)                     PC
        +----------------------+          +----------------------+
        | acquisition 100 Hz   |  HTTP    | bridge  --> broker   |
        | HTTP /data           | <------- | (mosquitto, 1883)    |
        |                      |          |         |            |
        | haptic task  --------|  MQTT    |         v            |
        | subscribes           | <------- | Python_Motion_Replay |
        +----------------------+          +----------------------+
```

If the broker listens on all interfaces (the usual mosquitto default),
one instance serves both the bridge (through whichever interface the
bridge uses) and the ESP32 (through `192.168.4.2`). Adjust
`MQTT_BROKER_IP` in `config.h` if your PC gets another address.

### 6.4 The command format

```json
{"v":1,"seq":42,
 "left":0.80,"right":0.00,
 "pulse_hz":6.0,"pulse_ms":80,"hold_ms":800}
```

| Field | Meaning |
| --- | --- |
| `left`, `right` | motor power, `0.0` = off … `1.0` = full |
| `pulse_hz` | pulses per second (`0` would mean continuous) |
| `pulse_ms` | ON time of one pulse |
| `hold_ms` | how long the command stays valid |

The structure is flat on purpose: the firmware parses it with a small
bounded scanner instead of pulling in a JSON library, exactly as V4
*writes* its JSON with `snprintf` instead of one.

`hold_ms` is a safety watchdog: the firmware stops the motors on its
own when no new command arrives in time. If this program crashes, if
the WiFi drops or if you press Ctrl+C, the motors stop within a
fraction of a second. `HAPTIC_MAX_HOLD_MS` (5 s) caps it, so no single
command can keep a motor running.

---

## 7. What happens when something goes wrong

| Situation | Behaviour |
| --- | --- |
| The broker is unreachable at start | the program starts and connects as soon as it answers |
| The broker or WiFi drops mid-session | the screen shows `OFFLINE`, the hold timer resets, no error is displayed, the motors stop by themselves, and the session resumes on reconnection |
| The suit stops sending (ESP32 off) | after `STALE_DATA_TIMEOUT_S` the state becomes `WAITING FOR DATA`, the timer is reset, the motors are silenced |
| A message is malformed | counted in `invalid`, dropped, the session continues |
| An IMU reports `ok:false` or a quaternion of four zeros | that sensor is ignored for as long as it is silent; the others keep working |
| An IMU is missing from the recording | it is not compared; only sensors present on both sides are |
| The CSV is not a recording, is empty, has no marker, or has no complete movement | the program refuses it with a readable explanation instead of crashing |
| The recording stops in the middle of a movement | the complete movements are kept, a warning names the incomplete one |
| No target sensor is usable in a movement | that movement is skipped, with a warning |

No missing value is ever replaced by an invented one.

---

## 8. Files

```
Python_Motion_Replay/
├── main.py            entry point: choose a recording, run the session
├── config.py          every tunable parameter
├── choreography.py    CSV loading, START/END cutting, target poses
├── orientation.py     quaternion algebra (Hamilton, w x y z)
├── live_data.py       MQTT link: subscribe to data, publish haptics
├── guidance.py        comparison, hysteresis, 5 s hold, progression
├── haptics.py         direction and vibration commands
├── trajectory.py      optional DTW score
├── ui.py              terminal dashboard
├── keyboard.py        non blocking keyboard
├── requirements.txt
└── README.md
```

Related projects in the same folder:

* `V4/` - the suit firmware (with the haptic addition) and the MQTT
  bridge;
* `Python_Motion_Recorder/` - records the choreographies this project
  replays.
