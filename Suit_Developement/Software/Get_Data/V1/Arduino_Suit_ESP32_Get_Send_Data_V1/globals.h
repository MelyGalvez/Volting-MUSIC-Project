#pragma once

#include <WebServer.h>
#include <Adafruit_BNO055.h>

#include "config.h"
#include "types.h"


// ================================================
// GLOBALS.h
// ================================================


// --------------------- Object -------------------


extern WebServer server;

extern Adafruit_BNO055 imuSensors[NUM_IMUS];


// ---------------------- Data --------------------


extern SensorReading allReadings[NUM_IMUS];

extern bool actionTriggered;