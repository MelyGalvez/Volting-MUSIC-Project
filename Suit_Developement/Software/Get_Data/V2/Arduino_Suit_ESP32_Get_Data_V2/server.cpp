#include "server.h"

#include "global.h"
#include "handlers.h"

// ======================================================
// SERVER
// ======================================================


// ======================================================
// Health endpoint
// ======================================================

static void handleHealthRequest()
{
    server.send(
        200,
        "application/json",
        "{\"status\":\"ok\"}"
    );
}


// ======================================================
// Initialization
// ======================================================

void initializeServer()
{
    Serial.println();
    Serial.println("===============================");
    Serial.println("Initializing HTTP Server");
    Serial.println("===============================");

    //----------------------------------------------------
    // Routes
    //----------------------------------------------------

    server.on(
        "/data",
        HTTP_GET,
        handleDataRequest
    );

    server.on(
        "/health",
        HTTP_GET,
        handleHealthRequest
    );

    //----------------------------------------------------
    // Start server
    //----------------------------------------------------

    server.begin();

    Serial.println("HTTP server started.");
}