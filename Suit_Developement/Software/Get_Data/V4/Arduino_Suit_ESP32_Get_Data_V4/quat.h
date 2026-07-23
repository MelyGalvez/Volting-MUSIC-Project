#pragma once

#include <math.h>

#include "types.h"


// ================================================
// QUAT.h
//
// Header-only quaternion math. Convention: Hamilton
// product, component order (w, x, y, z), unit
// quaternions represent rotations.
// ================================================


// ------------------ Conjugate -------------------


inline Quaternion quatConjugate(const Quaternion& q)
{
    Quaternion r;
    r.w =  q.w;
    r.x = -q.x;
    r.y = -q.y;
    r.z = -q.z;
    return r;
}


// --------------- Hamilton product ---------------


inline Quaternion quatMultiply(
    const Quaternion& a,
    const Quaternion& b
)
{
    Quaternion r;
    r.w = a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z;
    r.x = a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y;
    r.y = a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x;
    r.z = a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w;
    return r;
}


// ------------------ Norm tools ------------------


inline float quatNormSq(const Quaternion& q)
{
    return q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z;
}


inline Quaternion quatNormalize(const Quaternion& q)
{
    float n = sqrtf(quatNormSq(q));

    if(n < 1e-6f)
    {
        return Quaternion{};    // identity
    }

    Quaternion r;
    r.w = q.w / n;
    r.x = q.x / n;
    r.y = q.y / n;
    r.z = q.z / n;
    return r;
}


// ------------------ Validation ------------------


// A BNO055 read that fails on the bus returns all zeros;
// a corrupted read returns a wildly non-unit quaternion.
// Both are rejected here before entering the pipeline.
inline bool quatIsValid(const Quaternion& q)
{
    if(isnan(q.w) || isnan(q.x) || isnan(q.y) || isnan(q.z))
    {
        return false;
    }

    if(isinf(q.w) || isinf(q.x) || isinf(q.y) || isinf(q.z))
    {
        return false;
    }

    float n = quatNormSq(q);

    return n > 0.7f && n < 1.3f;
}


// ---------- Delta relative to a reference -------


// Rotation from the reference pose to the current pose,
// expressed in the SENSOR frame at calibration time:
//
//     delta = conj(reference) * current
//
// This is the correct convention for downstream per-sensor
// mounting corrections (applied as C * delta * conj(C)):
// the delta's rotation axes live in the sensor frame that
// the mounting table describes. The previous firmware used
// current * conj(reference) (a world-frame delta), which
// made displayed rotation axes depend on which way the
// user faced during calibration.
inline Quaternion quatDeltaLocal(
    const Quaternion& current,
    const Quaternion& reference
)
{
    return quatMultiply(quatConjugate(reference), current);
}


// -------------- Euler conversion ----------------


// Aerospace Z-Y-X (yaw-pitch-roll) angles in degrees.
// Computed from the delta quaternion, so the results are
// inherently T-pose-relative and wrap-safe: no offset
// subtraction (and no 0/360 discontinuity) is ever needed.
inline void quatToEuler(
    const Quaternion& q,
    float& heading,
    float& pitch,
    float& roll
)
{
    constexpr float RAD_TO_DEG_F = 57.29577951308232f;

    float sinp = 2.0f * (q.w * q.y - q.z * q.x);

    if(sinp > 1.0f)  sinp = 1.0f;
    if(sinp < -1.0f) sinp = -1.0f;

    pitch = asinf(sinp) * RAD_TO_DEG_F;

    heading = atan2f(
        2.0f * (q.w * q.z + q.x * q.y),
        1.0f - 2.0f * (q.y * q.y + q.z * q.z)
    ) * RAD_TO_DEG_F;

    roll = atan2f(
        2.0f * (q.w * q.x + q.y * q.z),
        1.0f - 2.0f * (q.x * q.x + q.y * q.y)
    ) * RAD_TO_DEG_F;
}
