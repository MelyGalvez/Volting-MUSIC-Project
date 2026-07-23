#pragma once

#include <Arduino.h>

#include "types.h"


// ================================================
// IMU.h
// ================================================


/**
 * @brief Initialize every BNO055 (with fast ACK probing).
 */
void initializeIMUs();


/**
 * @brief (Re-)initialize a single BNO055.
 *
 * @return true when the sensor answered and was configured.
 */
bool initializeIMU(uint8_t index);


/**
 * @brief True if this IMU is currently considered present.
 */
bool imuDetected(uint8_t index);


/**
 * @brief Number of currently detected IMUs.
 */
uint8_t imuDetectedCount();


/**
 * @brief Declare an IMU lost after repeated read failures.
 */
void imuMarkLost(uint8_t index);


/**
 * @brief Read and validate the absolute quaternion of one IMU.
 *
 * @return true when a valid, normalized quaternion was read.
 */
bool readImuQuat(uint8_t index, Quaternion& out);


/**
 * @brief Read the fusion vectors of one IMU into a frame.
 *
 * Fills accel, linAccel, gravity, gyro and mag. Assumes the
 * IMU's mux channel is already selected, so call it right
 * after a successful readImuQuat() on the same index.
 */
void readImuVectors(uint8_t index, ImuFrame& frame);


/**
 * @brief Read temperature, calibration and status of one IMU.
 *
 * These change on a seconds timescale; the acquisition task
 * refreshes one sensor per scan. Same mux-channel assumption
 * as readImuVectors().
 */
void readImuSlowData(uint8_t index, ImuFrame& frame);
