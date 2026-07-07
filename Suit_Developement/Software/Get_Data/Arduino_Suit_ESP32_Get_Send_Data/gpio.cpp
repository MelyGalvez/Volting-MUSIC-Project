#include <Arduino.h>

#include "gpio.h"
#include "config.h"


// ================================================
// GPIO.cpp
// ================================================


// -------------- GPIO initialisation -------------


void initializeGPIO()
{
    // ------------------ LED ---------------------

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    // ------------- Vibration motors -------------

    pinMode(VIB_LEFT_PIN, OUTPUT);
    pinMode(VIB_RIGHT_PIN, OUTPUT);

    digitalWrite(VIB_LEFT_PIN, LOW);
    digitalWrite(VIB_RIGHT_PIN, LOW);

    // ---------------- Piezo ----------------

    pinMode(PIEZO_PIN, INPUT);
}