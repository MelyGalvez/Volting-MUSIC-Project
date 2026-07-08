import time
import threading


import config
from communication import (
    get_sensor_data,
    send_led,
    send_vibration
)
from keyboard_control import (
    keyboard_listener,
    stop_keyboard_listener
)
from display import display_sensor_data
from led_control import (
    toggle_green,
    toggle_orange,
    toggle_red
)
from vibration_control import (
    toggle_left,
    toggle_right
)


# ==========================================
# MAIN PROGRAM
# ==========================================


http_lock = threading.Lock()


# ---------------- Keyboard ----------------


keyboard_listener(
    green=toggle_green,
    orange=toggle_orange,
    red=toggle_red,
    left_vibration=toggle_left,
    right_vibration=toggle_right
)


# ---------------- Main loop ----------------


try:

    while True:

        with http_lock:

            data = get_sensor_data()

        display_sensor_data(
            data
        )

        time.sleep(
            config.UPDATE_PERIOD
        )

except KeyboardInterrupt:

    print("\nProgram stopped")

except Exception as e:

    print(e)

finally:

    stop_keyboard_listener()

    send_led(
        green=False,
        orange=False,
        red=False
    )

    send_vibration(
        left=False,
        right=False
    )