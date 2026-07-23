#include <WiFi.h>

#include "wifi_manager.h"
#include "config.h"
#include "status.h"


// ================================================
// WIFI_MANAGER.cpp
// ================================================


// -------------- Initialisation ------------------


bool initializeWiFi()
{
    Serial.println();
    Serial.println("===============================");
    Serial.println("Initializing WiFi");
    Serial.println("===============================");

    // --------------- Access point ---------------

    WiFi.mode(WIFI_AP);

    bool success = WiFi.softAP(
        WIFI_SSID,
        WIFI_PASSWORD,
        WIFI_CHANNEL,
        false,              // not hidden
        WIFI_MAX_CLIENTS
    );

    if(!success)
    {
        Serial.println("Failed to create Access Point.");

        setSystemState(SYSTEM_ERROR);

        return false;
    }

    // ---------------- Information ---------------

    Serial.print("SSID : ");
    Serial.println(WIFI_SSID);

    Serial.print("IP Address : ");
    Serial.println(WiFi.softAPIP());

    Serial.println("WiFi ready.");

    return true;
}
