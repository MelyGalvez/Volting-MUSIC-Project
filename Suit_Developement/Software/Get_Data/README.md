# Get Data

This folder contains different versions of the ESP32 firmware and Python client used to receive sensor data from the wearable suit over Wi-Fi.

---

# V1 – Receive and Send Data

## Description

This first version allows the computer to communicate with the ESP32 through Wi-Fi.

Available features:

- Receive Euler angles from all 8 BNO055 IMUs
- Receive left and right piezo sensor values
- Control the three onboard LEDs
- Control the two vibration motors

---

## How to use

1. Upload the ESP32 firmware.
2. Power on the board.
3. Wait approximately **30 seconds** for the sensors to initialize.
4. Once the **blue Wi-Fi LED** is ON, connect your computer to the ESP32 Wi-Fi network.
5. Launch the Python client (`main.py`).

The console should continuously display the sensor values.

Example:

```text
===============================================
          [ STATUS MULTI-IMU RX ]
-----------------------------------------------
CH 0 | H=359.9 | P=4.6 | R=48.6 | PIEZO_L=0.0 | PIEZO_R=0.0
CH 1 | H=0.0   | P=-1.6| R=91.7 | PIEZO_L=0.0 | PIEZO_R=0.0
CH 2 | H=359.9 | P=3.3 | R=91.1 | PIEZO_L=0.0 | PIEZO_R=0.0
CH 3 | H=359.9 | P=-10.1|R=80.9 | PIEZO_L=0.0 | PIEZO_R=0.0
CH 4 | H=359.9 | P=16.6| R=106.9| PIEZO_L=0.0 | PIEZO_R=0.0
CH 5 | H=359.9 | P=17.6| R=96.2 | PIEZO_L=0.0 | PIEZO_R=0.0
CH 6 | H=0.0   | P=-1.8| R=74.1 | PIEZO_L=0.0 | PIEZO_R=0.0
CH 7 | H=359.9 | P=4.6 | R=48.6 | PIEZO_L=0.0 | PIEZO_R=0.0
-----------------------------------------------
Action TX: False
```

---

## Keyboard shortcuts

### LEDs

| Key | Action |
|------|--------|
| G | Toggle Green LED |
| O | Toggle Orange LED |
| R | Toggle Red LED |

### Vibrators

| Key | Action |
|------|--------|
| ← | Toggle Left Vibrator |
| → | Toggle Right Vibrator |

---

## HTTP commands

LED control

```
http://192.168.4.1/led?green=0&orange=0&red=0
```

Vibration control

```
http://192.168.4.1/vibration?left=0&right=0
```

---

# V2 – Automatic Initialization and Sensor Calibration

## Description

Version 2 introduces a complete initialization procedure.

After startup, the user is asked to stand in a **T-pose** while the system automatically computes the reference orientation of every IMU.

The calibration takes approximately **10 seconds**.

Each sensor is then referenced to its own initial orientation, allowing all reported angles to be relative to the calibration pose.

---

## LED Status

| LED | Meaning |
|------|---------|
| Yellow | System initialization / calibration in progress |
| Green | System ready |
| Red | One or more IMUs failed during initialization |

---

## HTTP API

### Read sensor data

```
GET http://192.168.4.1/data
```

Example response:

```json
{
    "timestamp":1305435,
    "system":"ready",
    "imu_data":[
        {
            "body":"back_upper",
            "detected":true,
            "calibrated":true,
            "heading":-2.69,
            "pitch":0.37,
            "roll":0.69,
            "piezo_left":0,
            "piezo_right":0
        }
    ]
}
```

---

### Health endpoint

```
GET http://192.168.4.1/health
```

Response

```json
{
    "status":"ok"
}
```

---

## Python Client Output

After calibration, running the Python client displays:

```text
========================================
 ESP32 DATA
========================================
Timestamp : 1162287
System    : ready
----------------------------------------
back_upper      | H=  -2.69 P=   0.37 R=   0.69 | Detected=True Cal=True
back_lower      | H=  -3.12 P=  -0.31 R=  -1.62 | Detected=True Cal=True
left_arm        | H= 356.94 P=  -1.31 R=  -0.06 | Detected=True Cal=True
right_arm       | H= 357.56 P=   0.31 R=  -0.13 | Detected=True Cal=True
left_forearm    | H= 358.94 P=  -0.62 R=  -0.19 | Detected=True Cal=True
right_forearm   | H= 357.87 P=   1.31 R=  -0.44 | Detected=True Cal=True
left_hand       | H=-331.13 P=   1.87 R=  -0.94 | Detected=True Cal=True
right_hand      | H=  -4.31 P=   0.44 R=   0.37 | Detected=True Cal=True
----------------------------------------
Piezo L: 0   Piezo R: 0
```

---

## Improvements over V1

- Automatic IMU detection
- Automatic T-pose calibration
- Relative orientation instead of raw Euler angles
- Sensor status (detected/calibrated)
- System state monitoring
- Health endpoint (`/health`)
- Cleaner JSON structure
- Improved Python client output