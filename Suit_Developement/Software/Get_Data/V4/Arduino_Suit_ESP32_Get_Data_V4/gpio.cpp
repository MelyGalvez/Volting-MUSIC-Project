#include "gpio.h"
#include "config.h"


// ================================================
// GPIO.cpp
// ================================================


// ---------------- Initialization ----------------


void initializeGPIO()
{

    // ------------------- LEDs -------------------

    pinMode(LED_RED_PIN, OUTPUT);
    pinMode(LED_YELLOW_PIN, OUTPUT);
    pinMode(LED_GREEN_PIN, OUTPUT);

    setRedLED(false);
    setYellowLED(false);
    setGreenLED(false);

    // ------------------ Piezos ------------------

    pinMode(PIEZO_LEFT_PIN, INPUT);
    pinMode(PIEZO_RIGHT_PIN, INPUT);

    // Make the ADC configuration explicit instead of
    // relying on core defaults, so the thresholds in
    // config.h stay valid across core versions.
    // 12 bit + 11 dB attenuation = full 0..~3.3 V range.
    analogReadResolution(12);
    analogSetPinAttenuation(PIEZO_LEFT_PIN, ADC_11db);
    analogSetPinAttenuation(PIEZO_RIGHT_PIN, ADC_11db);
}


// --------------------- LEDs ---------------------


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


// -------------------- Piezos --------------------


uint16_t readLeftPiezo()
{
    return (uint16_t)analogRead(PIEZO_LEFT_PIN);
}

uint16_t readRightPiezo()
{
    return (uint16_t)analogRead(PIEZO_RIGHT_PIN);
}
