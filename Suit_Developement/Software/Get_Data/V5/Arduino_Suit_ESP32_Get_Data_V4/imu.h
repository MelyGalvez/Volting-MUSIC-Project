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


// Bits returned by imuProbeMask().
constexpr uint8_t IMU_PROBE_PRIMARY = 0x01;
constexpr uint8_t IMU_PROBE_ALTERNATE = 0x02;


/**
 * @brief True if this IMU is currently considered present.
 */
bool imuDetected(uint8_t index);


/**
 * @brief True when this channel is declared as carrying a sensor.
 */
bool imuEquipped(uint8_t index);


/**
 * @brief Number of channels declared as carrying a sensor.
 */
uint8_t imuEquippedCount();


/**
 * @brief I2C address this IMU answered on (0 when undetected).
 */
uint8_t imuAddress(uint8_t index);


/**
 * @brief Addresses that answered the last probe of this channel.
 *
 * Bit field of IMU_PROBE_PRIMARY / IMU_PROBE_ALTERNATE. Tells a
 * mis-strapped sensor apart from a dead channel.
 */
uint8_t imuProbeMask(uint8_t index);


/**
 * @brief Human-readable form of imuProbeMask ("none", "0x28"...).
 */
const char* imuProbeName(uint8_t index);


/**
 * @brief Chip ID last read on this channel (0 when unreadable).
 *
 * A BNO055 answers 0xA0. Any other value means the sensor
 * acknowledges its address but its registers do not read back,
 * which is an electrical problem rather than a missing sensor.
 */
uint8_t imuChipId(uint8_t index);


/**
 * @brief Bus clock this IMU is driven at, in Hz.
 */
uint32_t imuClock(uint8_t index);


/**
 * @brief True when this IMU runs on the external 32 kHz crystal.
 */
bool imuExternalCrystal(uint8_t index);


/**
 * @brief Number of times this IMU has been declared lost.
 *
 * A counter that keeps climbing means a branch that answers but
 * cannot hold a conversation: flapping, not absent.
 */
uint16_t imuLostCount(uint8_t index);


/**
 * @brief Drop one channel to the fallback bus clock.
 *
 * Last resort before declaring a sensor lost: a marginal run
 * reads back garbage at the nominal clock while still
 * acknowledging its address. The choice is sticky, so a later
 * re-init does not put the channel back on the speed that made
 * it drop out.
 *
 * @return true when the channel was actually downgraded.
 */
bool imuDowngradeClock(uint8_t index);


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