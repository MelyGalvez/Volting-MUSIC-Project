import quaternion as quat


# ================================================
# CALIBRATION
# ================================================


references = {}

calibrated = False


# ---------------- Data conversion ----------------


def _to_body_dict(data):
    """
    Convert IMU data into a body-indexed dictionary.

    The function accepts either the raw ESP32 JSON packet
    containing an "imu_data" list or an already body-indexed
    dictionary and always returns a dictionary indexed by body
    segment names.

    """
    
    if not data:
        return {}

    if isinstance(data, dict) and "imu_data" in data:
        result = {}
        for imu in data["imu_data"]:
            body = imu.get("body")
            if body is not None:
                result[body] = imu
        return result

    if isinstance(data, dict):
        return data

    return {}


def calibrate(data):
    """
    Perform the software calibration.

    The current quaternion of every available IMU is stored as the
    reference orientation. Future measurements are expressed
    relative to this calibration pose.

    """
    
    global references
    global calibrated

    body_data = _to_body_dict(data)

    new_refs = {}

    for body, imu in body_data.items():
        try:
            q = quat.normalize((
                float(imu["qw"]),
                float(imu["qx"]),
                float(imu["qy"]),
                float(imu["qz"]),
            ))
        except (TypeError, KeyError, ValueError):
            continue
        new_refs[body] = q

    if not new_refs:
        print("Calibration skipped: no valid quaternion data")
        return False

    references = new_refs
    calibrated = True

    print("Calibration finished (quaternion re-zero)")
    return True


# -------------- Calibration offset ---------------


def apply_offset(body, q):
    """
    Apply the software calibration offset.

    The function computes the orientation of the current
    quaternion relative to the stored calibration reference.
    If no calibration has been performed, the quaternion is
    returned unchanged.

    """
    
    if not calibrated or body not in references:
        return q

    return quat.delta(q, references[body])