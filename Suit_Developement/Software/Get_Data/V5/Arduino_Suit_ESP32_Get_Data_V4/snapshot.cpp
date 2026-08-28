#include <Arduino.h>
#include <esp_timer.h>

#include "snapshot.h"


// ================================================
// SNAPSHOT.cpp
// ================================================


static SemaphoreHandle_t s_mutex = nullptr;
static Snapshot s_snapshot;


// --------------- Initialization ----------------


void initializeSnapshot()
{
    s_mutex = xSemaphoreCreateMutex();
}


// ------------------ Writers --------------------


void snapshotPublishImu(const ImuFrame frames[NUM_IMUS])
{
    if(xSemaphoreTake(s_mutex, portMAX_DELAY) != pdTRUE)
    {
        return;
    }

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        s_snapshot.imu[i] = frames[i];
    }

    s_snapshot.seq++;
    s_snapshot.timestampMs =
        (uint64_t)(esp_timer_get_time() / 1000LL);

    xSemaphoreGive(s_mutex);
}


void snapshotUpdatePiezo(
    const PiezoChannelState& left,
    const PiezoChannelState& right
)
{
    if(xSemaphoreTake(s_mutex, portMAX_DELAY) != pdTRUE)
    {
        return;
    }

    s_snapshot.piezoLeft = left;
    s_snapshot.piezoRight = right;

    xSemaphoreGive(s_mutex);
}


// ------------------- Reader --------------------


void snapshotGet(Snapshot& out)
{
    if(xSemaphoreTake(s_mutex, portMAX_DELAY) != pdTRUE)
    {
        return;
    }

    out = s_snapshot;

    xSemaphoreGive(s_mutex);
}