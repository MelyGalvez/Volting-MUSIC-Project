import serial
import csv
import time
from datetime import datetime

# Port série
ser = serial.Serial('COM3', 115200, timeout=1)

# Nom du fichier
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
path = rf"C:\Users\melyg\OneDrive\Bureau\Volting\Volting-MUSIC-Project\Initial_Prototype\V1\Results\donnees_volting_{timestamp}.csv"

with open(path, 'w', newline='') as csvfile:

    # 🔥 Nouveau format
    fieldnames = [
        'time',
        'ACC_x', 'ACC_y', 'ACC_z',
        'GYRO_x', 'GYRO_y', 'GYRO_z',
        'MAG_x', 'MAG_y', 'MAG_z',
        'D1', 'D2',
        'BTN1', 'BTN2'
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    data = {}

    try:
        while True:
            line = ser.readline().decode('utf-8').strip()

            if not line:
                continue

            # ---------- ACC ----------
            if line.startswith('ACC:'):
                parts = line[4:].strip().split(',')
                if len(parts) == 3:
                    data['ACC_x'], data['ACC_y'], data['ACC_z'] = [p.strip() for p in parts]

            # ---------- GYRO ----------
            elif line.startswith('GYRO:'):
                parts = line[5:].strip().split(',')
                if len(parts) == 3:
                    data['GYRO_x'], data['GYRO_y'], data['GYRO_z'] = [p.strip() for p in parts]

            # ---------- MAG ----------
            elif line.startswith('MAG:'):
                parts = line[4:].strip().split(',')
                if len(parts) == 3:
                    data['MAG_x'], data['MAG_y'], data['MAG_z'] = [p.strip() for p in parts]

            # ---------- DISTANCES ----------
            elif line.startswith('D1:'):
                data['D1'] = line[3:].strip()

            elif line.startswith('D2:'):
                data['D2'] = line[3:].strip()

            # ---------- BOUTONS ----------
            elif line.startswith('BTN:'):
                parts = line[4:].strip().split(',')
                if len(parts) == 2:
                    data['BTN1'], data['BTN2'] = [p.strip() for p in parts]

            # ---------- FIN CYCLE ----------
            elif line == '---':
                data['time'] = time.time()

                if all(key in data for key in fieldnames):
                    writer.writerow(data)
                    csvfile.flush()

                data = {}

    except KeyboardInterrupt:
        print("Arrêt par utilisateur")

    finally:
        ser.close()