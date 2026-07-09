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


print("======================================")
print("      BODY MOTION MIDI")
print("======================================")
print("CH0 : Back")
print("CH1 : Back")
print("CH2 : Left arm")
print("CH3 : Right arm")
print("CH4 : Left forearm")
print("CH5 : Right forearm")
print("CH6 : Left hand")
print("CH7 : Right hand")
print("======================================")

try:

    while True:

        interface.root.update()

        r = requests.get(
            config.ESP32 + "/data",
            timeout=2
        )

        data = r.json()

        imus = {}

        for imu in data["imu_data"]:
            imus[imu["channel"]] = imu

        if len(imus) < 8:
            continue

        # =====================================================
        # OCTAVE (Back)
        # =====================================================

        back_angle = (
            imus[0]["pitch"] +
            imus[1]["pitch"]
        ) / 2

        octave = mapping.map_octave(
            back_angle
        )

        # =====================================================
        # NOTES
        # =====================================================

        left_note = mapping.map_note(
            imus[2]["pitch"]
        )

        right_note = mapping.map_note(
            imus[3]["pitch"]
        )

        left_midi = mapping.build_midi_note(
            octave,
            left_note
        )

        right_midi = mapping.build_midi_note(
            octave,
            right_note
        )

        # =====================================================
        # VOLUME
        # =====================================================

        player.set_left_volume(
            mapping.map_volume(
                imus[6]["roll"]
            )
        )

        player.set_right_volume(
            mapping.map_volume(
                imus[7]["roll"]
            )
        )

        # =====================================================
        # REVERB
        # =====================================================

        player.set_left_reverb(
            mapping.map_reverb(
                imus[4]["pitch"]
            )
        )

        player.set_right_reverb(
            mapping.map_reverb(
                imus[5]["pitch"]
            )
        )

        # =====================================================
        # PLAY NOTES
        # =====================================================

        player.play_left(
            left_midi,
            octave
        )

        player.play_right(
            right_midi,
            octave
        )

        # =====================================================
        # PIEZOS
        # =====================================================

        if mapping.detect_left_hit(
            imus[6]["piezo_left"]
        ):

            player.play_drum(
                names.DRUMS[
                    interface.left_drum_combo.get()
                ]
            )

        if mapping.detect_right_hit(
            imus[7]["piezo_right"]
        ):

            player.play_drum(
                names.DRUMS[
                    interface.right_drum_combo.get()
                ]
            )

        # =====================================================
        # CONSOLE
        # =====================================================

        print(
            f"L {midi_name(left_midi):4s}"
            f"  Oct:{octave}"
            f"  Vol:{player.current_left_volume:3d}"
            f"  Rev:{player.current_left_reverb:3d}"
            f"    |    "
            f"R {midi_name(right_midi):4s}"
            f"  Oct:{octave}"
            f"  Vol:{player.current_right_volume:3d}"
            f"  Rev:{player.current_right_reverb:3d}",
            end="\r"
        )

        time.sleep(0.05)


except tk.TclError:

    print("\nWindow closed.")

except KeyboardInterrupt:

    print("\nProgram stopped.")

finally:

    player.close()

    try:
        interface.root.destroy()

    except tk.TclError:
        pass