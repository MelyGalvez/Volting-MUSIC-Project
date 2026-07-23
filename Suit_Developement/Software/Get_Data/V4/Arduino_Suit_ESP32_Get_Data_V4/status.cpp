#include <Arduino.h>

#include "status.h"
#include "gpio.h"


// ================================================
// STATUS.cpp
//
// System state + LED patterns:
//
//   BOOT        : yellow
//   CALIBRATION : yellow blinking (visible now that
//                 calibration no longer blocks in
//                 delay(); previously this pattern
//                 was dead code)
//   READY       : green
//   DEGRADED    : green + red (partial sensor loss)
//   ERROR       : red
// ================================================


// Written by the acquisition task, read by loop() and
// HTTP handlers. Single-byte aligned access is atomic on
// Xtensa; volatile prevents caching in registers.
static volatile SystemState s_state = SYSTEM_BOOT;

static uint32_t s_previousBlinkMs = 0;
static bool s_blinkState = false;


// ---------------- Initialisation ----------------


void initializeStatus()
{
    s_state = SYSTEM_BOOT;
    refreshStatus();
}


// -------------------- State ---------------------


static const char* stateName(SystemState state)
{
    switch(state)
    {
        case SYSTEM_BOOT:        return "boot";
        case SYSTEM_CALIBRATION: return "calibration";
        case SYSTEM_READY:       return "ready";
        case SYSTEM_DEGRADED:    return "degraded";
        case SYSTEM_ERROR:       return "error";
        default:                 return "unknown";
    }
}


const char* systemStateName(SystemState state)
{
    return stateName(state);
}


void setSystemState(SystemState state)
{
    if(s_state == state)
    {
        return;
    }

    Serial.printf(
        "[STATE] %s -> %s\n",
        stateName(s_state),
        stateName(state)
    );

    s_state = state;

    refreshStatus();
}


SystemState getSystemState()
{
    return s_state;
}


// ------------------ LED refresh -----------------


void refreshStatus()
{
    switch(s_state)
    {
        case SYSTEM_BOOT:
        case SYSTEM_CALIBRATION:

            setRedLED(false);
            setYellowLED(true);
            setGreenLED(false);

            break;

        case SYSTEM_READY:

            setRedLED(false);
            setYellowLED(false);
            setGreenLED(true);

            break;

        case SYSTEM_DEGRADED:

            setRedLED(true);
            setYellowLED(false);
            setGreenLED(true);

            break;

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
    if(s_state != SYSTEM_CALIBRATION)
    {
        return;
    }

    uint32_t now = millis();

    if(now - s_previousBlinkMs >= 500)
    {
        s_previousBlinkMs = now;

        s_blinkState = !s_blinkState;

        setYellowLED(s_blinkState);
    }
}
