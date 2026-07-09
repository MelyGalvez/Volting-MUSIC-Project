import requests

import config


# ==========================================
# COMMUNICATION
# ==========================================


# ---------------- Send data  --------------


def send_led(
    green: bool = False,
    orange: bool = False,
    red: bool = False
) -> bool:
    """
    Send LED states to ESP32.

    Parameters
    ----------
    green : bool
        Green LED state.
    orange : bool
        Orange LED state.
    red : bool
        Red LED state.

    Returns
    -------
    bool
        True if request succeeded.
    """

    try:

        response = requests.get(
            f"{config.ESP32}/led"
            f"?green={int(green)}"
            f"&orange={int(orange)}"
            f"&red={int(red)}",
            timeout=config.REQUEST_TIMEOUT
        )

        print(
            f"LED -> G:{green} O:{orange} R:{red} | "
            f"HTTP {response.status_code}"
        )

        return True

    except Exception as e:

        print("[LED ERROR]", e)

        return False
    
def send_vibration(
    left: bool = False,
    right: bool = False,
) -> bool:
    """
    Send vibration states to ESP32.

    Parameters
    ----------
    left : bool
        Left vibrator state.
    right : bool
        Right vibrator state.

    Returns
    -------
    bool
        True if request succeeded.
    """

    try:

        response = requests.get(
            f"{config.ESP32}/vibration"
            f"?left={int(left)}"
            f"&right={int(right)}",
            timeout=config.REQUEST_TIMEOUT
        )

        print(
            f"Vibration -> Left:{left} Right:{right} | "
            f"HTTP {response.status_code}"
        )

        return True

    except Exception as e:

        print("[VIBRATION ERROR]", e)

        return False


# -------------- Receive data --------------


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