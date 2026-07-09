#include "mux.h"

#include <Wire.h>

#include "config.h"

// ======================================================
// MUX
// ======================================================

void selectMuxChannel(uint8_t channel)
{
    if(channel >= NUM_IMUS)
    {
        return;
    }

    Wire.beginTransmission(TCA9548A_ADDR);

    Wire.write(1 << channel);

    Wire.endTransmission();
}