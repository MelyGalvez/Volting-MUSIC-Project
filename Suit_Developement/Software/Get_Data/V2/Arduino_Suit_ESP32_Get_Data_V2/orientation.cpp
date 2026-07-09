#include "orientation.h"

// ======================================================
// ORIENTATION
// ======================================================

Orientation imuOrientation[NUM_IMUS] =
{
    // BACK UPPER
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // BACK LOWER
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // LEFT ARM
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // RIGHT ARM
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // LEFT FOREARM
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // RIGHT FOREARM
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // LEFT HAND
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false},

    // RIGHT HAND
    {AXIS_X, AXIS_Y, AXIS_Z, false, false, false}
};


static float axisValue(
    Axis axis,
    float x,
    float y,
    float z
)
{
    switch(axis)
    {
        case AXIS_X: return x;
        case AXIS_Y: return y;
        default:     return z;
    }
}

void applyOrientation(
    uint8_t index,
    float& heading,
    float& pitch,
    float& roll
)
{
    Orientation o = imuOrientation[index];

    float x = heading;
    float y = pitch;
    float z = roll;

    heading = axisValue(o.headingAxis, x, y, z);
    pitch   = axisValue(o.pitchAxis, x, y, z);
    roll    = axisValue(o.rollAxis, x, y, z);

    if(o.invertHeading)
        heading = -heading;

    if(o.invertPitch)
        pitch = -pitch;

    if(o.invertRoll)
        roll = -roll;
}