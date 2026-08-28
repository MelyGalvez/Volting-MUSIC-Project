#include <WebServer.h>
#include <esp_timer.h>
#include <stdarg.h>

#include "server.h"
#include "config.h"
#include "json.h"
#include "snapshot.h"
#include "status.h"
#include "calibration.h"
#include "imu.h"


// ================================================
// SERVER.cpp
// ================================================


static WebServer s_server(HTTP_PORT);

static char s_jsonBuffer[JSON_BUFFER_SIZE];


// ------------------ /data ----------------------


static void handleDataRequest()
{
    Snapshot snap;
    snapshotGet(snap);

    size_t n = buildJson(
        s_jsonBuffer,
        sizeof(s_jsonBuffer),
        snap,
        getSystemState()
    );

    if(n == 0)
    {
        s_server.send(
            500,
            "application/json",
            "{\"error\":\"serialization_overflow\"}"
        );

        return;
    }

    s_server.send_P(
        200,
        "application/json",
        s_jsonBuffer,
        n
    );
}


// ------------------ /health --------------------


static bool healthAppend(
    char* buf,
    size_t cap,
    size_t& offset,
    const char* fmt,
    ...
)
{
    if(offset >= cap)
    {
        return false;
    }

    va_list args;
    va_start(args, fmt);

    int n = vsnprintf(buf + offset, cap - offset, fmt, args);

    va_end(args);

    if(n < 0 || (size_t)n >= cap - offset)
    {
        offset = cap;
        return false;
    }

    offset += (size_t)n;

    return true;
}


static void handleHealthRequest()
{
    Snapshot snap;
    snapshotGet(snap);

    static char buf[1792];

    size_t off = 0;
    bool ok = true;

    ok &= healthAppend(
        buf, sizeof(buf), off,
        "{\"status\":\"ok\",\"state\":\"%s\","
        "\"seq\":%lu,\"uptime_ms\":%llu,"
        "\"free_heap\":%lu,\"imus_detected\":%u,"
        "\"imus_expected\":%u,\"channels\":[",
        systemStateName(getSystemState()),
        (unsigned long)snap.seq,
        (unsigned long long)(esp_timer_get_time() / 1000LL),
        (unsigned long)ESP.getFreeHeap(),
        (unsigned)imuDetectedCount(),
        (unsigned)imuEquippedCount()
    );

    for(uint8_t i = 0; i < NUM_IMUS && ok; i++)
    {
        ok &= healthAppend(
            buf, sizeof(buf), off,
            "%s{\"ch\":%u,\"body\":\"%s\","
            "\"equipped\":%s,\"detected\":%s,"
            "\"addr\":\"0x%02X\",\"probe\":\"%s\","
            "\"chip\":\"0x%02X\",\"clock\":%lu,"
            "\"xtal\":\"%s\",\"lost\":%u}",
            (i > 0) ? "," : "",
            (unsigned)i,
            bodyName(i),
            imuEquipped(i) ? "true" : "false",
            imuDetected(i) ? "true" : "false",
            (unsigned)imuAddress(i),
            imuProbeName(i),
            (unsigned)imuChipId(i),
            (unsigned long)imuClock(i),
            imuExternalCrystal(i) ? "ext" : "int",
            (unsigned)imuLostCount(i)
        );
    }

    ok &= healthAppend(buf, sizeof(buf), off, "]}");

    if(!ok)
    {
        s_server.send(
            500,
            "application/json",
            "{\"error\":\"serialization_overflow\"}"
        );

        return;
    }

    s_server.send(200, "application/json", buf);
}


// ---------------- /calibrate -------------------


static void handleCalibrateRequest()
{
    calibrationRequest();

    s_server.send(
        200,
        "application/json",
        "{\"status\":\"calibration_started\"}"
    );
}


// ------------------ Not found ------------------


static void handleNotFound()
{
    s_server.send(
        404,
        "application/json",
        "{\"error\":\"not_found\"}"
    );
}


// -------------- Initialisation -----------------


void initializeServer()
{
    Serial.println();
    Serial.println("===============================");
    Serial.println("Initializing HTTP Server");
    Serial.println("===============================");

    s_server.on("/data", HTTP_GET, handleDataRequest);
    s_server.on("/health", HTTP_GET, handleHealthRequest);
    s_server.on("/calibrate", HTTP_POST, handleCalibrateRequest);
    s_server.onNotFound(handleNotFound);

    s_server.begin();

    Serial.println("HTTP server started.");
}


// ------------------ Polling --------------------


void serverHandleClient()
{
    s_server.handleClient();
}