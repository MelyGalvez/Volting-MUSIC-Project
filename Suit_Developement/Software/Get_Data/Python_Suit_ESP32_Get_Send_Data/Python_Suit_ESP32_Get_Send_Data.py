import requests
from pynput import keyboard
import threading
import time

ESP32 = "http://192.168.4.1"

led_state = False


# ================= LED TOGGLE =================
def toggle_led():
    global led_state

    led_state = not led_state
    value = 1 if led_state else 0

    try:
        requests.get(
            f"{ESP32}/led?on={value}",
            timeout=2
        )
        print("\nLED =", led_state)

    except Exception as e:
        print("[LED ERROR]", e)


# ================= KEYBOARD THREAD =================
def keyboard_task():
    while True:
        keyboard.wait("space")
        print("Space detected")
        toggle_led()


threading.Thread(
    target=keyboard_task,
    daemon=True
).start()


# ================= MAIN LOOP =================
while True:

    try:
        r = requests.get(
            f"{ESP32}/data",
            timeout=5
        )

        data = r.json()

        imu_readings = data.get("imu_data", [])
        action_flag = data.get("action_flag", False)

        print("\n===============================================")
        print("          [ STATUT MULTI-IMU REÇU ]            ")

        if not imu_readings:
            print("Avertissement : imu_data vide ou manquant.")
        else:
            for i, reading in enumerate(imu_readings):

                channel = reading.get("channel", i + 1)
                heading = reading.get("heading", 0.0)
                pitch = reading.get("pitch", 0.0)
                roll = reading.get("roll", 0.0)
                piezo = reading.get("piezo", 0)

                print(
                    f"| Canal {channel:<2} "
                    f"| Heading: {heading:6.1f} "
                    f"| Pitch: {pitch:6.1f} "
                    f"| Roll: {roll:6.1f} "
                    f"| Piezo: {piezo:4d}"
                )

        print("-" * 50)
        status = "ACTIVÉ" if action_flag else "INACTIF"
        print(
            f"STATUT ACTION GLOBALE : {status} | "
            f"Timestamp: {data.get('timestamp', 'N/A')}"
        )

        time.sleep(0.2)

    except requests.exceptions.ConnectionError:
        print(f"\n[ERREUR] Impossible de joindre ESP32 ({ESP32})")
        time.sleep(1)

    except requests.exceptions.Timeout:
        print("\n[ERREUR] Timeout ESP32 (réponse trop lente)")
        time.sleep(1)

    except ValueError:
        print("\n[ERREUR] JSON invalide reçu depuis ESP32")
        time.sleep(1)

    except Exception as e:
        print(f"\n[ERREUR GÉNÉRALE] {e}")
        time.sleep(1)