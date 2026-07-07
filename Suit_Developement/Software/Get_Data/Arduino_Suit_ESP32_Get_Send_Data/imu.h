#pragma once

#include <Arduino.h>


// ================================================
// IMU.h
// ================================================

// ------------------ IMU functions ---------------


/**
 * @brief Initialize all BNO055 sensors.
 */
void initializeIMUs();

/**
 * @brief Read Euler angles from one IMU.
 *
 * @param index IMU index.
 * @param heading Heading angle.
 * @param pitch Pitch angle.
 * @param roll Roll angle.
 * @return true if the reading was successful.
 */
bool readIMUData(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll
);

/**
 * @brief Capture data from all IMUs.
 */
void captureIMUData();