# ==========================================
# DISPLAY
# ==========================================


# -------------- Display data --------------


def display_sensor_data(data: dict | None) -> None:

    if data is None:
        return

    print("\n========================================")
    print(" ESP32 DATA")
    print("========================================")

    print("Timestamp :", data["timestamp"])
    print("System    :", data["system"])

    print("----------------------------------------")

    for imu in data["imu_data"]:

        print(
            f"{imu['body']:15s} | "
            f"H={imu['heading']:7.2f} "
            f"P={imu['pitch']:7.2f} "
            f"R={imu['roll']:7.2f} | "
            f"Detected={imu['detected']} "
            f"Cal={imu['calibrated']}"
        )

    print("----------------------------------------")

    print(
        "Piezo L:",
        data["imu_data"][0]["piezo_left"],
        "Piezo R:",
        data["imu_data"][0]["piezo_right"]
    )