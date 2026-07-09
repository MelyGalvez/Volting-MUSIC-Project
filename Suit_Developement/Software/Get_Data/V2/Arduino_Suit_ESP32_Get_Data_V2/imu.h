#pragma once

#include <Arduino.h>


// ================================================
// IMU.h
// ================================================


/**
 * @brief Initialize every BNO055.
 */
void initializeIMUs();


/**
 * @brief Read one IMU.
 *
 * @param index IMU index (0-7)
 * @param heading
 * @param pitch
 * @param roll
 *
 * @return true if acquisition succeeded.
 */
bool readIMU(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll
);


/**
 * @brief Read every IMU.
 */
void captureIMUs();


/**
 * @brief Return true if every IMU has been detected.
 */
bool allIMUsDetected();