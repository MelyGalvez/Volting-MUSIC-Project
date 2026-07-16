import math


# ================================================
# QUATERNION
# ================================================


# ------------- Quaternion calculation ------------


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


def delta(current, reference):
    """
    Compute the quaternion representing the
    rotation from a reference orientation to
    the current orientation.

    """
    
    return multiply(current, conjugate(reference))


def to_euler(q):
    """
    Convert a quaternion into heading, pitch
    and roll angles expressed in degrees.
    Intended for debugging only.

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


def from_json(imu, default=None):
    """
    Extract a quaternion from one IMU JSON object.

    Returns default (identity if not given) when the quaternion
    fields are missing, so the pipeline stays robust against an
    older firmware that only sends Euler angles.
    
    """
    if default is None:
        default = identity()

    try:
        q = (
            float(imu["qw"]),
            float(imu["qx"]),
            float(imu["qy"]),
            float(imu["qz"]),
        )
    except (KeyError, TypeError, ValueError):
        return default

    return normalize(q)