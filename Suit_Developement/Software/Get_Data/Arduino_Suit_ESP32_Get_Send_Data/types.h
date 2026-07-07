#pragma once


// ================================================
// Types.h
// ================================================


// ----------------- Data structures --------------


struct SensorReading
{
    uint8_t channel;
    float heading;
    float pitch;
    float roll;

    int piezo;
};