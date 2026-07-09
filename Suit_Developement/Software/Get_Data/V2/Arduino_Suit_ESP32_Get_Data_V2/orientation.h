#pragma once

#include <Arduino.h>
#include "config.h"

// ======================================================
// ORIENTATION
// ======================================================

enum Axis : uint8_t
{
    AXIS_X = 0,
    AXIS_Y,
    AXIS_Z
};

struct Orientation
{
    Axis headingAxis;
    Axis pitchAxis;
    Axis rollAxis;

    bool invertHeading;
    bool invertPitch;
    bool invertRoll;
};

extern Orientation imuOrientation[NUM_IMUS];

/**
 * @brief Apply the orientation mapping of one IMU.
 */
void applyOrientation(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll
);