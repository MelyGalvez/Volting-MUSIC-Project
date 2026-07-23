#include <Wire.h>
#include <Adafruit_BNO055.h>

#include "imu.h"
#include "config.h"
#include "mux.h"
#include "quat.h"


// ================================================
// IMU.cpp
//
// BNO055 access. One quaternion read per sensor per
// scan: the Euler angles are derived from the
// quaternion downstream, which halves I2C traffic
// and sidesteps the documented unreliability of the
// BNO055 Euler output registers in some quadrants.
// The fusion vectors are read alongside the quat;
// slow diagnostics (temperature, calibration and
// status) are refreshed one sensor per scan by the
// acquisition task.
// ================================================


static Adafruit_BNO055 s_sensors[NUM_IMUS] =
{
    Adafruit_BNO055(0, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(1, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(2, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(3, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(4, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(5, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(6, BNO055_ADDRESS_A, &Wire),
    Adafruit_BNO055(7, BNO055_ADDRESS_A, &Wire)
};

static bool s_detected[NUM_IMUS] = {false};


// ----------------- ACK probing ------------------


// Fast presence test (<1 ms) before running the full
// Adafruit begin() sequence, which retries with second-
// long delays when a sensor is absent. Keeps boot fast
// and makes periodic re-init attempts nearly free.
static bool probeSensor()
{
    Wire.beginTransmission(BNO055_ADDRESS_A);
    return Wire.endTransmission() == 0;
}


// --------------- Initialize one IMU -------------


bool initializeIMU(uint8_t index)
{
    if(index >= NUM_IMUS)
    {
        return false;
    }

    s_detected[index] = false;

    if(!selectMuxChannel(index))
    {
        return false;
    }

    if(!probeSensor())
    {
        return false;
    }

    if(!s_sensors[index].begin(BNO_OPERATION_MODE))
    {
        return false;
    }

    s_sensors[index].setExtCrystalUse(
        BNO_USE_EXTERNAL_CRYSTAL
    );

    s_detected[index] = true;

    return true;
}


// --------------- Initialize IMUs ----------------


void initializeIMUs()
{
    Serial.println();
    Serial.println("=================================");
    Serial.println("Initializing IMUs");
    Serial.println("=================================");

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        bool ok = initializeIMU(i);

        Serial.printf(
            "IMU %u : %s\n",
            (unsigned)i,
            ok ? "OK" : "FAILED"
        );
    }
}


// ---------------- IMU detection -----------------


bool imuDetected(uint8_t index)
{
    return index < NUM_IMUS && s_detected[index];
}


uint8_t imuDetectedCount()
{
    uint8_t count = 0;

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(s_detected[i])
        {
            count++;
        }
    }

    return count;
}


void imuMarkLost(uint8_t index)
{
    if(index < NUM_IMUS)
    {
        s_detected[index] = false;
    }
}


// ------------------ IMU reading -----------------


bool readImuQuat(uint8_t index, Quaternion& out)
{
    if(index >= NUM_IMUS || !s_detected[index])
    {
        return false;
    }

    if(!selectMuxChannel(index))
    {
        return false;
    }

    imu::Quaternion q = s_sensors[index].getQuat();

    Quaternion raw;
    raw.w = (float)q.w();
    raw.x = (float)q.x();
    raw.y = (float)q.y();
    raw.z = (float)q.z();

    // A failed bus read yields all zeros; a corrupted one
    // yields a non-unit quaternion. Reject both so garbage
    // never propagates to clients.
    if(!quatIsValid(raw))
    {
        return false;
    }

    out = quatNormalize(raw);

    return true;
}


// ---------------- Vector reading ----------------


// Copies one fusion output vector into a Vec3.
static void readVector(
    uint8_t index,
    Adafruit_BNO055::adafruit_vector_type_t type,
    Vec3& out
)
{
    imu::Vector<3> v = s_sensors[index].getVector(type);

    out.x = (float)v.x();
    out.y = (float)v.y();
    out.z = (float)v.z();
}


void readImuVectors(uint8_t index, ImuFrame& frame)
{
    if(index >= NUM_IMUS || !s_detected[index])
    {
        return;
    }

    readVector(
        index,
        Adafruit_BNO055::VECTOR_ACCELEROMETER,
        frame.accel
    );

    readVector(
        index,
        Adafruit_BNO055::VECTOR_LINEARACCEL,
        frame.linAccel
    );

    readVector(
        index,
        Adafruit_BNO055::VECTOR_GRAVITY,
        frame.gravity
    );

    readVector(
        index,
        Adafruit_BNO055::VECTOR_GYROSCOPE,
        frame.gyro
    );

    // Zero while BNO_OPERATION_MODE is IMUPLUS (the
    // magnetometer is off); populated again if the mode
    // is ever switched to NDOF.
    readVector(
        index,
        Adafruit_BNO055::VECTOR_MAGNETOMETER,
        frame.mag
    );
}


// ------------------ Slow data -------------------


// ST_RESULT (0x36) .. SYS_ERR (0x3A) in one burst. Read
// directly because the library's getSystemStatus() ends
// with delay(200), which would stall the acquisition
// scan. This firmware never leaves register page 0, so
// no page switch is needed.
static bool readStatusRegisters(
    uint8_t& sysStatus,
    uint8_t& selfTest,
    uint8_t& sysError
)
{
    const uint8_t reg =
        Adafruit_BNO055::BNO055_SELFTEST_RESULT_ADDR;

    Wire.beginTransmission(BNO055_ADDRESS_A);
    Wire.write(reg);

    if(Wire.endTransmission() != 0)
    {
        return false;
    }

    if(Wire.requestFrom((uint8_t)BNO055_ADDRESS_A,
                        (uint8_t)5) != 5)
    {
        return false;
    }

    selfTest = (uint8_t)Wire.read();

    Wire.read();   // INT_STA (not exposed by the library)
    Wire.read();   // SYS_CLK_STATUS (idem)

    sysStatus = (uint8_t)Wire.read();
    sysError = (uint8_t)Wire.read();

    return true;
}


void readImuSlowData(uint8_t index, ImuFrame& frame)
{
    if(index >= NUM_IMUS || !s_detected[index])
    {
        return;
    }

    frame.temperature = s_sensors[index].getTemp();

    s_sensors[index].getCalibration(
        &frame.calibSys,
        &frame.calibGyro,
        &frame.calibAccel,
        &frame.calibMag
    );

    // On a failed bus read the previous values are kept.
    readStatusRegisters(
        frame.sysStatus,
        frame.selfTest,
        frame.sysError
    );
}
