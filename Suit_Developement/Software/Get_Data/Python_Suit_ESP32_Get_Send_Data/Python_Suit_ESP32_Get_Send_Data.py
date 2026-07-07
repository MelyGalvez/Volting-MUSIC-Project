import requests
from pynput import keyboard
import threading
import time

ESP32 = "http://192.168.4.1"

led_state = False

# Empêche deux requêtes HTTP en même temps
http_lock = threading.Lock()


# ================= LED TOGGLE =================
def toggle_led():
    global led_state

    led_state = not led_state
    value = 1 if led_state else 0

    try:
        with http_lock:
            r = requests.get(
                f"{ESP32}/led?on={value}",
                timeout=2
            )

        print(f"LED = {led_state} | HTTP {r.status_code}")

    except Exception as e:
        print("[LED ERROR]", e)


# ================= KEYBOARD =================
def on_press(key):
    try:
        if key == keyboard.Key.space:
            print("Space detected")
            toggle_led()
    except Exception as e:
        print(e)


listener = keyboard.Listener(on_press=on_press)
listener.daemon = True
listener.start()


# ================= MAIN LOOP =================
while True:

    try:
        with http_lock:
            r = requests.get(
                f"{ESP32}/data",
                timeout=5
            )

        data = r.json()

        imu_readings = data.get("imu_data", [])
        action_flag = data.get("action_flag", False)

        print("\n===============================================")
        print("          [ STATUT MULTI-IMU RX ]")

        for reading in imu_readings:
            print(
                f"CH {reading['channel']} | "
                f"H={reading['heading']:.1f} "
                f"P={reading['pitch']:.1f} "
                f"R={reading['roll']:.1f} "
                f"Piezo={reading['piezo']}"
            )

        print("-----------------------------------------------")
        print("Action TX:", action_flag)

        time.sleep(0.2)

    except Exception as e:
        print(e)
        time.sleep(1)