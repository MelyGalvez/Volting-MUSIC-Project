import keyboard
from typing import Callable


# ==========================================
# KEYBOARD CONTROL
# ==========================================


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

    if green is not None:
        keyboard.add_hotkey("g", green)

    if orange is not None:
        keyboard.add_hotkey("o", orange)

    if red is not None:
        keyboard.add_hotkey("r", red)

    if left_vibration is not None:
        keyboard.add_hotkey("left", left_vibration)

    if right_vibration is not None:
        keyboard.add_hotkey("right", right_vibration)


# ------------ Stop listener ---------------


def stop_keyboard_listener() -> None:
    """
    Stop keyboard listener.
    """

    keyboard.unhook_all_hotkeys()