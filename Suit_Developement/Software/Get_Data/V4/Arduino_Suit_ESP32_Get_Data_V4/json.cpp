#include <Arduino.h>
#include <inttypes.h>
#include <stdarg.h>

#include "json.h"
#include "status.h"


// ================================================
// JSON.cpp
//
// Serialization into a caller-provided fixed buffer
// with snprintf. The previous implementation built
// the packet by concatenating an Arduino String
// (~100 heap reallocations per request at up to
// 100 req/s), a classic source of heap fragmentation
// during long sessions. This version performs zero
// heap allocations.
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


// --------------- Append helper ------------------


// Appends printf-formatted text at *offset, returns false
// (and poisons the offset) when the buffer would overflow.
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


// ---------------- JSON generation ---------------


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

    for(uint8_t i = 0; i < NUM_IMUS && ok; i++)
    {
        const ImuFrame& f = snap.imu[i];

        // Quaternion components are in [-1, 1]; 4 decimals
        // quantize to ~0.006 deg. Euler at 2 decimals.
        ok &= appendf(
            buf, cap, off,
            "%s{\"body\":\"%s\","
            "\"ok\":%s,\"cal\":%s,"
            "\"qw\":%.4f,\"qx\":%.4f,"
            "\"qy\":%.4f,\"qz\":%.4f,"
            "\"heading\":%.2f,\"pitch\":%.2f,"
            "\"roll\":%.2f,",
            (i > 0) ? "," : "",
            BODY_NAMES[i],
            f.ok ? "true" : "false",
            f.calibrated ? "true" : "false",
            (double)f.quat.w,
            (double)f.quat.x,
            (double)f.quat.y,
            (double)f.quat.z,
            (double)f.euler.heading,
            (double)f.euler.pitch,
            (double)f.euler.roll
        );

        // Accelerations at 2 decimals match the BNO055 LSB
        // (0.01 m/s^2). The accelerometer output already is
        // the total acceleration (gravity + linear), so it
        // is exported under both names for consumers.
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

        // Gyro in deg/s and mag in uT (both LSB 1/16; mag
        // reads zero while the IMUPLUS mode is active).
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

        // Diagnostics refresh round-robin (one sensor per
        // scan), so they may lag the vectors by ~100 ms.
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
    }

    ok &= appendf(buf, cap, off, "]}");

    return ok ? off : 0;
}
