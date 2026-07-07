#include "server.h"

#include <Arduino.h>

#include "globals.h"
#include "handlers.h"


// ================================================
// SERVER.cpp
// ================================================

// ------------------ Initialisation --------------


void initializeServer()
{
    Serial.println("\n=== INITIALIZING HTTP SERVER ===");

    // --------------- HTTP routes ----------------

    server.on(
        "/data",
        HTTP_GET,
        handleDataRequest
    );

    server.on(
        "/led",
        HTTP_GET,
        handleLedRequest
    );

    server.on(
        "/vibration",
        HTTP_GET,
        handleVibrationRequest
    );

    // ---------------- Start server ----------------

    server.begin();


    Serial.println("HTTP server started");
}