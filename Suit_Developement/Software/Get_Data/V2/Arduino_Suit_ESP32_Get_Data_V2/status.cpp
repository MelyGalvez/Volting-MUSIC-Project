#include "status.h"

#include <Arduino.h>

#include "global.h"
#include "gpio.h"

// ======================================================
// STATUS
// ======================================================

static unsigned long previousBlink = 0;
static bool blinkState = false;

// ======================================================
// Initialization
// ======================================================

void initializeStatus()
{
    systemState = SYSTEM_BOOT;
    refreshStatus();
}

// ======================================================
// State
// ======================================================

void setSystemState(SystemState state)
{
    systemState = state;

    // Mise à jour immédiate des LEDs
    refreshStatus();
}

SystemState getSystemState()
{
    return systemState;
}

// ======================================================
// LED Refresh
// ======================================================

void refreshStatus()
{
    switch(systemState)
    {
        //------------------------------------------------
        // BOOT
        //------------------------------------------------

        case SYSTEM_BOOT:

            setRedLED(false);
            setYellowLED(true);
            setGreenLED(false);

            break;

        //------------------------------------------------
        // CALIBRATION
        //------------------------------------------------

        case SYSTEM_CALIBRATION:

            setRedLED(false);
            setYellowLED(true);      // Allumée immédiatement
            setGreenLED(false);

            break;

        //------------------------------------------------
        // READY
        //------------------------------------------------

        case SYSTEM_READY:

            setRedLED(false);
            setYellowLED(false);
            setGreenLED(true);

            break;

        //------------------------------------------------
        // ERROR
        //------------------------------------------------

        case SYSTEM_ERROR:

            setRedLED(true);
            setYellowLED(false);
            setGreenLED(false);

            break;
    }
}

// ======================================================
// Loop Update
// ======================================================

void updateStatus()
{
    if(systemState != SYSTEM_CALIBRATION)
        return;

    if(millis() - previousBlink >= 500)
    {
        previousBlink = millis();

        blinkState = !blinkState;

        setYellowLED(blinkState);
    }
}