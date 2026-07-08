from communication import send_led


# ==========================================
# LED CONTROL
# ==========================================


# --------------- LED toggle ---------------


green_state = False
orange_state = False
red_state = False 
    
def toggle_green():
    """
    @brief Toggle ESP32 green LED state.

    This function changes the current green LED state and sends
    the new value to the ESP32 through HTTP.

    @return None
    """
    
    global green_state

    green_state = not green_state

    send_led(
        green=green_state,
        orange=orange_state,
        red=red_state
    )


def toggle_orange():
    """
    @brief Toggle ESP32 orange LED state.

    This function changes the current orange LED state and sends
    the new value to the ESP32 through HTTP.

    @return None
    """
    
    global orange_state

    orange_state = not orange_state

    send_led(
        green=green_state,
        orange=orange_state,
        red=red_state
    )


def toggle_red():
    """
    @brief Toggle ESP32 red LED state.

    This function changes the current red LED state and sends
    the new value to the ESP32 through HTTP.

    @return None
    """
    
    global red_state

    red_state = not red_state

    send_led(
        green=green_state,
        orange=orange_state,
        red=red_state
    )