#pragma once

#include <Arduino.h>


// ================================================
// MUX.h
// ================================================


/**
 * @brief Configure the I2C peripheral (pins, clock, timeout).
 */
void initializeI2C();


/**
 * @brief Select one channel of the TCA9548A.
 *
 * Triggers an automatic bus recovery after repeated
 * addressing failures.
 *
 * @return true when the mux acknowledged the selection.
 */
bool selectMuxChannel(uint8_t channel);


/**
 * @brief Force a 9-clock I2C bus recovery and re-init.
 */
void recoverI2CBus();
