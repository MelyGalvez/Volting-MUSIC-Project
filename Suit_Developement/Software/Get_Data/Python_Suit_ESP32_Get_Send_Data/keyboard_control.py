from pynput import keyboard
from typing import Callable


# =================================================
# KEYBOARD CONTROL
# =================================================


# --------------------- LED -----------------------


def keyboard_listener(callback: Callable[[], None]) -> None:
    """
    Start keyboard listener.

    Parameters
    ----------
    callback : function
        Function called when space is pressed.
    """


    def on_press(key):

        try:

            if key == keyboard.Key.space:

                callback()


        except Exception as e:

            print(e)



    listener = keyboard.Listener(
        on_press=on_press
    )


    listener.daemon = True
    listener.start()