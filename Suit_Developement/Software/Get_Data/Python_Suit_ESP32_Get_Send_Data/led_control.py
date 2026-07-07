from communication import send_led


# =================================================
# LED CONTROL
# =================================================


# ------------------ LED Toggle -------------------


led_state = False


def toggle_led() -> None:
    """
    @brief Toggle ESP32 LED state.

    This function changes the current LED state and sends
    the new value to the ESP32 through HTTP.

    @return None
    """

    global led_state


    led_state = not led_state


    send_led(
        led_state
    )