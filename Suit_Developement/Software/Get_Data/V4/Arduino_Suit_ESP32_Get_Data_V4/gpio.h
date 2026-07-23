#pragma once

#include <Arduino.h>

// ================================================
// GPIO.h
// ================================================


/**
 * @brief Initialize every GPIO (LEDs, piezo ADC config).
 */
void initializeGPIO();


// --------------------- LEDs ---------------------


void setRedLED(bool state);

void setYellowLED(bool state);

void setGreenLED(bool state);


// -------------------- Piezos --------------------


uint16_t readLeftPiezo();

uint16_t readRightPiezo();
