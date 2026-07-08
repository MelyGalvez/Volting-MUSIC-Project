#include <Arduino.h>
#include <Wire.h>


#include "config.h"
#include "globals.h"
#include "gpio.h"
#include "imu.h"
#include "wifi_manager.h"
#include "server.h"


// ================================================
// MAIN
// ================================================


// --------------------- Setup --------------------


void setup()
{

    // ------------------- Serial -----------------

    Serial.begin(115200);

    delay(500);

    Serial.println();
    Serial.println("==============================");
    Serial.println(" ESP32 GET - SEND START ");
    Serial.println("==============================");

    // ----------------- Hardware -----------------

    initializeGPIO();

    // ------------------- I2C --------------------

    Wire.begin(
        SDA_PIN,
        SCL_PIN
    );

    // ----------------- Sensors ------------------

    initializeIMUs();

    // -------------- Communication ---------------

    initializeWiFi();

    initializeServer();

    Serial.println();
    Serial.println("System ready");
}


// ---------------------- Loop --------------------


void loop()
{
    server.handleClient();

    delay(5);
}