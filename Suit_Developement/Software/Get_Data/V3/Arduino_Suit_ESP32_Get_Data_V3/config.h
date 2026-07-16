#pragma once


// ================================================
// CONFIG.h
// ================================================


// --------------------- GPIO ---------------------


constexpr uint8_t SDA_PIN = 21;
constexpr uint8_t SCL_PIN = 22;

constexpr uint8_t PIEZO_LEFT_PIN  = 34;
constexpr uint8_t PIEZO_RIGHT_PIN = 35;

constexpr uint8_t LED_RED_PIN    = 16;
constexpr uint8_t LED_YELLOW_PIN = 17;
constexpr uint8_t LED_GREEN_PIN  = 18;


// ---------------------- I2C ---------------------


constexpr uint8_t TCA9548A_ADDR = 0x70;


// --------------------- IMUs ---------------------


constexpr uint8_t NUM_IMUS = 8;

constexpr uint16_t IMU_DELAY_MS = 3;


// ------------------ Calibration -----------------


constexpr uint32_t CALIBRATION_TIME_MS = 10000;


// --------------------- Wifi ---------------------


constexpr char WIFI_SSID[] = "ESP32_Test";
constexpr char WIFI_PASSWORD[] = "12345678";