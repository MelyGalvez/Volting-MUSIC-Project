#include <Arduino.h>
#include <Wire.h>

#include "config.h"
#include "gpio.h"
#include "status.h"
#include "imu.h"
#include "calibration.h"
#include "wifi_manager.h"
#include "server.h"
#include "global.h"
#include "json.h"


// ================================================
// MAIN.ino
// ================================================


// --------------------- Setup --------------------


void setup()
{

    // ------------------- Serial -----------------

    Serial.begin(115200);

    delay(500);

    // ----------------- Hardware -----------------

    initializeGPIO();

    initializeStatus();

    // ------------------- I2C --------------------

    Wire.begin(
        SDA_PIN,
        SCL_PIN
    );

    // ----------------- Sensors ------------------

    initializeIMUs();

    if(getSystemState() != SYSTEM_ERROR)
    {
        calibrateIMUs();
    }

    // -------------- Communication ---------------

    initializeWiFi();

    initializeServer();

}


// ---------------------- Loop --------------------


void loop()
{
    // --------------- Update LED -----------------

    updateStatus();
    data = buildJson();
    print(data);
    server.handleClient();
}