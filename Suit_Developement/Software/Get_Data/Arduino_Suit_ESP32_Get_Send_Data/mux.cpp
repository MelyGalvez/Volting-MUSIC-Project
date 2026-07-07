#include <Wire.h>

#include "mux.h"
#include "config.h"


// ================================================
// MUX.cpp
// ================================================


// ------------------ MUX functions ---------------


void selectMuxChannel(uint8_t channel)
{
    if (channel < 1 || channel > NUM_IMUS)
    {
        return;
    }

    Wire.beginTransmission(TCA9548A_ADDR);
    Wire.write(1 << (channel));
    Wire.endTransmission();
}