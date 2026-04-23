import serial
import json
import csv
import time
from datetime import datetime

# ---------- SERIAL ----------
ser = serial.Serial('COM4', 115200, timeout=1)
ser.reset_input_buffer()

# ---------- FILE ----------
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

path = rf"C:\Users\Administrator\Desktop\Volting-MUSIC-Project\Immersive_Environnement\Measurememt codes\Volting_MUSIC_Data_Measurement_To_the_Server\Measuremets results\Position_Measurement_{timestamp}.csv"

# ---------- CSV ----------
fieldnames = [
    'time',
    'Roll', 'Pitch', 'Yaw',
    'Ax', 'Ay', 'Az',
    'D1', 'D2'
]

with open(path, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    print("Capturing 10 samples...")

    count = 0
    max_samples = 10
    start_time = None
    timeout = time.time() + 5

    while count < max_samples and time.time() < timeout:

        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue

        try:
            start = line.find("{")
            end = line.rfind("}")
            if start == -1 or end == -1:
                continue

            data = json.loads(line[start:end+1])

            if start_time is None:
                start_time = time.time()

            row = {
                'time': time.time() - start_time,

                'Roll': data.get("Roll", 0),
                'Pitch': data.get("Pitch", 0),
                'Yaw': data.get("Yaw", 0),

                'Ax': data.get("Ax", 0),
                'Ay': data.get("Ay", 0),
                'Az': data.get("Az", 0),

                'D1': data.get("D1", 0),
                'D2': data.get("D2", 0),
            }

            writer.writerow(row)
            count += 1

        except:
            continue

ser.close()

print("Done. Samples:", count)