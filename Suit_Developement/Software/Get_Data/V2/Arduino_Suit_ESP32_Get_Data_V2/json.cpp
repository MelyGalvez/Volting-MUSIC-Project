#include "json.h"

#include "global.h"

// ======================================================
// JSON
// ======================================================


// ---------- Convert body part to string ----------

static String bodyName(BodyPart body)
{
    switch(body)
    {
        case BACK_UPPER:      return "back_upper";
        case BACK_LOWER:      return "back_lower";

        case LEFT_ARM:        return "left_arm";
        case RIGHT_ARM:       return "right_arm";

        case LEFT_FOREARM:    return "left_forearm";
        case RIGHT_FOREARM:   return "right_forearm";

        case LEFT_HAND:       return "left_hand";
        case RIGHT_HAND:      return "right_hand";

        default:              return "unknown";
    }
}


// ---------- Convert system state ----------

static String stateName(SystemState state)
{
    switch(state)
    {
        case SYSTEM_BOOT:
            return "boot";

        case SYSTEM_CALIBRATION:
            return "calibration";

        case SYSTEM_READY:
            return "ready";

        case SYSTEM_ERROR:
            return "error";

        default:
            return "unknown";
    }
}


// ---------- JSON generation ----------

String buildJson()
{
    String json = "{";

    // ==========================================
    // Timestamp
    // ==========================================

    json += "\"timestamp\":";
    json += millis();
    json += ",";

    // ==========================================
    // System state
    // ==========================================

    json += "\"system\":\"";
    json += stateName(systemState);
    json += "\",";

    // ==========================================
    // IMUs
    // ==========================================

    json += "\"imu_data\":[";

    for(uint8_t i=0;i<NUM_IMUS;i++)
    {
        json += "{";

        json += "\"body\":\"";
        json += bodyName(allReadings[i].body);
        json += "\",";

        json += "\"detected\":";
        json += imuStatus[i].detected ? "true":"false";
        json += ",";

        json += "\"calibrated\":";
        json += imuStatus[i].calibrated ? "true":"false";
        json += ",";

        json += "\"heading\":";
        json += String(allReadings[i].angle.heading,2);
        json += ",";

        json += "\"pitch\":";
        json += String(allReadings[i].angle.pitch,2);
        json += ",";

        json += "\"roll\":";
        json += String(allReadings[i].angle.roll,2);
        json += ",";

        json += "\"piezo_left\":";
        json += allReadings[i].piezoLeft;
        json += ",";

        json += "\"piezo_right\":";
        json += allReadings[i].piezoRight;

        json += "}";

        if(i < NUM_IMUS-1)
            json += ",";
    }

    json += "]";

    json += "}";

    return json;
}