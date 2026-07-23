#include <Arduino.h>

#include "piezo.h"
#include "config.h"
#include "gpio.h"
#include "snapshot.h"


// ================================================
// PIEZO.cpp
//
// Dedicated 1 kHz sampling task. Piezo strikes are
// ~1-5 ms wide: sampling them once per HTTP poll
// (the previous design) misses most hits entirely.
// This task detects hits in firmware and publishes:
//
//   - a monotonic hit counter  (clients diff it, so
//     detection is independent of polling rate and
//     safe with multiple concurrent clients)
//   - the peak of the last hit (MIDI velocity source)
//   - a decaying peak envelope (diagnostics/legacy)
//
// Hit state machine per channel:
//
//   ARMED --(signal >= trigger)--> TRACKING
//   TRACKING --(track window over: count the hit,
//               latch its peak)--> COOLDOWN
//   COOLDOWN --(cooldown over AND signal <= rearm)
//            --> ARMED
// ================================================


enum class HitPhase : uint8_t
{
    ARMED = 0,
    TRACKING,
    COOLDOWN
};


struct ChannelDetector
{
    HitPhase phase = HitPhase::ARMED;

    uint16_t envelope = 0;
    uint16_t trackPeak = 0;

    uint32_t trackUntilMs = 0;
    uint32_t cooldownUntilMs = 0;

    PiezoChannelState state;
};


static ChannelDetector s_left;
static ChannelDetector s_right;

static TaskHandle_t s_task = nullptr;


// ---------------- Sample handling ----------------


static void processSample(
    ChannelDetector& ch,
    uint16_t sample,
    uint32_t nowMs
)
{
    // Decaying peak envelope so slow pollers still see
    // strike amplitudes.
    uint16_t decayed =
        (ch.envelope > PIEZO_ENVELOPE_DECAY)
            ? (uint16_t)(ch.envelope - PIEZO_ENVELOPE_DECAY)
            : 0;

    ch.envelope = (sample > decayed) ? sample : decayed;

    switch(ch.phase)
    {
        case HitPhase::ARMED:

            if(sample >= PIEZO_TRIGGER_THRESHOLD)
            {
                ch.phase = HitPhase::TRACKING;
                ch.trackPeak = sample;
                ch.trackUntilMs = nowMs + PIEZO_PEAK_TRACK_MS;
            }

            break;

        case HitPhase::TRACKING:

            if(sample > ch.trackPeak)
            {
                ch.trackPeak = sample;
            }

            if((int32_t)(nowMs - ch.trackUntilMs) >= 0)
            {
                ch.state.hitCount++;
                ch.state.lastHitPeak = ch.trackPeak;

                ch.phase = HitPhase::COOLDOWN;
                ch.cooldownUntilMs = nowMs + PIEZO_COOLDOWN_MS;
            }

            break;

        case HitPhase::COOLDOWN:

            if((int32_t)(nowMs - ch.cooldownUntilMs) >= 0 &&
               sample <= PIEZO_REARM_THRESHOLD)
            {
                ch.phase = HitPhase::ARMED;
            }

            break;
    }

    ch.state.peak = ch.envelope;
}


// ------------------ Piezo task -------------------


static void piezoTask(void*)
{
    TickType_t lastWake = xTaskGetTickCount();

    for(;;)
    {
        uint32_t now = millis();

        processSample(s_left, readLeftPiezo(), now);
        processSample(s_right, readRightPiezo(), now);

        snapshotUpdatePiezo(s_left.state, s_right.state);

        // Fixed-rate delay: keeps the 1 kHz cadence stable
        // even when a sample iteration runs long.
        vTaskDelayUntil(
            &lastWake,
            pdMS_TO_TICKS(PIEZO_SAMPLE_PERIOD_MS)
        );
    }
}


// ---------------- Initialization -----------------


void startPiezoTask()
{
    xTaskCreatePinnedToCore(
        piezoTask,
        "piezo",
        PIEZO_TASK_STACK,
        nullptr,
        PIEZO_TASK_PRIORITY,
        &s_task,
        PIEZO_TASK_CORE
    );
}
