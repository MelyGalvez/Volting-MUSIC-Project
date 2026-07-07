#include <WiFi.h>

#include "wifi_manager.h"
#include "config.h"


// ================================================
// wifi_manager.cpp
// ================================================


// ----------------- Initialisation ---------------


void initializeWiFi()
{
    Serial.println("\n=== INITIALIZING WIFI ===");

    WiFi.softAP(
        WIFI_SSID,
        WIFI_PASSWORD
    );

    Serial.print("SSID: ");
    Serial.println(WIFI_SSID);

    Serial.print("IP Address: ");
    Serial.println(
        WiFi.softAPIP()
    );

    Serial.println("WiFi initialized");
}