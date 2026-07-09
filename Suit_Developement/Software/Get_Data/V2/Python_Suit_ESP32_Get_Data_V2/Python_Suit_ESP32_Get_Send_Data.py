import time

import config
from communication import get_sensor_data
from display import display_sensor_data


print("==========================")
print("ESP32 MUSIC SUIT CLIENT")
print("==========================")


try:

    while True:

        data = get_sensor_data()

        display_sensor_data(data)

        time.sleep(config.UPDATE_PERIOD)

except KeyboardInterrupt:

    print("\nProgram stopped.")