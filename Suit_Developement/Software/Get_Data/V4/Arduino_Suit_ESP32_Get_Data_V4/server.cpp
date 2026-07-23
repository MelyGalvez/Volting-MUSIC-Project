#include <WebServer.h>
#include <esp_timer.h>

#include "server.h"
#include "config.h"
#include "json.h"
#include "snapshot.h"
#include "status.h"
#include "calibration.h"
#include "imu.h"


// ================================================
// SERVER.cpp
//
// HTTP endpoints:
//
//   GET  /data      : latest acquisition snapshot
//   GET  /health    : liveness + diagnostics
//   POST /calibrate : trigger a T-pose recalibration
//
// Handlers only copy the cached snapshot and
// serialize it (<1 ms); no sensor I/O ever happens
// on the network path.
// ================================================


static WebServer s_server(HTTP_PORT);

// Static (not stack) so the ~8 KB payload does not weigh
// on the loop task stack.
static char s_jsonBuffer[JSON_BUFFER_SIZE];


// ------------------- /data ----------------------


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

    // send_P streams the buffer with an explicit length and
    // no intermediate String copy of the ~4.5 KB body (on
    // ESP32, PROGMEM pointers are plain pointers).
    s_server.send_P(
        200,
        "application/json",
        s_jsonBuffer,
        n
    );
}


// ------------------ /health ---------------------


static void handleHealthRequest()
{
    Snapshot snap;
    snapshotGet(snap);

    static char buf[256];

    snprintf(
        buf,
        sizeof(buf),
        "{\"status\":\"ok\",\"state\":\"%s\","
        "\"seq\":%lu,\"uptime_ms\":%llu,"
        "\"free_heap\":%lu,\"imus_detected\":%u}",
        systemStateName(getSystemState()),
        (unsigned long)snap.seq,
        (unsigned long long)(esp_timer_get_time() / 1000LL),
        (unsigned long)ESP.getFreeHeap(),
        (unsigned)imuDetectedCount()
    );

    s_server.send(200, "application/json", buf);
}


// ----------------- /calibrate -------------------


static void handleCalibrateRequest()
{
    calibrationRequest();

    s_server.send(
        200,
        "application/json",
        "{\"status\":\"calibration_started\"}"
    );
}


// ------------------ Not found -------------------


static void handleNotFound()
{
    s_server.send(
        404,
        "application/json",
        "{\"error\":\"not_found\"}"
    );
}


// --------------- Initialisation -----------------


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


// ------------------- Polling --------------------


void serverHandleClient()
{
    s_server.handleClient();
}
