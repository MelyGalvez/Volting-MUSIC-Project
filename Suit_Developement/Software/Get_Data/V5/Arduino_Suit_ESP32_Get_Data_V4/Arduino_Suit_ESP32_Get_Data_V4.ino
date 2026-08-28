#include <Arduino.h>

#include "config.h"
#include "gpio.h"
#include "status.h"
#include "mux.h"
#include "imu.h"
#include "snapshot.h"
#include "piezo.h"
#include "acquisition.h"
#include "wifi_manager.h"
#include "server.h"


// ================================================
// MAIN.ino
// ================================================


// --------------------- Setup --------------------


void setup()
{

    // ------------------- Serial -----------------

    Serial.begin(115200);

    delay(500);

    Serial.println();
    Serial.println("==================================");
    Serial.println("      ESP32 MUSIC SUIT V4");
    Serial.println("==================================");

    // ----------------- Hardware -----------------

    initializeGPIO();

    initializeStatus();

    initializeSnapshot();

    // ------------------- I2C --------------------

    initializeI2C();

    // ----------------- Sensors ------------------

    initializeIMUs();

    // -------------- Communication ---------------

    if(!initializeWiFi())
    {
        for(;;)
        {
            delay(1000);
        }
    }

    initializeServer();

    // ---------------- Background ----------------

    startPiezoTask();

    startAcquisitionTask();

    Serial.println();
    Serial.println("System ready.");
}


// ---------------------- Loop --------------------


void loop()
{
    updateStatus();

    serverHandleClient();

    delay(1);
}