from communication import send_vibration


# ==========================================
# VIBRATION CONTROL
# ==========================================


# ------------ Vibration toggle ------------


left_state = False
right_state = False


# ------------- Left vibration -------------


def toggle_left() -> None:
    """
    @brief Toggle ESP32 left vibrator state.

    This function changes the current left vibrator state and sends
    the new value to the ESP32 through HTTP.

    @return None
    """

    global left_state

    left_state = not left_state

    send_vibration(
        left=left_state,
        right=right_state
    )


# ------------ Right vibration -------------


def toggle_right() -> None:
    """
    @brief Toggle ESP32 right vibrator state.

    This function changes the current right vibrator state and sends
    the new value to the ESP32 through HTTP.

    @return None
    """

    global right_state

    right_state = not right_state

    send_vibration(
        left=left_state,
        right=right_state
    )