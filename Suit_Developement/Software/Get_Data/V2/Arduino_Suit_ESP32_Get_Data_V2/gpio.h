#pragma once

#include <Arduino.h>

// ======================================================
// GPIO
// ======================================================


/**
 * @brief Initialize every GPIO.
 */
void initializeGPIO();


// ================= LEDs ===============================

void setRedLED(bool state);

void setYellowLED(bool state);

void setGreenLED(bool state);


// ================= Piezos =============================

int readLeftPiezo();

int readRightPiezo();