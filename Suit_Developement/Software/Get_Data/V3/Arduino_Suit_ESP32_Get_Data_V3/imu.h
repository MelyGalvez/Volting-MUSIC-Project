#pragma once

#include <Arduino.h>

#include "types.h"


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
 * @param index
 * @param heading
 * @param pitch
 * @param roll
 * @param quat
 *
 * @return
 */
bool readIMU(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll,
    Quaternion& quat
);


/**
 * @brief Read every IMU.
 */
void captureIMUs();


/**
 * @brief Return true if every IMU has been detected.
 */
bool allIMUsDetected();