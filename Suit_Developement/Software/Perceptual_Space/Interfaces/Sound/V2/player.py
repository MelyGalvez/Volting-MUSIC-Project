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

current_left_volume = -1
current_right_volume = -1

current_left_reverb = -1
current_right_reverb = -1


# ----------------- Instruments -------------------


LEFT_INSTRUMENT = 0
RIGHT_INSTRUMENT = 40

player.set_instrument(
    LEFT_INSTRUMENT,
    config.LEFT_CHANNEL
)

player.set_instrument(
    RIGHT_INSTRUMENT,
    config.RIGHT_CHANNEL
)


# ------------------- Callbacks -------------------


def change_left_instrument(event):

    player.set_instrument(
        interface.INSTRUMENTS[
            interface.left_combo.get()
        ],
        config.LEFT_CHANNEL
    )


def change_right_instrument(event):

    player.set_instrument(
        interface.INSTRUMENTS[
            interface.right_combo.get()
        ],
        config.RIGHT_CHANNEL
    )


interface.left_combo.bind(
    "<<ComboboxSelected>>",
    change_left_instrument
)

interface.right_combo.bind(
    "<<ComboboxSelected>>",
    change_right_instrument
)


# ---------------- Interface update ---------------


def update_left_display(note, octave):

    interface.left_label.config(
        text=
        f"Note     : {midi_name(note)}\n"
        f"Octave   : {octave}\n"
        f"Volume   : {current_left_volume}\n"
        f"Reverb   : {current_left_reverb}"
    )


def update_right_display(note, octave):

    interface.right_label.config(
        text=
        f"Note     : {midi_name(note)}\n"
        f"Octave   : {octave}\n"
        f"Volume   : {current_right_volume}\n"
        f"Reverb   : {current_right_reverb}"
    )


# ---------------- Left player --------------------


def play_left(note, octave):

    global current_left

    if note != current_left:

        if current_left is not None:

            player.note_off(
                current_left,
                config.VELOCITY,
                config.LEFT_CHANNEL
            )

        current_left = note

        player.note_on(
            current_left,
            config.VELOCITY,
            config.LEFT_CHANNEL
        )

    update_left_display(
        note,
        octave
    )


# ---------------- Right player -------------------


def play_right(note, octave):

    global current_right

    if note != current_right:

        if current_right is not None:

            player.note_off(
                current_right,
                config.VELOCITY,
                config.RIGHT_CHANNEL
            )

        current_right = note

        player.note_on(
            current_right,
            config.VELOCITY,
            config.RIGHT_CHANNEL
        )

    update_right_display(
        note,
        octave
    )


# ---------------- Volume -------------------------


def set_left_volume(value):

    global current_left_volume

    value = max(0, min(127, value))

    if value == current_left_volume:
        return

    current_left_volume = value

    player.write_short(
        0xB0 + config.LEFT_CHANNEL,
        config.CC_VOLUME,
        value
    )

    if current_left is not None:
        update_left_display(
            current_left,
            current_left // 12
        )


def set_right_volume(value):

    global current_right_volume

    value = max(0, min(127, value))

    if value == current_right_volume:
        return

    current_right_volume = value

    player.write_short(
        0xB0 + config.RIGHT_CHANNEL,
        config.CC_VOLUME,
        value
    )

    if current_right is not None:
        update_right_display(
            current_right,
            current_right // 12
        )


# ---------------- Reverb -------------------------


def set_left_reverb(value):

    global current_left_reverb

    value = max(0, min(127, value))

    if value == current_left_reverb:
        return

    current_left_reverb = value

    player.write_short(
        0xB0 + config.LEFT_CHANNEL,
        config.CC_REVERB,
        value
    )

    if current_left is not None:
        update_left_display(
            current_left,
            current_left // 12
        )


def set_right_reverb(value):

    global current_right_reverb

    value = max(0, min(127, value))

    if value == current_right_reverb:
        return

    current_right_reverb = value

    player.write_short(
        0xB0 + config.RIGHT_CHANNEL,
        config.CC_REVERB,
        value
    )

    if current_right is not None:
        update_right_display(
            current_right,
            current_right // 12
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


def close():

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