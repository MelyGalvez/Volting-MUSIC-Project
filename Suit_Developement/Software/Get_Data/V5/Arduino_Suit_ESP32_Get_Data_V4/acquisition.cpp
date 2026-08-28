#include <Arduino.h>

#include "acquisition.h"
#include "config.h"
#include "imu.h"
#include "calibration.h"
#include "snapshot.h"
#include "status.h"
#include "quat.h"


// ================================================
// ACQUISITION.cpp
// ================================================


static TaskHandle_t s_task = nullptr;

static ImuFrame s_frames[NUM_IMUS];
static uint8_t s_failCount[NUM_IMUS] = {0};

static uint32_t s_lastReinitMs = 0;
static uint8_t s_reinitCursor = 0;

static uint8_t s_slowCursor = 0;


// ------------- Lost sensor recovery --------------


static void attemptReinit(uint32_t nowMs)
{
    if(imuDetectedCount() == imuEquippedCount())
    {
        return;
    }

    if(nowMs - s_lastReinitMs < IMU_REINIT_PERIOD_MS)
    {
        return;
    }

    s_lastReinitMs = nowMs;

    for(uint8_t n = 0; n < NUM_IMUS; n++)
    {
        uint8_t i = (uint8_t)((s_reinitCursor + n) % NUM_IMUS);

        if(!imuEquipped(i))
        {
            continue;
        }

        if(!imuDetected(i))
        {
            s_reinitCursor = (uint8_t)((i + 1) % NUM_IMUS);

            if(initializeIMU(i))
            {
                Serial.printf(
                    "[IMU] Sensor %u recovered\n",
                    (unsigned)i
                );

                s_failCount[i] = 0;
            }

            return;
        }
    }
}


// --------------- System state -------------------


static void updateSystemState()
{
    if(calibrationActive())
    {
        setSystemState(SYSTEM_CALIBRATION);
        return;
    }

    uint8_t okCount = 0;

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(s_frames[i].ok)
        {
            okCount++;
        }
    }

    if(okCount > 0 && okCount == imuEquippedCount())
    {
        setSystemState(SYSTEM_READY);
    }
    else if(okCount > 0)
    {
        setSystemState(SYSTEM_DEGRADED);
    }
    else
    {
        setSystemState(SYSTEM_ERROR);
    }
}


// ------------------ One scan --------------------


static void scanOnce()
{
    Quaternion raw[NUM_IMUS];
    bool rawValid[NUM_IMUS] = {false};

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(!imuDetected(i))
        {
            s_frames[i].ok = false;
            continue;
        }

        if(readImuQuat(i, raw[i]))
        {
            rawValid[i] = true;
            s_failCount[i] = 0;

            readImuVectors(i, s_frames[i]);

            if(i == s_slowCursor)
            {
                readImuSlowData(i, s_frames[i]);
            }
        }
        else
        {

            if(s_failCount[i] < 255)
            {
                s_failCount[i]++;
            }

            if(s_failCount[i] >= IMU_FAILS_BEFORE_LOST)
            {
                if(imuDowngradeClock(i))
                {
                    s_failCount[i] = 0;
                }
                else
                {
                    if(s_frames[i].ok)
                    {
                        Serial.printf(
                            "[IMU] Sensor %u lost\n",
                            (unsigned)i
                        );
                    }

                    s_frames[i].ok = false;
                    imuMarkLost(i);
                }
            }
        }
    }

    calibrationProcess(raw, rawValid);

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(!rawValid[i])
        {
            continue;
        }

        s_frames[i].quat = quatDeltaLocal(
            raw[i],
            calibrationReference(i)
        );

        quatToEuler(
            s_frames[i].quat,
            s_frames[i].euler.heading,
            s_frames[i].euler.pitch,
            s_frames[i].euler.roll
        );

        s_frames[i].ok = true;
        s_frames[i].calibrated = calibrationHasReference(i);
    }

    s_slowCursor = (uint8_t)((s_slowCursor + 1) % NUM_IMUS);

    snapshotPublishImu(s_frames);
}


// -------------- Acquisition task ----------------


static void acquisitionTask(void*)
{
    if(CALIBRATE_ON_BOOT)
    {
        calibrationRequest();
    }

    for(;;)
    {
        uint32_t startMs = millis();

        scanOnce();
        attemptReinit(startMs);
        updateSystemState();

        uint32_t elapsed = millis() - startMs;

        uint32_t delayMs =
            (elapsed < IMU_SCAN_PERIOD_MS)
                ? (IMU_SCAN_PERIOD_MS - elapsed)
                : 1;

        vTaskDelay(pdMS_TO_TICKS(delayMs));
    }
}


// ---------------- Initialization -----------------


void startAcquisitionTask()
{
    xTaskCreatePinnedToCore(
        acquisitionTask,
        "acquisition",
        ACQUISITION_TASK_STACK,
        nullptr,
        ACQUISITION_TASK_PRIORITY,
        &s_task,
        ACQUISITION_TASK_CORE
    );
}