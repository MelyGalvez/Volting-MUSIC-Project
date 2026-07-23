# Objective

Extend the existing project while preserving its architecture, formatting, coding style, and existing functionality.

## General Rules

- DO NOT rewrite the project.
- DO NOT refactor unrelated code.
- DO NOT rename files unless explicitly requested.
- DO NOT modify existing APIs unless required.
- Preserve comments whenever possible.
- Preserve the existing JSON formatting style.
- Preserve indentation and naming conventions.
- Keep backward compatibility.

The objective is to ADD functionality, not redesign the project.

---

# Part 1 - Arduino

Project:

Arduino_Suit_ESP32_Get_Data_V4

Current behavior:

The ESP32 exposes an HTTP endpoint:

http://192.168.4.1/data

which returns JSON containing the orientation angles of every BNO055.

## Required modification

Modify the project so that **every available measurement provided by each BNO055** is exported instead of only orientation.

For every IMU, include every value available through the Adafruit BNO055 library, including whenever available:

- Euler angles
    - heading
    - roll
    - pitch

- Quaternion
    - w
    - x
    - y
    - z

- Linear acceleration
    - x
    - y
    - z

- Total acceleration
    - x
    - y
    - z

- Gravity vector
    - x
    - y
    - z

- Gyroscope angular velocity
    - x
    - y
    - z

- Magnetometer
    - x
    - y
    - z

- Accelerometer
    - x
    - y
    - z

- Temperature

- Calibration state
    - system
    - gyro
    - accel
    - mag

- Sensor status

Include every other quantity available from the BNO055 if already accessible through the current library.

Do NOT remove any existing field.

Only add new fields.

---

## JSON

Keep exactly the same JSON structure already used by the project.

Only enrich each IMU object with additional measurements.

Do not change:

- endpoint
- URI
- HTTP server
- response formatting
- pretty printing
- naming convention

The endpoint must remain

http://192.168.4.1/data

---

## Performance

Avoid unnecessary allocations.

Reuse existing JsonDocument.

Avoid duplicate sensor reads whenever possible.

Keep memory usage low.

---

# Part 2 - Python

Create a new folder

Python_MQTT_Bridge

containing a standalone Python application.

Its purpose is:

ESP32 HTTP JSON

↓

Python

↓

MQTT Broker

---

## Behaviour

The application continuously:

1. Requests

http://192.168.4.1/data

2. Parses the JSON

3. Publishes exactly the same JSON without modification

to

Broker

mqtt://test.mosquitto.org:1883

Topic

motion_suit/data

No username.

No password.

No TLS.

QoS = 0

retain = False

---

## Requirements

Use

requests

and

paho-mqtt

The application must:

- reconnect automatically
- retry HTTP requests
- survive temporary network failures
- print useful logs
- exit cleanly with Ctrl+C

---

## Project structure

Python_MQTT_Bridge/

    main.py

    requirements.txt

    README.md

requirements.txt must contain every dependency.

README.md must explain:

- installation

- pip install

- execution

- broker

- topic

- architecture

---

## Code Quality

Use functions.

Use constants.

Add docstrings.

Comment important sections.

Avoid duplicated code.

Use descriptive variable names.

The application should be production-quality.