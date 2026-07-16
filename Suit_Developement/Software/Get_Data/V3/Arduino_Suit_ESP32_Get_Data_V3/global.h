#pragma once

#include <WebServer.h>
#include <Adafruit_BNO055.h>

#include "config.h"
#include "types.h"


// ================================================
// GLOBAL.h
// ================================================


// ----------------- HTTP Server ------------------


extern WebServer server;


// -------------------- IMUs ----------------------


extern Adafruit_BNO055 imuSensors[NUM_IMUS];


// ----------------- Sensor data ------------------


extern SensorReading allReadings[NUM_IMUS];


// ----------------- Calibration ------------------


extern CalibrationOffset imuOffsets[NUM_IMUS];

extern Quaternion imuQuatOffsets[NUM_IMUS];


// ------------------ IMU status ------------------


extern IMUStatus imuStatus[NUM_IMUS];


// -------------------- System --------------------


extern SystemState systemState;