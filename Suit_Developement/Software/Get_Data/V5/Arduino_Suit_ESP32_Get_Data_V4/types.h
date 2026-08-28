#pragma once

#include <Arduino.h>

#include "config.h"


// ================================================
// TYPES.h
// ================================================


// ------------------ Body parts ------------------


enum BodyPart : uint8_t
{
    BACK_UPPER = 0,
    BACK_LOWER,

    LEFT_ARM,
    RIGHT_ARM,

    LEFT_FOREARM,
    RIGHT_FOREARM,

    LEFT_HAND,
    RIGHT_HAND
};


// ---------------- System states -----------------


enum SystemState : uint8_t
{
    SYSTEM_BOOT = 0,
    SYSTEM_CALIBRATION,
    SYSTEM_READY,

    SYSTEM_DEGRADED,

    SYSTEM_ERROR
};


// ------------------ Quaternion ------------------


struct Quaternion
{
    float w = 1.0f;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};


// ----------------- Euler angles -----------------


struct EulerAngles
{
    float heading = 0.0f;
    float pitch = 0.0f;
    float roll = 0.0f;
};


// ------------------- 3D vector ------------------


struct Vec3
{
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};


// ------------------ IMU frame -------------------


struct ImuFrame
{
    Quaternion quat;      // T-pose relative (sensor frame)
    EulerAngles euler;    // derived from quat

    Vec3 accel;           // accelerometer (total), m/s^2
    Vec3 linAccel;        // linear acceleration, m/s^2
    Vec3 gravity;         // gravity vector, m/s^2
    Vec3 gyro;            // angular velocity, deg/s
    Vec3 mag;             // magnetic field, uT

    int8_t temperature = 0;   // die temperature, deg C

    uint8_t calibSys = 0;
    uint8_t calibGyro = 0;
    uint8_t calibAccel = 0;
    uint8_t calibMag = 0;

    uint8_t sysStatus = 0;
    uint8_t selfTest = 0;
    uint8_t sysError = 0;

    bool ok = false;          // last read succeeded
    bool calibrated = false;  // T-pose reference captured
};


// ------------------ Piezo state -----------------


struct PiezoChannelState
{
    uint16_t peak = 0;

    uint16_t lastHitPeak = 0;

    uint32_t hitCount = 0;
};


// ------------------ Snapshot -------------------


struct Snapshot
{
    uint32_t seq = 0;
    uint64_t timestampMs = 0;

    ImuFrame imu[NUM_IMUS];

    PiezoChannelState piezoLeft;
    PiezoChannelState piezoRight;
};