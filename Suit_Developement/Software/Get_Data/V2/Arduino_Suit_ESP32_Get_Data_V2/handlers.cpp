#include "handlers.h"

#include "global.h"
#include "imu.h"
#include "json.h"

// ======================================================
// HANDLERS
// ======================================================


// ======================================================
// /data
// ======================================================

void handleDataRequest()
{
    // ---------------- Capture sensors ----------------

    captureIMUs();

    // ---------------- Build JSON ----------------------

    String json = buildJson();

    // ---------------- Send response -------------------

    server.send(
        200,
        "application/json",
        json
    );
}