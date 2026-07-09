#include "handlers.h"
#include "config.h"
#include "globals.h"
#include "imu.h"
#include "json.h"


// ================================================
// HANDLERS.cpp
// ================================================


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

    if (server.hasArg("green"))
    {
        bool state = server.arg("green") == "1";

        digitalWrite(
            LED_G_PIN,
            state
        );

        Serial.print("Green LED: ");
        Serial.println(state ? "ON" : "OFF");
    }

    if (server.hasArg("orange"))
    {
        bool state = server.arg("orange") == "1";

        digitalWrite(
            LED_O_PIN,
            state
        );

        Serial.print("Orange LED: ");
        Serial.println(state ? "ON" : "OFF");
    }

    if (server.hasArg("red"))
    {
        bool state = server.arg("red") == "1";

        digitalWrite(
            LED_R_PIN,
            state
        );

        Serial.print("Red LED: ");
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