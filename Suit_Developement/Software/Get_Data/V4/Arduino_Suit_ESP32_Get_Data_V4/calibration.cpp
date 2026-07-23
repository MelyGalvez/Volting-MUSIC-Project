#include <Arduino.h>

#include "calibration.h"
#include "config.h"
#include "quat.h"


// ================================================
// CALIBRATION.cpp
//
// Non-blocking T-pose reference capture, driven by
// the acquisition task (one call per scan). Replaces
// the previous blocking delay(10000) + single-sample
// design: the LED keeps blinking, the HTTP server
// keeps answering, and the reference is the average
// of ~100 samples instead of one noisy reading.
//
// Phases:  IDLE -> SETTLE -> SAMPLE -> IDLE
// ================================================


enum class CalPhase : uint8_t
{
    IDLE = 0,
    SETTLE,
    SAMPLE
};


static CalPhase s_phase = CalPhase::IDLE;
static volatile bool s_pending = false;

static uint32_t s_phaseStartMs = 0;

static float s_sum[NUM_IMUS][4];
static uint16_t s_sampleCount[NUM_IMUS];

static Quaternion s_reference[NUM_IMUS];
static bool s_hasReference[NUM_IMUS] = {false};


// ------------------- Requests -------------------


void calibrationRequest()
{
    s_pending = true;
}


bool calibrationActive()
{
    return s_pending || s_phase != CalPhase::IDLE;
}


// ------------------ References ------------------


bool calibrationHasReference(uint8_t index)
{
    return index < NUM_IMUS && s_hasReference[index];
}


const Quaternion& calibrationReference(uint8_t index)
{
    static const Quaternion identity{};

    if(index >= NUM_IMUS || !s_hasReference[index])
    {
        return identity;
    }

    return s_reference[index];
}


// ----------------- Accumulation -----------------


static void resetAccumulators()
{
    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        s_sum[i][0] = 0.0f;
        s_sum[i][1] = 0.0f;
        s_sum[i][2] = 0.0f;
        s_sum[i][3] = 0.0f;
        s_sampleCount[i] = 0;
    }
}


static void accumulate(uint8_t i, const Quaternion& q)
{
    // q and -q are the same rotation; align each sample
    // with the running sum so the average does not cancel.
    float dot =
        s_sum[i][0] * q.w + s_sum[i][1] * q.x +
        s_sum[i][2] * q.y + s_sum[i][3] * q.z;

    float sign = (dot < 0.0f) ? -1.0f : 1.0f;

    s_sum[i][0] += sign * q.w;
    s_sum[i][1] += sign * q.x;
    s_sum[i][2] += sign * q.y;
    s_sum[i][3] += sign * q.z;

    s_sampleCount[i]++;
}


static void finalizeReferences()
{
    uint8_t calibratedCount = 0;

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(s_sampleCount[i] == 0)
        {
            // Keep a previous reference if one existed:
            // a recalibration must not destroy a working
            // sensor's zero because it briefly dropped out.
            continue;
        }

        Quaternion mean;
        mean.w = s_sum[i][0];
        mean.x = s_sum[i][1];
        mean.y = s_sum[i][2];
        mean.z = s_sum[i][3];

        if(!quatIsValid(quatNormalize(mean)))
        {
            continue;
        }

        s_reference[i] = quatNormalize(mean);
        s_hasReference[i] = true;
        calibratedCount++;
    }

    Serial.printf(
        "[CAL] Finished: %u/%u sensors calibrated\n",
        (unsigned)calibratedCount,
        (unsigned)NUM_IMUS
    );
}


// ---------------- State machine -----------------


bool calibrationProcess(
    const Quaternion rawQuats[NUM_IMUS],
    const bool rawValid[NUM_IMUS]
)
{
    uint32_t now = millis();

    switch(s_phase)
    {
        case CalPhase::IDLE:

            if(s_pending)
            {
                s_pending = false;
                s_phase = CalPhase::SETTLE;
                s_phaseStartMs = now;

                Serial.println();
                Serial.println("[CAL] Hold the T-pose...");
            }

            return false;

        case CalPhase::SETTLE:

            if(now - s_phaseStartMs >= CALIBRATION_SETTLE_MS)
            {
                resetAccumulators();
                s_phase = CalPhase::SAMPLE;
                s_phaseStartMs = now;

                Serial.println("[CAL] Sampling...");
            }

            return false;

        case CalPhase::SAMPLE:

            for(uint8_t i = 0; i < NUM_IMUS; i++)
            {
                if(rawValid[i])
                {
                    accumulate(i, rawQuats[i]);
                }
            }

            if(now - s_phaseStartMs >= CALIBRATION_SAMPLE_MS)
            {
                finalizeReferences();
                s_phase = CalPhase::IDLE;
                return true;
            }

            return false;
    }

    return false;
}
