# Initial Prototyp - V1

This first version of the prototyp allow the user to create sounds with movements of his own body (hands and chest).

## Prerequisites


### Hardware

- 1 Arduino UNO and it's connection cable.
- 1 IMU GY-85.
- 2 Ultrasound sensors RCW-0001 (as long as you have the ‘TRIG’ and ‘ECHO’ pins, you can use any 4-pin component of your choice).
- 2 4-Pin push-button switches.
- 3 TH LEDs respectively red, yellow and green.
- 5 Security TH resistors of 220 Ohm.
- 2 1-Metre cable leads, male to 4-pin female.
- 2 1-Metre cable leads, male to 3-pin female.
- 1 Breadboard, measuring at least 10 × 10 cm (if you can print your own PCB it's better, the code is in the [Measurement_Device_PCB](https://github.com/MelyGalvez/Volting-MUSIC-Project/tree/main/Initial_Prototype/V1/PCB/Measurement_Device_PCB) file).
- 1 Soldering iron and some tin.

### Software

- Arduino IDE
- Processing-3.5.4


## PCB

Assemble / Solder your board by following the [routing](https://github.com/MelyGalvez/Volting-MUSIC-Project/tree/main/Initial_Prototype/V1/PCB).


## Run code

- Open the [Volting_MUSIC_Arduino_Prototype_V1](https://github.com/MelyGalvez/Volting-MUSIC-Project/tree/main/Initial_Prototype/V1/Codes/Volting_MUSIC_Arduino_Prototype_V1) file.
- Connect your PCB to your machine, select the right COM and board (UNO).
- Download the Arduino code via the IDE.
- You can check the serial monitor to see data sent at the right rate. Do not forget to close this monitor before the next steps. If you don't it will block the COM port.
- Open the [Volting_MUSIC_Processing_Prototype_V1](https://github.com/MelyGalvez/Volting-MUSIC-Project/tree/main/Initial_Prototype/V1/Codes/Volting_MUSIC_Processing_Prototype_V1) file.
- Run the code and enjoy.


## Conclusion

This first version of the prototype works, but is not particularly effective, as the GY-85 IMU is an imprecise sensor. It is therefore difficult to choose the right location for mapping.