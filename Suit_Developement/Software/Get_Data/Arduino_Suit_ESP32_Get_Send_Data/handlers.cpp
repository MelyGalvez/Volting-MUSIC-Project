#include "handlers.h"
#include "config.h"
#include "globals.h"
#include "imu.h"
#include "json.h"


// ==========================================================
// HANDLERS.cpp
// ==========================================================


// --------- Sensor data request handler ----------


void handleDataRequest()
{
    Serial.println("\n[HTTP] /data");

    // ----------- Data acquisition ---------------

    unsigned long startTime = millis();

    captureIMUData();

    unsigned long elapsedTime = millis() - startTime;

    Serial.print("Capture time: ");
    Serial.print(elapsedTime);
    Serial.println(" ms");

    // ------------ JSON generation ---------------

    String json = buildJson();

    Serial.print("JSON size: ");
    Serial.println(json.length());

    // ------------- HTTP response ----------------

    server.send(
        200,
        "application/json",
        json
    );

    Serial.println("Response sent");
}


// -------------- LED request handler -------------


void handleLedRequest()
{
    Serial.println("\n[HTTP] /led");

    if (server.hasArg("on"))
    {
        bool state = server.arg("on") == "1";

        digitalWrite(
            LED_PIN,
            state
        );

        actionTriggered = state;

        Serial.print("LED: ");
        Serial.println(state ? "ON" : "OFF");
    }

    server.send(
        200,
        "text/plain",
        "OK"
    );
}


// ---------- Vibration request handler -----------


void handleVibrationRequest()
{
    Serial.println("\n[HTTP] /vibration");

    // -------------- Left motor ------------------

    if (server.hasArg("left"))
    {
        bool state = server.arg("left") == "1";

        digitalWrite(
            VIB_LEFT_PIN,
            state
        );
    }

    // -------------- Right motor -----------------

    if (server.hasArg("right"))
    {
        bool state = server.arg("right") == "1";

        digitalWrite(
            VIB_RIGHT_PIN,
            state
        );
    }

    server.send(
        200,
        "text/plain",
        "OK"
    );
}