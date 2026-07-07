#pragma once


// ================================================
// CONFIG.h
// ================================================


// --------------- Pin configuration --------------


#define SDA_PIN             21
#define SCL_PIN             22

#define PIEZO_PIN           34

#define LED_PIN             18

#define VIB_LEFT_PIN        12
#define VIB_RIGHT_PIN       13


// --------------- I2C configuration --------------


#define TCA9548A_ADDR       0x70


// --------------- IMU configuration --------------


#define NUM_IMUS            8
#define FIRST_IMU_CHANNEL   8


// -------------- Wifi configuration --------------


constexpr char WIFI_SSID[] = "ESP32_Test";
constexpr char WIFI_PASSWORD[] = "12345678";