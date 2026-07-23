#pragma once

#include <Arduino.h>

#include "types.h"


// ================================================
// CALIBRATION.h
// ================================================


/**
 * @brief Request a T-pose calibration (non-blocking).
 *
 * Safe to call from any task or HTTP handler; the
 * acquisition task performs the capture.
 */
void calibrationRequest();


/**
 * @brief True while a calibration is pending or running.
 */
bool calibrationActive();


/**
 * @brief Advance the calibration state machine.
 *
 * Called once per scan by the acquisition task with the
 * raw absolute quaternions of the current scan.
 *
 * @return true on the scan where calibration completes.
 */
bool calibrationProcess(
    const Quaternion rawQuats[NUM_IMUS],
    const bool rawValid[NUM_IMUS]
);


/**
 * @brief True once a T-pose reference exists for this IMU.
 */
bool calibrationHasReference(uint8_t index);


/**
 * @brief T-pose reference quaternion (identity if absent).
 */
const Quaternion& calibrationReference(uint8_t index);
