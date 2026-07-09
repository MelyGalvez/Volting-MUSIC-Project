import requests
import time
import tkinter as tk

import config
import mapping
import interface
import player
import names
from names import midi_name


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

            player.play_left(
                midi,
                octave
            )

            # ---------- Left piezo ----------

            if mapping.detect_left_hit(
                imuright["piezo_left"]
            ):

                player.play_drum(
                    names.DRUMS[
                        interface.left_drum_combo.get()
                    ]
                )

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

            player.play_right(
                midi,
                octave
            )

            # ---------- Right piezo ----------

            if mapping.detect_right_hit(
                imuleft["piezo_right"]
            ):

                player.play_drum(
                    names.DRUMS[
                        interface.right_drum_combo.get()
                    ]
                )

        # ---------------- Console -----------------

        if imuright is not None and imuleft is not None:

            print(
                f"Left : {midi_name(player.current_left):4s} ({player.current_left:2d}) "
                f"| L Piezo : {imuright['piezo_left']:4.0f}      "
                f"Right : {midi_name(player.current_right):4s} ({player.current_right:2d}) "
                f"| R Piezo : {imuleft['piezo_right']:4.0f}",
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