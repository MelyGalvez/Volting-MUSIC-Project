import pygame.midi
import time

import config
import interface
from names import midi_name


# =================================================
# PLAYER
# =================================================


# ---------------- Initialization -----------------


pygame.midi.init()

player = pygame.midi.Output(1)

current_left = None
current_right = None


# ----------------- Instruments -------------------


LEFT_INSTRUMENT = 0
RIGHT_INSTRUMENT = 40

player.set_instrument(LEFT_INSTRUMENT, config.LEFT_CHANNEL)
player.set_instrument(RIGHT_INSTRUMENT, config.RIGHT_CHANNEL)


# ------------------- Callbacks -------------------


def change_left_instrument(event: object) -> None:
    """
    Update the MIDI instrument assigned to the left hand.

    This callback is triggered when the left instrument selection changes.
    """

    player.set_instrument(
        interface.INSTRUMENTS[interface.left_combo.get()],
        config.LEFT_CHANNEL
    )

def change_right_instrument(event: object) -> None:
    """
    Update the MIDI instrument assigned to the right hand.

    This callback is triggered when the right instrument selection changes.
    """

    player.set_instrument(
        interface.INSTRUMENTS[interface.right_combo.get()],
        config.RIGHT_CHANNEL
    )


# -------------------- Events ---------------------


interface.left_combo.bind(
    "<<ComboboxSelected>>",
    change_left_instrument
)

interface.right_combo.bind(
    "<<ComboboxSelected>>",
    change_right_instrument
)


# ---------------- Left player --------------------


def play_left(note: int, octave: int) -> None:
    """
    Play a MIDI note for the left hand.

    Stop the previously played note, play the new one and update
    the left-hand note display.
    """

    global current_left

    if note==current_left:
        return

    if current_left is not None:
        player.note_off(
            current_left,
            config.VELOCITY,
            config.LEFT_CHANNEL
        )

    current_left=note

    player.note_on(
        current_left,
        config.VELOCITY,
        config.LEFT_CHANNEL
    )

    interface.left_label.config(
        text=f"Left : {midi_name(note)} ({note}) | Octave : {octave}"
    )


# ---------------- Right player -------------------


def play_right(note: int, octave: int) -> None:
    """
    Play a MIDI note for the right hand.

    Stop the previously played note, play the new one and update
    the right-hand note display.
    """

    global current_right

    if note==current_right:
        return

    if current_right is not None:
        player.note_off(
            current_right,
            config.VELOCITY,
            config.RIGHT_CHANNEL
        )

    current_right=note

    player.note_on(
        current_right,
        config.VELOCITY,
        config.RIGHT_CHANNEL
    )

    interface.right_label.config(
        text=f"Right : {midi_name(note)} ({note}) | Octave : {octave}"
    )


# ----------------- Drum player -------------------


def play_drum(note):

    player.note_on(
        note,
        config.VELOCITY,
        config.DRUM_CHANNEL
    )

    time.sleep(0.02)

    player.note_off(
        note,
        config.VELOCITY,
        config.DRUM_CHANNEL
    )
    
    
# -------------------- Cleanup --------------------


def close() -> None:
    """
    Stop all active MIDI notes and close the MIDI device.
    """

    global current_left, current_right

    if current_left is not None:
        player.note_off(
            current_left,
            config.VELOCITY,
            config.LEFT_CHANNEL
        )

    if current_right is not None:
        player.note_off(
            current_right,
            config.VELOCITY,
            config.RIGHT_CHANNEL
        )

    pygame.midi.quit()