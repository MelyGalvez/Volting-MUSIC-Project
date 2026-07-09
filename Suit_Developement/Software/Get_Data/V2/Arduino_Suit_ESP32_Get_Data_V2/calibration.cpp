#include "calibration.h"

#include <Arduino.h>

#include "global.h"
#include "imu.h"
#include "status.h"

// ======================================================
// CALIBRATION
// ======================================================

void calibrateIMUs()
{
    Serial.println();
    Serial.println("===============================");
    Serial.println("IMU CALIBRATION");
    Serial.println("===============================");
    Serial.println("Keep the T-pose...");
    Serial.println();

    setSystemState(SYSTEM_CALIBRATION);

    delay(CALIBRATION_TIME_MS);

    for(uint8_t i=0;i<NUM_IMUS;i++)
    {
        float h;
        float p;
        float r;

        if(!readIMU(i,h,p,r))
            continue;

        imuOffsets[i].heading = h;
        imuOffsets[i].pitch   = p;
        imuOffsets[i].roll    = r;

        imuStatus[i].calibrated = true;

        Serial.print("IMU ");
        Serial.print(i);
        Serial.print(" calibrated");
        Serial.println();
    }

    setSystemState(SYSTEM_READY);

    Serial.println();
    Serial.println("Calibration finished.");
}