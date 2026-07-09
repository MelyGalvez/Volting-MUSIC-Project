#pragma once

#include <Arduino.h>

// ======================================================
// MUX
// ======================================================

/**
 * @brief Select one channel of the TCA9548A.
 *
 * @param channel Channel number (0 to 7).
 */
void selectMuxChannel(uint8_t channel);