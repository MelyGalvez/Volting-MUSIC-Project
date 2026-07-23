#pragma once


// ================================================
// ACQUISITION.h
// ================================================


/**
 * @brief Start the continuous IMU scanning task.
 *
 * Runs the boot calibration (when enabled), keeps the
 * shared snapshot fresh and maintains the system state.
 */
void startAcquisitionTask();
