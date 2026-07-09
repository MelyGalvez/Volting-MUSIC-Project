#include "globals.h"


// ================================================
// GLOBALS.cpp
// ================================================


// ----------- Global object instances ------------


WebServer server(80);

Adafruit_BNO055 imuSensors[NUM_IMUS] =
{
    Adafruit_BNO055(),
    Adafruit_BNO055(),
    Adafruit_BNO055(),
    Adafruit_BNO055(),
    Adafruit_BNO055(),
    Adafruit_BNO055(),
    Adafruit_BNO055(),
    Adafruit_BNO055()
};


// -------------- Global sensor data --------------


SensorReading allReadings[NUM_IMUS];


// ---------- Global system states data -----------


bool actionTriggered = false;