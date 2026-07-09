#pragma once

#include <Arduino.h>


// ================================================
// TYPES.h
// ================================================


// ---------------- Body parts --------------------


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


// --------------- System states ------------------


enum SystemState : uint8_t
{
    SYSTEM_BOOT = 0,
    SYSTEM_CALIBRATION,
    SYSTEM_READY,
    SYSTEM_ERROR
};


// --------------- Euler angles -------------------


struct EulerAngles
{
    float heading = 0.0f;
    float pitch = 0.0f;
    float roll = 0.0f;
};


// ------------ Calibration offsets ---------------


struct CalibrationOffset
{
    float heading = 0.0f;
    float pitch = 0.0f;
    float roll = 0.0f;
};


// --------------- IMU states -------------------


struct IMUStatus
{
    bool detected = false;
    bool calibrated = false;
};


// -------------- Sensors reading -----------------


struct SensorReading
{
    BodyPart body;

    EulerAngles angle;

    int piezoLeft = 0;
    int piezoRight = 0;
};