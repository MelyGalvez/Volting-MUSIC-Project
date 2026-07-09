import requests


# =================================================
# VIBRATION
# =================================================


def update_vibration(ESP32: str, left: bool, right: bool) -> None:
    """
    Send the vibration state to the ESP32.
    """

    try:

        requests.get(
            f"{ESP32}/vibration?left={int(left)}&right={int(right)}",
            timeout=0.2
        )

    except Exception as e:
        print(e)