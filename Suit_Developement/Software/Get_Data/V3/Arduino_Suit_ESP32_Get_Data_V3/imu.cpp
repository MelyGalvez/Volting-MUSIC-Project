#include <Wire.h>

#include "imu.h"
#include "config.h"
#include "global.h"
#include "gpio.h"
#include "mux.h"
#include "status.h"
#include "orientation.h"
#include "quat.h"


// ================================================
// IMU.cpp
// ================================================


// --------------- Initialize IMUs ----------------


void initializeIMUs()
{
    Serial.println();
    Serial.println("=================================");
    Serial.println("Initializing IMUs");
    Serial.println("=================================");

    bool success = true;

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        selectMuxChannel(i);

        delay(20);

        Serial.print("IMU ");
        Serial.print(i);
        Serial.print(" : ");

        imuStatus[i].detected =
            imuSensors[i].begin();

        imuStatus[i].calibrated = false;

        if(imuStatus[i].detected)
        {
            imuSensors[i].setExtCrystalUse(true);

            Serial.println("OK");
        }
        else
        {
            Serial.println("FAILED");

            success = false;
        }
    }

    if(success)
    {
        setSystemState(SYSTEM_CALIBRATION);
    }
    else
    {
        setSystemState(SYSTEM_ERROR);
    }
}


// ---------------- IMU detection -----------------


bool allIMUsDetected()
{
    for(uint8_t i=0;i<NUM_IMUS;i++)
    {
        if(!imuStatus[i].detected)
        {
            return false;
        }
    }

    return true;
}


// ------------------ IMU reading -----------------


bool readIMU(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll,
    Quaternion& quat
)
{
    if(index >= NUM_IMUS)
    {
        return false;
    }

    if(!imuStatus[index].detected)
    {
        return false;
    }

    selectMuxChannel(index);

    delay(IMU_DELAY_MS);

    // ------------ Absolute quaternion -----------

    imu::Quaternion q = imuSensors[index].getQuat();

    quat.w = q.w();
    quat.x = q.x();
    quat.y = q.y();
    quat.z = q.z();

    // ------------------ Euler -------------------

    imu::Vector<3> euler =
        imuSensors[index].getVector(
            Adafruit_BNO055::VECTOR_EULER
        );

    heading = euler.x();
    pitch   = euler.y();
    roll    = euler.z();
    applyOrientation(
    index,
    heading,
    pitch,
    roll
);

    return true;
}


// --------------- IMU acquisition ----------------


void captureIMUs()
{
    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        float heading;
        float pitch;
        float roll;
        Quaternion rawQuat;

        if(!readIMU(
            i,
            heading,
            pitch,
            roll,
            rawQuat))
        {
            continue;
        }

        allReadings[i].quat =
            quatDelta(rawQuat, imuQuatOffsets[i]);


        allReadings[i].angle.heading =
            heading - imuOffsets[i].heading;

        allReadings[i].angle.pitch =
            pitch - imuOffsets[i].pitch;

        allReadings[i].angle.roll =
            roll - imuOffsets[i].roll;
    }

    int leftPiezo = readLeftPiezo();
    int rightPiezo = readRightPiezo();

    for(uint8_t i=0;i<NUM_IMUS;i++)
    {
        allReadings[i].piezoLeft = leftPiezo;
        allReadings[i].piezoRight = rightPiezo;
    }
}