import math


# ==========================================
# QUATERNION
# ==========================================


# -------------- Euler limits --------------


_EULER_PITCH_LIMIT_DEG = 180.0
_EULER_YAW_LIMIT_DEG = 360.0


# ---------- Quaternion calculation --------


def identity():
    """
    Return the identity quaternion representing a zero rotation.

    """
    
    return (1.0, 0.0, 0.0, 0.0)


def normalize(q):
    """
        Normalize a quaternion to unit length.
        Returns the identity quaternion if the input
        is degenerate.

    """
    
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n == 0.0:
        return identity()
    return (w / n, x / n, y / n, z / n)


def conjugate(q):
    """
    Compute the conjugate of a quaternion.
    For a unit quaternion, this is also its inverse.

    """
    
    w, x, y, z = q
    return (w, -x, -y, -z)


def multiply(a, b):
    """
    Compute the Hamilton product of two quaternions.

    """
    
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def rotate_vector(q, v):
    """
    Rotate a three-dimensional vector using a quaternion.

    """
    
    qv = (0.0, v[0], v[1], v[2])
    r = multiply(multiply(q, qv), conjugate(q))
    return (r[1], r[2], r[3])


def delta_local(current, reference):
    """
    Rotation from the reference orientation to the current
    orientation, expressed in the REFERENCE (sensor-at-
    calibration) frame:

        delta = conj(reference) * current

    This is the convention required by the per-sensor
    mounting corrections in imu_mapping (applied as
    C * delta * conj(C)): the delta's rotation axes must
    live in the frame that the mounting table describes.
    The previous current * conj(reference) form produced a
    world-frame delta, which made displayed rotation axes
    depend on which way the user faced during calibration.

    """

    return multiply(conjugate(reference), current)


def to_euler(q):
    """
    Convert a quaternion into heading, pitch
    and roll angles expressed in degrees.

    Aerospace Z-Y-X convention: the triplet describes the
    intrinsic composition Rz(heading) . Ry(pitch) . Rx(roll).
    Identical formulas to quatToEuler() in the firmware
    (quat.h), which is what produces the angles on the wire.

    """
    
    w, x, y, z = normalize(q)
    
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)

    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    heading = math.atan2(siny_cosp, cosy_cosp)

    return {
        "heading": math.degrees(heading),
        "pitch": math.degrees(pitch),
        "roll": math.degrees(roll),
    }


def from_euler(heading, pitch, roll):
    """
    Build the quaternion of an aerospace Z-Y-X Euler triplet
    given in degrees.

    Exact inverse of to_euler(), and therefore of the
    firmware's quatToEuler(): feeding it the transmitted
    heading/pitch/roll reconstructs the very quaternion the
    firmware derived them from (up to the double cover, q and
    -q being the same rotation, and up to the 0.01 deg
    quantization of the wire format).

    The rotation is the intrinsic composition

        q = Rz(heading) . Ry(pitch) . Rx(roll)

    so the axes are the ones the firmware used: heading about
    the sensor Z axis, pitch about Y, roll about X, all of
    them expressed in the sensor frame captured at T-pose
    calibration. That is precisely the frame the mounting
    table in imu_mapping describes, which is why the rebuilt
    quaternion can be fed unchanged to the existing pipeline.

    """

    h = math.radians(heading) * 0.5
    p = math.radians(pitch) * 0.5
    r = math.radians(roll) * 0.5

    ch, sh = math.cos(h), math.sin(h)
    cp, sp = math.cos(p), math.sin(p)
    cr, sr = math.cos(r), math.sin(r)

    return (
        cr * cp * ch + sr * sp * sh,
        sr * cp * ch - cr * sp * sh,
        cr * sp * ch + sr * cp * sh,
        cr * cp * sh - sr * sp * ch,
    )


def dot(a, b):
    """
    Quaternion dot product.
    
    """
    
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]


def negate(q):
    """
    Return -q (same rotation, opposite hemisphere).
    
    """
    
    return (-q[0], -q[1], -q[2], -q[3])


def same_hemisphere(q, reference):
    """
    Return q or -q so that it lies in the same hemisphere as
    reference. Quaternions double-cover rotations (q and -q are
    the same orientation); aligning hemispheres avoids interpolating
    or measuring "the long way around".
    
    """
    
    if dot(q, reference) < 0.0:
        return negate(q)
    return q


def angle_between(a, b):
    """
    Shortest rotation angle between two quaternions, in degrees.
    
    """
    
    d = abs(dot(normalize(a), normalize(b)))
    d = min(1.0, max(-1.0, d))
    return math.degrees(2.0 * math.acos(d))


def slerp(a, b, t):
    """
    Spherical linear interpolation from a to b by fraction t.
    Handles the double cover and falls back to normalized lerp for
    nearly-parallel quaternions.
    
    """
    
    a = normalize(a)
    b = normalize(b)

    d = dot(a, b)
    if d < 0.0:
        b = negate(b)
        d = -d

    if d > 0.9995:
        r = (
            a[0] + t * (b[0] - a[0]),
            a[1] + t * (b[1] - a[1]),
            a[2] + t * (b[2] - a[2]),
            a[3] + t * (b[3] - a[3]),
        )
        return normalize(r)

    theta0 = math.acos(d)
    theta = theta0 * t
    sin0 = math.sin(theta0)

    s0 = math.sin(theta0 - theta) / sin0
    s1 = math.sin(theta) / sin0

    return (
        s0 * a[0] + s1 * b[0],
        s0 * a[1] + s1 * b[1],
        s0 * a[2] + s1 * b[2],
        s0 * a[3] + s1 * b[3],
    )


def is_valid(q):
    """
    True if q is a finite, non-degenerate quaternion.
    
    """
    
    if q is None or len(q) != 4:
        return False
    if not all(math.isfinite(c) for c in q):
        return False
    norm_sq = q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]
    return norm_sq > 1e-9


def is_valid_euler(heading, pitch, roll):
    """
    True if a heading/pitch/roll triplet can be a real pose.

    Rejects the NaN/inf and the absurd magnitudes a corrupted
    packet produces. The bounds stay deliberately loose (the
    firmware emits pitch in [-90, 90] and the two atan2 angles
    in [-180, 180]) so a differently wrapped but perfectly
    valid heading is never dropped: from_euler() handles any
    wrapping.

    """

    if not all(math.isfinite(a) for a in (heading, pitch, roll)):
        return False

    return (
        abs(heading) <= _EULER_YAW_LIMIT_DEG
        and abs(pitch) <= _EULER_PITCH_LIMIT_DEG
        and abs(roll) <= _EULER_YAW_LIMIT_DEG
    )


def from_json(imu):
    """
    Extract the orientation of one IMU JSON object.

    The firmware transmits the T-pose-relative rotation of
    each sensor as its Euler triplet (heading, pitch, roll, in
    degrees) instead of the delta quaternion it derives them
    from. Since from_euler() inverts that derivation exactly,
    this rebuilds the same local delta quaternion the pipeline
    received before: the software re-zero, the mounting
    correction, the SLERP filter and the forward kinematics
    downstream are untouched, and the displayed motion is
    unchanged.

    Returns None when the fields are missing or implausible so
    the caller can skip the sample and hold the last good
    pose. (The previous behaviour returned identity, which
    snapped the bone back to T-pose on any parse failure.)

    """

    try:
        heading = float(imu["heading"])
        pitch = float(imu["pitch"])
        roll = float(imu["roll"])
    except (KeyError, TypeError, ValueError):
        return None

    if not is_valid_euler(heading, pitch, roll):
        return None

    return from_euler(heading, pitch, roll)