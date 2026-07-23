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
//
// Continuous sensor scanning in a dedicated task,
// fully decoupled from the HTTP server. The previous
// design sampled all sensors inside the HTTP handler
// (8 mux switches + 8 x 3 ms delays + 16 I2C reads
// per request, ~40-70 ms of blocking per client
// poll). Here the handler serves a cached snapshot
// in well under a millisecond and data freshness is
// bounded by the scan period (10 ms), not by client
// behaviour. With the full measurement set (quat +
// five vectors per sensor) a scan can exceed that
// period; the loop then paces itself to the actual
// scan time and freshness follows it.
// ================================================


static TaskHandle_t s_task = nullptr;

static ImuFrame s_frames[NUM_IMUS];
static uint8_t s_failCount[NUM_IMUS] = {0};

static uint32_t s_lastReinitMs = 0;
static uint8_t s_reinitCursor = 0;

// Round-robin index for the slow-data refresh (see
// scanOnce): temperature, calibration and status of one
// sensor per scan.
static uint8_t s_slowCursor = 0;


// ------------- Lost sensor recovery --------------


// Try to bring back at most one lost sensor per period.
// The ACK probe inside initializeIMU() fails in <1 ms for
// an absent sensor, so a scan is never stalled noticeably.
static void attemptReinit(uint32_t nowMs)
{
    if(imuDetectedCount() == NUM_IMUS)
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


// ---------------- System state -------------------


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

    if(okCount == NUM_IMUS)
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


// ------------------ One scan ---------------------


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

            // The mux channel is still selected: read the
            // rest of the measurement set in the same slot
            // so the vectors stay coherent with the quat.
            readImuVectors(i, s_frames[i]);

            // Temperature, calibration and status change
            // slowly; one sensor per scan keeps the scan
            // short (full sweep every NUM_IMUS scans).
            if(i == s_slowCursor)
            {
                readImuSlowData(i, s_frames[i]);
            }
        }
        else
        {
            // Tolerate isolated glitches: the frame keeps
            // its last good orientation and only loses its
            // ok flag after several consecutive failures.
            if(s_failCount[i] < 255)
            {
                s_failCount[i]++;
            }

            if(s_failCount[i] >= IMU_FAILS_BEFORE_LOST)
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

    calibrationProcess(raw, rawValid);

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(!rawValid[i])
        {
            continue;
        }

        // T-pose-relative rotation expressed in the sensor
        // frame at calibration time (see quat.h for why
        // this convention, not q * conj(ref), is required
        // by downstream mounting corrections). Without a
        // reference the raw quaternion passes through and
        // calibrated=false flags it.
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


// -------------- Acquisition task -----------------


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

        // Pace the scan to IMU_SCAN_PERIOD_MS; if a scan
        // ran long (bus recovery, reinit), yield at least
        // one tick so lower-priority work never starves.
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
