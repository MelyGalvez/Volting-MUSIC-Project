#pragma once

#include <math.h>

#include "types.h"


// ================================================
// QUAT.h
// ================================================


// ----------------- Conjugate -------------------


inline Quaternion quatConjugate(const Quaternion& q)
{
    Quaternion r;
    r.w =  q.w;
    r.x = -q.x;
    r.y = -q.y;
    r.z = -q.z;
    return r;
}


// -------------- Hamilton product ---------------


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


// ----------------- Norm tools ------------------


inline float quatNormSq(const Quaternion& q)
{
    return q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z;
}


inline Quaternion quatNormalize(const Quaternion& q)
{
    float n = sqrtf(quatNormSq(q));

    if(n < 1e-6f)
    {
        return Quaternion{};
    }

    Quaternion r;
    r.w = q.w / n;
    r.x = q.x / n;
    r.y = q.y / n;
    r.z = q.z / n;
    return r;
}


// ------------------ Validation ------------------


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


inline Quaternion quatDeltaLocal(
    const Quaternion& current,
    const Quaternion& reference
)
{
    return quatMultiply(quatConjugate(reference), current);
}


// -------------- Euler conversion ----------------


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