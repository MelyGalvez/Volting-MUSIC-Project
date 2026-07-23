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
//
// Architecture (per core):
//
//   Core 0 : acquisition task (I2C scan, 100 Hz)
//            piezo task       (ADC,      1 kHz)
//            WiFi stack
//
//   Core 1 : loop() -> HTTP server + status LEDs
//
// Sensor I/O never blocks the network path: HTTP
// handlers serve a mutex-guarded snapshot cache.
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

    // Network first, so /health and /data respond
    // during the boot calibration.
    if(!initializeWiFi())
    {
        // No network, nothing to serve: stay in ERROR
        // (red LED) rather than run half-alive.
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

    // Yield one tick: keeps the idle task fed and caps
    // this loop at ~1 kHz, which adds at most 1 ms to a
    // request while freeing the core for the WiFi stack.
    delay(1);
}
