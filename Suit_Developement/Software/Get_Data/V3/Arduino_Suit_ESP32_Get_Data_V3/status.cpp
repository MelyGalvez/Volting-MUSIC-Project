#include <Arduino.h>

#include "status.h"
#include "global.h"
#include "gpio.h"


// ================================================
// STATUS.cpp
// ================================================


static unsigned long previousBlink = 0;
static bool blinkState = false;


// ---------------- Initialisation ----------------


void initializeStatus()
{
    systemState = SYSTEM_BOOT;
    refreshStatus();
}


// -------------------- State ---------------------


void setSystemState(SystemState state)
{
    systemState = state;

    refreshStatus();
}

SystemState getSystemState()
{
    return systemState;
}


// ------------------ LED refresh -----------------


void refreshStatus()
{
    switch(systemState)
    {

    // ------------------  Boot -------------------

        case SYSTEM_BOOT:

            setRedLED(false);
            setYellowLED(true);
            setGreenLED(false);

            break;

            // -----------  Calibration -----------

        case SYSTEM_CALIBRATION:

            setRedLED(false);
            setYellowLED(true);
            setGreenLED(false);

            break;

    // ------------------  Ready ------------------

        case SYSTEM_READY:

            setRedLED(false);
            setYellowLED(false);
            setGreenLED(true);

            break;

            // --------------  Error --------------

        case SYSTEM_ERROR:

            setRedLED(true);
            setYellowLED(false);
            setGreenLED(false);

            break;
    }
}


// ------------------ Loop update -----------------


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