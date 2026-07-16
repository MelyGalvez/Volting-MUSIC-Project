#pragma once

#include <Arduino.h>


// ================================================
// MUX.h
// ================================================


/**
 * @brief Select one channel of the TCA9548A.
 *
 * @param channel
 */
void selectMuxChannel(uint8_t channel);