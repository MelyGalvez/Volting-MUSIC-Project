#include "wifi_manager.h"

#include <WiFi.h>

#include "config.h"
#include "global.h"
#include "status.h"

// ======================================================
// WIFI MANAGER
// ======================================================

void initializeWiFi()
{
    Serial.println();
    Serial.println("===============================");
    Serial.println("Initializing WiFi");
    Serial.println("===============================");

    //----------------------------------------------------
    // Access Point
    //----------------------------------------------------

    bool success = WiFi.softAP(
        WIFI_SSID,
        WIFI_PASSWORD
    );

    if(!success)
    {
        Serial.println("Failed to create Access Point.");

        setSystemState(SYSTEM_ERROR);

        return;
    }

    //----------------------------------------------------
    // Information
    //----------------------------------------------------

    Serial.print("SSID : ");
    Serial.println(WIFI_SSID);

    Serial.print("Password : ");
    Serial.println(WIFI_PASSWORD);

    Serial.print("IP Address : ");
    Serial.println(
        WiFi.softAPIP()
    );

    Serial.println("WiFi ready.");
}