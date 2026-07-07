#include <Arduino.h>
#include <Wire.h>

#include "imu.h"
#include "config.h"
#include "globals.h"
#include "mux.h"


// ================================================
// IMU.cpp
// ================================================


// ---------------- Initialisation  ---------------


void initializeIMUs()
{
    Serial.println("\n=== INITIALIZING IMUs ===");

    for (uint8_t i = 0; i < NUM_IMUS; i++)
    {
        uint8_t channel = i;

        selectMuxChannel(channel);

        delay(10);

        Serial.print("Initializing channel ");
        Serial.print(channel);
        Serial.print("... ");

        if (!imuSensors[i].begin())
        {
            Serial.println("FAILED");
        }
        else
        {
            imuSensors[i].setExtCrystalUse(true);
            Serial.println("OK");
        }
    }
}


// ----------------- IMU Reading ------------------


bool readIMUData(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll
)
{
    imu::Vector<3> euler =
        imuSensors[index].getVector(
            Adafruit_BNO055::VECTOR_EULER
        );

    heading = euler.x();
    pitch = euler.y();
    roll = euler.z();

    return true;
}

// --------------- Data acquisition  --------------


void captureIMUData()
{
    Serial.println("\n[CAPTURE] START");

    for (uint8_t i = 0; i < NUM_IMUS; i++)
    {
        uint8_t channel = i;

        Serial.print("Reading channel ");
        Serial.println(channel);

        selectMuxChannel(channel);

        delay(3);

        float heading = 0.0f;
        float pitch = 0.0f;
        float roll = 0.0f;

        bool success = readIMUData(
            i,
            heading,
            pitch,
            roll
        );

        if (!success)
        {
            Serial.println("FAILED");
            continue;
        }

        allReadings[i].channel = channel;
        allReadings[i].heading = heading;
        allReadings[i].pitch = pitch;
        allReadings[i].roll = roll;
    }

    // ----------------- Piezo  -------------------

    int piezo = analogRead(PIEZO_PIN);

    for (uint8_t i = 0; i < NUM_IMUS; i++)
    {
        allReadings[i].piezo = piezo;
    }

    Serial.println("[CAPTURE] END");
}