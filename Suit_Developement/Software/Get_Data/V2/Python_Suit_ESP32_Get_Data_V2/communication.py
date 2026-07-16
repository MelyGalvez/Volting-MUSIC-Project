import requests

import config


# ==========================================
# COMMUNICATION
# ==========================================


def get_sensor_data() -> dict | None:
    """
    Read IMU data from the ESP32.
    """

    try:

        response = requests.get(
            f"{config.ESP32}/data",
            timeout=config.REQUEST_TIMEOUT
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:

        print("[HTTP ERROR]", e)

        return None