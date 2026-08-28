#include <Arduino.h>
#include <inttypes.h>
#include <stdarg.h>

#include "json.h"
#include "status.h"


// ================================================
// JSON.cpp
// ================================================


// -------------- Body name table -----------------


static const char* const BODY_NAMES[NUM_IMUS] =
{
    "back_upper",
    "back_lower",
    "left_arm",
    "right_arm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand"
};


static const bool BODY_TRANSMITTED[NUM_IMUS] =
{
    true,     // back_upper
    true,     // back_lower
    true,     // left_arm
    true,     // right_arm
    true,     // left_forearm
    true,     // right_forearm
    true,     // left_hand
    true      // right_hand
};


const char* bodyName(uint8_t index)
{
    return (index < NUM_IMUS) ? BODY_NAMES[index] : "unknown";
}


// --------------- Append helper -----------------


static bool appendf(
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


// --------------- JSON generation ---------------


size_t buildJson(
    char* buf,
    size_t cap,
    const Snapshot& snap,
    SystemState state
)
{
    size_t off = 0;
    bool ok = true;

    ok &= appendf(
        buf, cap, off,
        "{\"v\":2,\"seq\":%" PRIu32
        ",\"timestamp\":%" PRIu64
        ",\"system\":\"%s\",",
        snap.seq,
        snap.timestampMs,
        systemStateName(state)
    );

    ok &= appendf(
        buf, cap, off,
        "\"piezo\":{"
        "\"left\":{\"peak\":%u,\"hits\":%" PRIu32
        ",\"hit_peak\":%u},"
        "\"right\":{\"peak\":%u,\"hits\":%" PRIu32
        ",\"hit_peak\":%u}},",
        (unsigned)snap.piezoLeft.peak,
        snap.piezoLeft.hitCount,
        (unsigned)snap.piezoLeft.lastHitPeak,
        (unsigned)snap.piezoRight.peak,
        snap.piezoRight.hitCount,
        (unsigned)snap.piezoRight.lastHitPeak
    );

    ok &= appendf(buf, cap, off, "\"imu_data\":[");

    uint8_t emitted = 0;

    for(uint8_t i = 0; i < NUM_IMUS && ok; i++)
    {
        if(!BODY_TRANSMITTED[i])
        {
            continue;
        }

        const ImuFrame& f = snap.imu[i];

        ok &= appendf(
            buf, cap, off,
            "%s{\"body\":\"%s\","
            "\"ok\":%s,\"cal\":%s,"
            "\"heading\":%.2f,\"pitch\":%.2f,"
            "\"roll\":%.2f,",
            (emitted > 0) ? "," : "",
            BODY_NAMES[i],
            f.ok ? "true" : "false",
            f.calibrated ? "true" : "false",
            (double)f.euler.heading,
            (double)f.euler.pitch,
            (double)f.euler.roll
        );

        ok &= appendf(
            buf, cap, off,
            "\"accel\":{\"x\":%.2f,\"y\":%.2f,"
            "\"z\":%.2f},"
            "\"total_accel\":{\"x\":%.2f,\"y\":%.2f,"
            "\"z\":%.2f},"
            "\"lin_accel\":{\"x\":%.2f,\"y\":%.2f,"
            "\"z\":%.2f},"
            "\"gravity\":{\"x\":%.2f,\"y\":%.2f,"
            "\"z\":%.2f},",
            (double)f.accel.x,
            (double)f.accel.y,
            (double)f.accel.z,
            (double)f.accel.x,
            (double)f.accel.y,
            (double)f.accel.z,
            (double)f.linAccel.x,
            (double)f.linAccel.y,
            (double)f.linAccel.z,
            (double)f.gravity.x,
            (double)f.gravity.y,
            (double)f.gravity.z
        );

        ok &= appendf(
            buf, cap, off,
            "\"gyro\":{\"x\":%.2f,\"y\":%.2f,"
            "\"z\":%.2f},"
            "\"mag\":{\"x\":%.2f,\"y\":%.2f,"
            "\"z\":%.2f},",
            (double)f.gyro.x,
            (double)f.gyro.y,
            (double)f.gyro.z,
            (double)f.mag.x,
            (double)f.mag.y,
            (double)f.mag.z
        );

        ok &= appendf(
            buf, cap, off,
            "\"temp\":%d,"
            "\"calib\":{\"sys\":%u,\"gyro\":%u,"
            "\"accel\":%u,\"mag\":%u},"
            "\"status\":{\"system\":%u,"
            "\"self_test\":%u,\"error\":%u}}",
            (int)f.temperature,
            (unsigned)f.calibSys,
            (unsigned)f.calibGyro,
            (unsigned)f.calibAccel,
            (unsigned)f.calibMag,
            (unsigned)f.sysStatus,
            (unsigned)f.selfTest,
            (unsigned)f.sysError
        );

        emitted++;
    }

    ok &= appendf(buf, cap, off, "]}");

    return ok ? off : 0;
}