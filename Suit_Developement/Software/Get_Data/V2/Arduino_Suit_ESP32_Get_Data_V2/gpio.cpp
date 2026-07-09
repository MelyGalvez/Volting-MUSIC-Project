#include "gpio.h"
#include "config.h"

// ======================================================
// GPIO
// ======================================================


// ================= Initialization =====================

void initializeGPIO()
{
    // -------- LEDs --------

    pinMode(LED_RED_PIN, OUTPUT);
    pinMode(LED_YELLOW_PIN, OUTPUT);
    pinMode(LED_GREEN_PIN, OUTPUT);

    setRedLED(false);
    setYellowLED(false);
    setGreenLED(false);

    // -------- Piezos ------

    pinMode(PIEZO_LEFT_PIN, INPUT);
    pinMode(PIEZO_RIGHT_PIN, INPUT);
}


// ================= LEDs ===============================

void setRedLED(bool state)
{
    digitalWrite(LED_RED_PIN, state);
}

void setYellowLED(bool state)
{
    digitalWrite(LED_YELLOW_PIN, state);
}

void setGreenLED(bool state)
{
    digitalWrite(LED_GREEN_PIN, state);
}


// ================= Piezos =============================

int readLeftPiezo()
{
    return analogRead(PIEZO_LEFT_PIN);
}

int readRightPiezo()
{
    return analogRead(PIEZO_RIGHT_PIN);
}