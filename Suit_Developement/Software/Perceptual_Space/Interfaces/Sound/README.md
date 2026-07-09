# Sound

This folder contains the Python applications used to transform the motion capture suit into a musical instrument.

Each version of the software is designed to work with the corresponding version of the ESP32 firmware available in the **Get Data** project.

| Music Version | Compatible ESP32 Firmware |
| ------------- | ------------------------- |
| Music V1      | Get Data V1               |
| Music V2      | Get Data V2               |

---

# Sound V1 – Dual Hand Musical Interface

## Description

The first version uses only the two hand IMUs to control two independent MIDI instruments.

Each hand controls one instrument.

### Mapping

**Left hand**

* Pitch → Octave
* Roll → Musical note
* Left piezo → Drum trigger

**Right hand**

* Pitch → Octave
* Roll → Musical note
* Right piezo → Drum trigger

The application also provides:

* Instrument selection
* Drum selection
* Note display
* Current octave display
* LED control
* Vibration control

This version communicates with **Get Data V1**, which provides raw IMU measurements and allows remote control of the LEDs and vibration motors.

---

## How to use

1. Upload **Get Data V1** to the ESP32.
2. Connect the computer to the ESP32 Wi-Fi network.
3. Launch `main.py`.

A graphical interface appears.

---

## Interface

The interface allows the user to:

* Select the left instrument
* Select the right instrument
* Select the left drum
* Select the right drum
* Enable or disable left vibration
* Enable or disable right vibration
* Display the current note
* Display the current octave

The piezo sensors trigger percussion sounds while the hand orientation continuously controls the two melodic instruments.

---

# Sound V2 – Full Body Musical Interface

## Description

The second version extends the musical interaction to the entire upper body.

Instead of using only the hands, every body segment contributes to one musical parameter.

This version requires **Get Data V2**, which performs automatic IMU calibration using a T-pose before streaming calibrated body orientations.

---

## Motion Mapping

### Back (Upper + Lower)

Channels:

* Back Upper
* Back Lower

Function:

* Controls the octave shared by both instruments.

Leaning forward or backward changes the octave.

---

### Arms

Channels:

* Left Arm
* Right Arm

Function:

* Control the pitch of each instrument independently.

Raising or lowering an arm changes the note played by the corresponding instrument.

---

### Forearms

Channels:

* Left Forearm
* Right Forearm

Function:

* Control the reverb amount of each instrument.

Bending or extending the forearm modifies the reverberation.

---

### Hands

Channels:

* Left Hand
* Right Hand

Function:

* Control the volume of each instrument.

Tilting the hand upward or downward changes the instrument volume.

---

### Piezo Sensors

The piezo sensors are used exclusively for percussion.

Each impact triggers the selected drum sound.

---

## Interface

The graphical interface allows the user to:

* Select the left instrument
* Select the right instrument
* Select the left drum
* Select the right drum
* Display the current note
* Display the current octave

Unlike Version 1, vibration control has been removed to focus entirely on musical interaction.

---

## How to use

1. Upload **Get Data V2** to the ESP32.
2. Power on the suit.
3. Wait for the automatic calibration.
4. Hold a T-pose during the calibration period.
5. Wait until the status LED becomes **green**.
6. Connect the computer to the ESP32 Wi-Fi network.
7. Launch `main.py`.

The application immediately starts receiving calibrated body orientations and converts them into MIDI messages.