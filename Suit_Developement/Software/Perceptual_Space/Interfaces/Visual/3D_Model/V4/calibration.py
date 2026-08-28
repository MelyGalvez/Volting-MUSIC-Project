import quaternion as quat


# ==========================================
# CALIBRATION
# ==========================================


references = {}

calibrated = False


# ------------- Data conversion ------------


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

    The current orientation of every available IMU is stored
    as the reference orientation. Sensors flagged not-ok by
    the firmware are skipped so a dropped sensor cannot poison
    its reference. Future measurements are expressed relative
    to this calibration pose.

    This is also what makes an uncalibrated sensor (cal:false,
    no T-pose reference on the ESP32) usable again: the
    reference it lacks is supplied here instead.

    """

    global references
    global calibrated

    body_data = _to_body_dict(data)

    new_refs = {}

    for body, imu in body_data.items():
        if imu.get("ok") is False:
            continue

        q = quat.from_json(imu)

        if q is None:
            continue

        new_refs[body] = q

    if not new_refs:
        print("Calibration skipped: no valid orientation data")
        return False

    references = new_refs
    calibrated = True

    print(
        "Calibration finished "
        f"({len(new_refs)} sensors re-zeroed)"
    )
    return True


# ------------ Calibration offset ----------


def has_reference(body):
    """
    True when a software reference exists for this segment.

    Lets the caller tell apart a sensor the ESP32 could not
    zero (cal:false) but that was re-zeroed here, from one that
    has no T-pose reference at all and whose transmitted angles
    are therefore absolute instead of T-pose-relative.

    """

    return calibrated and body in references


def apply_offset(body, q):
    """
    Apply the software calibration offset.

    Returns the orientation of the current quaternion
    relative to the stored reference, expressed in the
    reference frame (local delta). If no calibration has
    been performed, the quaternion is returned unchanged.

    """

    if not calibrated or body not in references:
        return q

    return quat.delta_local(q, references[body])