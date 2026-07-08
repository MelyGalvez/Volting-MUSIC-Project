from pynput import keyboard
from typing import Callable


# ==========================================
# KEYBOARD CONTROL
# ==========================================


# ---------------- Callbacks ---------------


green_callback = None
orange_callback = None
red_callback = None

left_vibration_callback = None
right_vibration_callback = None


# -------------- Key pressed ---------------


def on_press(key):
    """
    Keyboard callback.
    """

    try:

        if key == keyboard.Key.left and left_vibration_callback:
            left_vibration_callback()

        elif key == keyboard.Key.right and right_vibration_callback:
            right_vibration_callback()

        elif hasattr(key, "char"):

            key = key.char.lower()

            if key == "g" and green_callback:
                green_callback()

            elif key == "o" and orange_callback:
                orange_callback()

            elif key == "r" and red_callback:
                red_callback()

    except Exception as e:

        print(e)


# ------------ Keyboard listener -----------


def keyboard_listener(
    green: Callable[[], None] | None = None,
    orange: Callable[[], None] | None = None,
    red: Callable[[], None] | None = None,
    left_vibration: Callable[[], None] | None = None,
    right_vibration: Callable[[], None] | None = None
) -> None:
    """
    Start keyboard listener.
    """

    global green_callback
    global orange_callback
    global red_callback
    global left_vibration_callback
    global right_vibration_callback

    green_callback = green
    orange_callback = orange
    red_callback = red

    left_vibration_callback = left_vibration
    right_vibration_callback = right_vibration

    listener = keyboard.Listener(
        on_press=on_press
    )

    listener.daemon = True
    listener.start()