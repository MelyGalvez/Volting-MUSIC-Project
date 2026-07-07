import requests
import time
import tkinter as tk

import config
import mapping 
from names import midi_name
import interface
import player


# ==================================================
# MAIN
# ==================================================


# ---------------- Program start -------------------


print("====================================")
print("Dual Hand MIDI")
print("CH7 -> Instrument Left")
print("CH8 -> Instrument Right")
print("====================================")


# ------------------ Main loop ---------------------


try:

    while True:

        # ---------------- Tkinter -----------------
        
        interface.root.update()

        # ----------------- ESP32 ------------------
        
        r = requests.get(
            config.ESP32 + "/data",
            timeout=2
        )

        data = r.json()

        imuright = None
        imuleft = None

        for imu in data["imu_data"]:

            if imu["channel"] == 7:
                imuright = imu

            elif imu["channel"] == 6:
                imuleft = imu

        # --------------- Left hand ----------------

        if imuright is not None:

            octave = mapping.map_octave(
                imuright["pitch"]
            )

            note = mapping.map_note(
                imuright["roll"]
            )

            midi = mapping.build_midi_note(
                octave,
                note
            )

            player.play_left(midi, octave)

        # -------------- Right hand ----------------

        if imuleft is not None:

            octave = mapping.map_octave(
                imuleft["pitch"]
            )

            note = mapping.map_note(
                imuleft["roll"]
            )

            midi = mapping.build_midi_note(
                octave,
                note
            )

            player.play_right(midi, octave)

        # ---------------- Console -----------------

        if imuright is not None and imuleft is not None:

            print(
                f"Left : {midi_name(player.current_left):4s} ({player.current_left:2d})   "
                f"Right : {midi_name(player.current_right):4s} ({player.current_right:2d})",
                end="\r"
            )

        time.sleep(0.05)


# ------------------ Exceptions --------------------


except tk.TclError:
    print("\nWindow closed.")

except KeyboardInterrupt:
    print("\nProgram stopped.")


# ------------------- Cleanup ----------------------


finally:

    player.close()

    try:
        interface.root.destroy()
    except tk.TclError:
        pass