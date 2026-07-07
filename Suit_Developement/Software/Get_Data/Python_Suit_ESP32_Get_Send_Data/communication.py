import requests

import config


# =================================================
# COMMUNICATION
# =================================================


# ------------------ Send data  -------------------


def send_led(state: bool) -> bool:
    """
    Send LED state to ESP32.

    Parameters
    ----------
    state : bool
        LED state.

    Returns
    -------
    bool
        True if request succeeded.
    """

    value = 1 if state else 0

    try:
        response = requests.get(
            f"{config.ESP32}/led?on={value}",
            timeout=config.REQUEST_TIMEOUT
        )

        print(
            f"LED = {state} | HTTP {response.status_code}"
        )

        return True

    except Exception as e:
        print("[LED ERROR]", e)

        return False


# ------------------- Receive data ----------------


def get_sensor_data() -> dict | None:
    """
    Request IMU measurements from ESP32.

    Returns
    -------
    dict
        JSON data received from ESP32.
    """

    try:
        response = requests.get(
            f"{config.ESP32}/data",
            timeout=config.REQUEST_TIMEOUT
        )

        return response.json()


    except Exception as e:
        print("[DATA ERROR]", e)

        return None