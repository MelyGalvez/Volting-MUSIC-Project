# =================================================
# DISPLAY FUNCTIONS
# =================================================


# ----------------- Display data ------------------


def display_sensor_data(data: dict | None) -> None:
    """
    @brief Display IMU sensor data received from the ESP32.

    This function extracts sensor measurements from the JSON response
    received from the ESP32 and prints the values of each IMU channel,
    including Euler angles, piezo value and action status.

    @param data Dictionary containing ESP32 JSON response.
                 Expected keys:
                 - imu_data: list of IMU measurements
                 - action_flag: system action state

    @return None
    """

    if data is None:
        return


    imu_readings = data.get(
        "imu_data",
        []
    )


    action_flag = data.get(
        "action_flag",
        False
    )


    print("\n===============================================")
    print("          [ STATUS MULTI-IMU RX ]")
    print("-----------------------------------------------")


    for reading in imu_readings:

        print(
            f"CH {reading['channel']} | "
            f"H={reading['heading']:.1f} "
            f"P={reading['pitch']:.1f} "
            f"R={reading['roll']:.1f} "
            f"Piezo={reading['piezo']}"
        )


    print("-----------------------------------------------")
    print("Action TX:", action_flag)