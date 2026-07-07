import time
import threading


import config
from communication import get_sensor_data
from keyboard_control import keyboard_listener
from display import display_sensor_data
from led_control import toggle_led


# ==========================================================
# MAIN PROGRAM
# ==========================================================


http_lock = threading.Lock()


# ---------------- Keyboard ----------------


keyboard_listener(
    toggle_led
)


# ---------------- Main loop ----------------


while True:

    try:

        with http_lock:

            data = get_sensor_data()

        display_sensor_data(
            data
        )


        time.sleep(
            config.UPDATE_PERIOD
        )

    except KeyboardInterrupt:

        print(
            "\nProgram stopped"
        )

        break

    except Exception as e:

        print(e)

        time.sleep(1)