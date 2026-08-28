#pragma once

#include <Arduino.h>
#include <Adafruit_BNO055.h>


// ================================================
// CONFIG.h
// ================================================


// -------------------- GPIO ---------------------


constexpr uint8_t SDA_PIN = 21;
constexpr uint8_t SCL_PIN = 22;

constexpr uint8_t PIEZO_LEFT_PIN  = 34;
constexpr uint8_t PIEZO_RIGHT_PIN = 35;

constexpr uint8_t LED_RED_PIN    = 16;
constexpr uint8_t LED_YELLOW_PIN = 17;
constexpr uint8_t LED_GREEN_PIN  = 18;


// --------------------- I2C ---------------------


constexpr uint8_t TCA9548A_ADDR = 0x70;

constexpr uint32_t I2C_CLOCK_HZ = 400000;

constexpr uint16_t I2C_TIMEOUT_MS = 50;

constexpr uint32_t I2C_CLOCK_FALLBACK_HZ = 100000;

// Consecutive mux addressing failures tolerated before a
// full 9-pulse I2C bus recovery is attempted.
constexpr uint8_t MUX_FAILS_BEFORE_RECOVERY = 3;


// -------------------- IMUs ---------------------


constexpr uint8_t NUM_IMUS = 8;

constexpr adafruit_bno055_opmode_t BNO_OPERATION_MODE =
    OPERATION_MODE_IMUPLUS;

constexpr bool BNO_USE_EXTERNAL_CRYSTAL = true;

constexpr uint32_t IMU_FUSION_TIMEOUT_MS = 300;

constexpr uint8_t IMU_FAILS_BEFORE_LOST = 3;

constexpr uint32_t IMU_REINIT_PERIOD_MS = 5000;

constexpr uint32_t IMU_SCAN_PERIOD_MS = 10;

constexpr bool IMU_EQUIPPED[NUM_IMUS] =
{
    true,     // 0 : back_upper
    true,     // 1 : back_lower
    true,     // 2 : left_arm
    true,     // 3 : right_arm
    true,     // 4 : left_forearm
    true,     // 5 : right_forearm
    true,     // 6 : left_hand
    true      // 7 : right_hand
};

constexpr uint8_t BNO_ADDRESS_PRIMARY = BNO055_ADDRESS_A;
constexpr uint8_t BNO_ADDRESS_ALTERNATE = BNO055_ADDRESS_B;

constexpr uint8_t IMU_INIT_ATTEMPTS = 3;
constexpr uint32_t IMU_INIT_RETRY_MS = 250;


// ----------------- Calibration -----------------


constexpr bool CALIBRATE_ON_BOOT = true;

constexpr uint32_t CALIBRATION_SETTLE_MS = 5000;

constexpr uint32_t CALIBRATION_SAMPLE_MS = 1000;


// ------------------- Piezo ---------------------


constexpr uint32_t PIEZO_SAMPLE_PERIOD_MS = 1;
constexpr uint16_t PIEZO_TRIGGER_THRESHOLD = 500;
constexpr uint16_t PIEZO_REARM_THRESHOLD   = 200;
constexpr uint32_t PIEZO_PEAK_TRACK_MS = 6;
constexpr uint32_t PIEZO_COOLDOWN_MS = 80;
constexpr uint16_t PIEZO_ENVELOPE_DECAY = 30;


// -------------------- WiFi ---------------------


constexpr char WIFI_SSID[] = "ESP32_Test";
constexpr char WIFI_PASSWORD[] = "12345678";

constexpr uint8_t WIFI_CHANNEL = 1;
constexpr uint8_t WIFI_MAX_CLIENTS = 4;


// --------------------- HTTP ---------------------


constexpr uint16_t HTTP_PORT = 80;

constexpr size_t JSON_BUFFER_SIZE = 8192;


// ------------------ FreeRTOS --------------------


constexpr BaseType_t ACQUISITION_TASK_CORE = 0;
constexpr BaseType_t PIEZO_TASK_CORE = 0;

constexpr uint32_t ACQUISITION_TASK_STACK = 4096;
constexpr uint32_t PIEZO_TASK_STACK = 2048;

constexpr UBaseType_t ACQUISITION_TASK_PRIORITY = 1;
constexpr UBaseType_t PIEZO_TASK_PRIORITY = 2;