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

    pinMode(LED_R_PIN, OUTPUT);
    pinMode(LED_O_PIN, OUTPUT);
    pinMode(LED_G_PIN, OUTPUT);

    digitalWrite(LED_R_PIN, LOW);
    digitalWrite(LED_O_PIN, LOW);
    digitalWrite(LED_G_PIN, LOW);

    // ------------- Vibration motors -------------

    pinMode(VIB_LEFT_PIN, OUTPUT);
    pinMode(VIB_RIGHT_PIN, OUTPUT);

    digitalWrite(VIB_LEFT_PIN, LOW);
    digitalWrite(VIB_RIGHT_PIN, LOW);

    // ---------------- Piezo ----------------

    pinMode(PIEZO_LEFT_PIN, INPUT);
    pinMode(PIEZO_RIGHT_PIN, INPUT);
}