#pragma once

#include "types.h"


// ================================================
// QUAT.h
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


// ---------- Delta relative to a reference -------


inline Quaternion quatDelta(
    const Quaternion& current,
    const Quaternion& reference
)
{
    return quatMultiply(current, quatConjugate(reference));
}