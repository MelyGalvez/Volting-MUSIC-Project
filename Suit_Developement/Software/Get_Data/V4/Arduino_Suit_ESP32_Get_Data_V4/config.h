#pragma once

#include <Arduino.h>
#include <Adafruit_BNO055.h>


// ================================================
// CONFIG.h
//
// Every tunable constant of the firmware lives here.
// Each value documents why it was chosen so future
// tuning starts from the original rationale.
// ================================================


// --------------------- GPIO ---------------------


constexpr uint8_t SDA_PIN = 21;
constexpr uint8_t SCL_PIN = 22;

// ADC1 pins (34/35 are input-only). ADC1 keeps working
// while WiFi is active; ADC2 does not.
constexpr uint8_t PIEZO_LEFT_PIN  = 34;
constexpr uint8_t PIEZO_RIGHT_PIN = 35;

// NOTE: GPIO16/17 are used by PSRAM on WROVER modules.
// These assignments assume a WROOM-32 style board.
constexpr uint8_t LED_RED_PIN    = 16;
constexpr uint8_t LED_YELLOW_PIN = 17;
constexpr uint8_t LED_GREEN_PIN  = 18;


// ---------------------- I2C ---------------------


constexpr uint8_t TCA9548A_ADDR = 0x70;

// 400 kHz is the BNO055 datasheet maximum. It halves the
// full-suit scan time versus the 100 kHz default (8 IMUs:
// ~5 ms instead of ~16 ms). Drop to 100000 if a specific
// board shows bus errors.
constexpr uint32_t I2C_CLOCK_HZ = 400000;

// Upper bound for BNO055 clock stretching. Without an
// explicit timeout a stuck slave can hang a transaction
// far longer and stall the acquisition task.
constexpr uint16_t I2C_TIMEOUT_MS = 50;

// Consecutive mux addressing failures tolerated before a
// full 9-pulse I2C bus recovery is attempted.
constexpr uint8_t MUX_FAILS_BEFORE_RECOVERY = 3;


// --------------------- IMUs ---------------------


constexpr uint8_t NUM_IMUS = 8;

// IMUPLUS = accelerometer + gyroscope fusion, no
// magnetometer. On a body-worn suit the magnetometer is
// disturbed by nearby electronics and indoor steel, which
// makes NDOF heading jump. All consumers use T-pose
// relative orientation, so absolute magnetic heading adds
// nothing but instability. Yaw drifts slowly (deg/min) and
// is corrected by recalibrating.
constexpr adafruit_bno055_opmode_t BNO_OPERATION_MODE =
    OPERATION_MODE_IMUPLUS;

// Adafruit breakouts have an external 32 kHz crystal.
// Set false for bare modules without one.
constexpr bool BNO_USE_EXTERNAL_CRYSTAL = true;

// Consecutive failed reads before an IMU is declared lost
// (a single glitch must not drop a sensor).
constexpr uint8_t IMU_FAILS_BEFORE_LOST = 3;

// Period between re-initialization attempts of lost
// sensors. One sensor is probed per period; the probe is a
// fast I2C ACK test, so a missing sensor costs <1 ms.
constexpr uint32_t IMU_REINIT_PERIOD_MS = 5000;

// Target period of one full 8-IMU scan. 10 ms = 100 Hz,
// matching the BNO055 fusion output rate; scanning faster
// only rereads identical data.
constexpr uint32_t IMU_SCAN_PERIOD_MS = 10;


// ------------------ Calibration -----------------


// Run the T-pose capture automatically after boot.
constexpr bool CALIBRATE_ON_BOOT = true;

// Time for the user to settle into T-pose. The BNO055
// fusion converges in ~1-2 s when stationary; 5 s leaves
// margin for the user. Recalibration can also be triggered
// any time via POST /calibrate.
constexpr uint32_t CALIBRATION_SETTLE_MS = 5000;

// Averaging window: ~100 samples at 100 Hz. Averaging
// suppresses sensor noise that a single-shot reference
// would bake into every subsequent frame.
constexpr uint32_t CALIBRATION_SAMPLE_MS = 1000;


// -------------------- Piezo ---------------------


// Sampling period of the dedicated piezo task. Piezo
// strikes are ~1-5 ms wide; 1 kHz sampling guarantees
// detection regardless of how often clients poll.
constexpr uint32_t PIEZO_SAMPLE_PERIOD_MS = 1;

// Trigger / re-arm thresholds (12-bit ADC counts).
// 500 matches the historically tuned client-side value.
// Hysteresis (500 trigger / 200 re-arm) prevents one
// oscillating strike from firing multiple hits.
constexpr uint16_t PIEZO_TRIGGER_THRESHOLD = 500;
constexpr uint16_t PIEZO_REARM_THRESHOLD   = 200;

// Window after the trigger during which the true strike
// peak is tracked (piezo pulses reach their maximum within
// a few ms). The peak drives MIDI velocity downstream.
constexpr uint32_t PIEZO_PEAK_TRACK_MS = 6;

// Minimum interval between hits. Fastest intentional
// single-hand strike rates are ~10-12 Hz, so 80 ms accepts
// real playing and rejects mechanical ringing.
constexpr uint32_t PIEZO_COOLDOWN_MS = 80;

// Decay of the published peak envelope per 1 ms sample.
// 30/ms drains a full-scale 4095 hit in ~140 ms so slow
// pollers still observe the strike amplitude.
constexpr uint16_t PIEZO_ENVELOPE_DECAY = 30;


// --------------------- WiFi ---------------------


constexpr char WIFI_SSID[] = "ESP32_Test";
constexpr char WIFI_PASSWORD[] = "12345678";

// Explicit channel and client limit make AP behaviour
// deterministic across core versions.
constexpr uint8_t WIFI_CHANNEL = 1;
constexpr uint8_t WIFI_MAX_CLIENTS = 4;


// --------------------- HTTP ---------------------


constexpr uint16_t HTTP_PORT = 80;

// Static serialization buffer. A full packet is ~4.5 KB
// now that every BNO055 measurement is exported; 8 KB
// leaves ample headroom and the builder guards against
// overflow.
constexpr size_t JSON_BUFFER_SIZE = 8192;


// ------------------ FreeRTOS --------------------


// Acquisition and piezo tasks run on core 0 (with the WiFi
// stack, which preempts them as needed); the HTTP server
// stays on core 1 in loop(). This keeps blocking I2C
// traffic off the network core.
constexpr BaseType_t ACQUISITION_TASK_CORE = 0;
constexpr BaseType_t PIEZO_TASK_CORE = 0;

constexpr uint32_t ACQUISITION_TASK_STACK = 4096;
constexpr uint32_t PIEZO_TASK_STACK = 2048;

// Piezo priority above acquisition so 1 kHz sampling is
// not delayed by multi-ms I2C transactions.
constexpr UBaseType_t ACQUISITION_TASK_PRIORITY = 1;
constexpr UBaseType_t PIEZO_TASK_PRIORITY = 2;
