#pragma once

#include <Arduino.h>


// ================================================
// MUX.h
// ================================================


// ------------------ MUX functions ---------------


/**
 * @brief Select an I2C channel on the TCA9548A multiplexer.
 *
 * @param channel Multiplexer channel (0 to 7).
 */
void selectMuxChannel(uint8_t channel);