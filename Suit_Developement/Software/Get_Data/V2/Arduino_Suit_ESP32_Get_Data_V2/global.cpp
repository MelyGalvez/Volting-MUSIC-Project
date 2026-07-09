#include "global.h"

// ======================================================
// GLOBAL VARIABLES
// ======================================================


// ================= HTTP Server =========================

WebServer server(80);


// ================= IMUs ================================

Adafruit_BNO055 imuSensors[NUM_IMUS] =
{
    Adafruit_BNO055(0),
    Adafruit_BNO055(1),
    Adafruit_BNO055(2),
    Adafruit_BNO055(3),
    Adafruit_BNO055(4),
    Adafruit_BNO055(5),
    Adafruit_BNO055(6),
    Adafruit_BNO055(7)
};


// ================= Sensor data =========================

SensorReading allReadings[NUM_IMUS] =
{
    {BACK_UPPER},
    {BACK_LOWER},
    {LEFT_ARM},
    {RIGHT_ARM},
    {LEFT_FOREARM},
    {RIGHT_FOREARM},
    {LEFT_HAND},
    {RIGHT_HAND}
};


// ================= Calibration =========================

CalibrationOffset imuOffsets[NUM_IMUS];


// ================= IMU status ==========================

IMUStatus imuStatus[NUM_IMUS];


// ================= System ==============================

SystemState systemState = SYSTEM_BOOT;