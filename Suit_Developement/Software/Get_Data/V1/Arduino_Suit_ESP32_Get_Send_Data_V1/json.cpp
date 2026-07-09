#include "json.h"
#include "globals.h"


// ================================================
// JSON.cpp
// ================================================


// ---------- Json generation functions -----------


String buildJson()
{
    String json = "{";

    // ---------------- Timestamp ----------------

    json += "\"timestamp\":";
    json += String(millis());
    json += ",";

    // ---------------- IMU data -----------------

    json += "\"imu_data\":[";

    for (uint8_t i = 0; i < NUM_IMUS; i++)
    {
        const SensorReading& reading = allReadings[i];

        json += "{";

        json += "\"channel\":";
        json += String(reading.channel);
        json += ",";

        json += "\"heading\":";
        json += String(reading.heading, 2);
        json += ",";

        json += "\"pitch\":";
        json += String(reading.pitch, 2);
        json += ",";

        json += "\"roll\":";
        json += String(reading.roll, 2);
        json += ",";

        json += "\"piezo_left\":";
        json += String(reading.piezo_left);
        json += ",";

        json += "\"piezo_right\":";
        json += String(reading.piezo_right);
        
        json += "}";

        if (i < NUM_IMUS - 1)
        {
            json += ",";
        }
    }

    json += "],";

    // ---------------- System state --------------

    json += "\"action_flag\":";
    json += actionTriggered ? "true" : "false";
    json += "}";

    return json;
}