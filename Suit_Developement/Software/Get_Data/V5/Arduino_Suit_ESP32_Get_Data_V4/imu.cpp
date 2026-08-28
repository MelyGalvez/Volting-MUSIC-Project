#include <Wire.h>
#include <Adafruit_BNO055.h>

#include "imu.h"
#include "config.h"
#include "mux.h"
#include "quat.h"


// ================================================
// IMU.cpp
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

static uint8_t s_address[NUM_IMUS] =
{
    BNO_ADDRESS_PRIMARY, BNO_ADDRESS_PRIMARY,
    BNO_ADDRESS_PRIMARY, BNO_ADDRESS_PRIMARY,
    BNO_ADDRESS_PRIMARY, BNO_ADDRESS_PRIMARY,
    BNO_ADDRESS_PRIMARY, BNO_ADDRESS_PRIMARY
};

static uint8_t s_probeMask[NUM_IMUS] = {0};

static uint8_t s_chipId[NUM_IMUS] = {0};

static uint32_t s_clock[NUM_IMUS] =
{
    I2C_CLOCK_HZ, I2C_CLOCK_HZ, I2C_CLOCK_HZ, I2C_CLOCK_HZ,
    I2C_CLOCK_HZ, I2C_CLOCK_HZ, I2C_CLOCK_HZ, I2C_CLOCK_HZ
};

static bool s_forceFallback[NUM_IMUS] = {false};

static uint16_t s_lostCount[NUM_IMUS] = {0};

static bool s_crystal[NUM_IMUS] =
{
    BNO_USE_EXTERNAL_CRYSTAL, BNO_USE_EXTERNAL_CRYSTAL,
    BNO_USE_EXTERNAL_CRYSTAL, BNO_USE_EXTERNAL_CRYSTAL,
    BNO_USE_EXTERNAL_CRYSTAL, BNO_USE_EXTERNAL_CRYSTAL,
    BNO_USE_EXTERNAL_CRYSTAL, BNO_USE_EXTERNAL_CRYSTAL
};

static bool s_altCrystal[NUM_IMUS] = {false};


// ---------------- ACK probing ------------------


static bool probeAddress(uint8_t address)
{
    Wire.beginTransmission(address);
    return Wire.endTransmission() == 0;
}


static uint8_t probeChannel(uint8_t index)
{
    uint8_t mask = 0;

    if(probeAddress(BNO_ADDRESS_PRIMARY))
    {
        mask |= IMU_PROBE_PRIMARY;
    }

    if(BNO_ADDRESS_ALTERNATE != BNO_ADDRESS_PRIMARY &&
       probeAddress(BNO_ADDRESS_ALTERNATE))
    {
        mask |= IMU_PROBE_ALTERNATE;
    }

    s_probeMask[index] = mask;

    return mask;
}


// --------------- Chip ID read ------------------


static bool readChipId(uint8_t address, uint8_t& id)
{
    Wire.beginTransmission(address);
    Wire.write((uint8_t)Adafruit_BNO055::BNO055_CHIP_ID_ADDR);

    if(Wire.endTransmission(false) != 0)
    {
        return false;
    }

    if(Wire.requestFrom(address, (uint8_t)1) != 1)
    {
        return false;
    }

    id = (uint8_t)Wire.read();

    return true;
}


// ---------------- Fusion check -----------------


static bool waitForFusion(uint8_t index, uint32_t timeoutMs)
{
    uint32_t start = millis();

    for(;;)
    {
        imu::Quaternion q = s_sensors[index].getQuat();

        Quaternion raw;
        raw.w = (float)q.w();
        raw.x = (float)q.x();
        raw.y = (float)q.y();
        raw.z = (float)q.z();

        if(quatIsValid(raw))
        {
            return true;
        }

        if(millis() - start >= timeoutMs)
        {
            return false;
        }

        delay(10);
    }
}

static bool selectClockSource(uint8_t index)
{
    for(uint8_t attempt = 0; attempt < 2; attempt++)
    {
        bool external =
            (attempt == 0) != s_altCrystal[index];

        s_sensors[index].setExtCrystalUse(external);

        if(waitForFusion(index, IMU_FUSION_TIMEOUT_MS))
        {
            s_crystal[index] = external;

            if(external != BNO_USE_EXTERNAL_CRYSTAL)
            {
                s_altCrystal[index] = true;
            }

            return true;
        }
    }

    return false;
}


// --------------- Address binding ---------------


static void bindAddress(uint8_t index, uint8_t address)
{
    if(s_address[index] == address)
    {
        return;
    }

    s_sensors[index] = Adafruit_BNO055(
        (int32_t)index,
        address,
        &Wire
    );

    s_address[index] = address;

    Serial.printf(
        "[IMU] Sensor %u bound to 0x%02X\n",
        (unsigned)index,
        (unsigned)address
    );
}


// -------------- Initialize one IMU -------------


bool initializeIMU(uint8_t index)
{
    if(index >= NUM_IMUS || !IMU_EQUIPPED[index])
    {
        return false;
    }

    s_detected[index] = false;
    s_chipId[index] = 0;

    const uint32_t candidates[2] =
    {
        s_forceFallback[index]
            ? I2C_CLOCK_FALLBACK_HZ
            : I2C_CLOCK_HZ,
        s_forceFallback[index]
            ? I2C_CLOCK_HZ
            : I2C_CLOCK_FALLBACK_HZ
    };

    const uint8_t candidateCount =
        (I2C_CLOCK_FALLBACK_HZ != I2C_CLOCK_HZ) ? 2 : 1;

    for(uint8_t c = 0; c < candidateCount; c++)
    {
        setI2CClock(candidates[c]);

        if(!selectMuxChannel(index))
        {
            continue;
        }

        uint8_t mask = probeChannel(index);

        if(mask == 0)
        {
            continue;
        }

        uint8_t address =
            (mask & IMU_PROBE_PRIMARY)
                ? BNO_ADDRESS_PRIMARY
                : BNO_ADDRESS_ALTERNATE;

        bindAddress(index, address);

        uint8_t id = 0;

        if(!readChipId(address, id))
        {
            continue;
        }

        s_chipId[index] = id;

        if(id != BNO055_ID)
        {
            continue;
        }

        if(!s_sensors[index].begin(BNO_OPERATION_MODE))
        {
            continue;
        }

        if(!selectClockSource(index))
        {
            continue;
        }

        s_clock[index] = candidates[c];
        s_detected[index] = true;

        return true;
    }

    s_clock[index] = candidates[0];

    return false;
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
        if(!IMU_EQUIPPED[i])
        {
            Serial.printf(
                "IMU %u : skipped (channel declared empty)\n",
                (unsigned)i
            );

            continue;
        }

        bool ok = false;

        for(uint8_t attempt = 0;
            attempt < IMU_INIT_ATTEMPTS && !ok;
            attempt++)
        {
            if(attempt > 0)
            {
                delay(IMU_INIT_RETRY_MS);
            }

            ok = initializeIMU(i);
        }

        if(ok)
        {
            Serial.printf(
                "IMU %u : OK (addr 0x%02X, %lu Hz, %s clock)\n",
                (unsigned)i,
                (unsigned)s_address[i],
                (unsigned long)s_clock[i],
                s_crystal[i] ? "external" : "internal"
            );
        }
        else
        {
            Serial.printf(
                "IMU %u : FAILED (answered on: %s, chip id 0x%02X, "
                "no fusion on either clock source)\n",
                (unsigned)i,
                imuProbeName(i),
                (unsigned)s_chipId[i]
            );
        }
    }

    Serial.printf(
        "IMUs : %u/%u detected\n",
        (unsigned)imuDetectedCount(),
        (unsigned)imuEquippedCount()
    );
}


// ---------------- IMU detection ----------------


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


bool imuEquipped(uint8_t index)
{
    return index < NUM_IMUS && IMU_EQUIPPED[index];
}


uint8_t imuEquippedCount()
{
    uint8_t count = 0;

    for(uint8_t i = 0; i < NUM_IMUS; i++)
    {
        if(IMU_EQUIPPED[i])
        {
            count++;
        }
    }

    return count;
}


uint8_t imuAddress(uint8_t index)
{
    if(index >= NUM_IMUS || !s_detected[index])
    {
        return 0;
    }

    return s_address[index];
}


uint8_t imuProbeMask(uint8_t index)
{
    return (index < NUM_IMUS) ? s_probeMask[index] : 0;
}


uint8_t imuChipId(uint8_t index)
{
    return (index < NUM_IMUS) ? s_chipId[index] : 0;
}


uint32_t imuClock(uint8_t index)
{
    return (index < NUM_IMUS) ? s_clock[index] : I2C_CLOCK_HZ;
}


const char* imuProbeName(uint8_t index)
{
    switch(imuProbeMask(index))
    {
        case IMU_PROBE_PRIMARY:
            return "0x28";

        case IMU_PROBE_ALTERNATE:
            return "0x29";

        case IMU_PROBE_PRIMARY | IMU_PROBE_ALTERNATE:
            return "0x28+0x29";

        default:
            return "none";
    }
}


void imuMarkLost(uint8_t index)
{
    if(index < NUM_IMUS)
    {
        s_detected[index] = false;

        if(s_lostCount[index] < 0xFFFF)
        {
            s_lostCount[index]++;
        }
    }
}


uint16_t imuLostCount(uint8_t index)
{
    return (index < NUM_IMUS) ? s_lostCount[index] : 0;
}


bool imuExternalCrystal(uint8_t index)
{
    return (index < NUM_IMUS) ? s_crystal[index] : false;
}


bool imuDowngradeClock(uint8_t index)
{
    if(index >= NUM_IMUS)
    {
        return false;
    }

    if(I2C_CLOCK_FALLBACK_HZ == I2C_CLOCK_HZ ||
       s_forceFallback[index])
    {
        return false;
    }

    s_forceFallback[index] = true;
    s_clock[index] = I2C_CLOCK_FALLBACK_HZ;

    Serial.printf(
        "[IMU] Sensor %u dropped to %lu Hz after read failures\n",
        (unsigned)index,
        (unsigned long)I2C_CLOCK_FALLBACK_HZ
    );

    return true;
}


// ----------------- IMU reading -----------------


bool readImuQuat(uint8_t index, Quaternion& out)
{
    if(index >= NUM_IMUS || !s_detected[index])
    {
        return false;
    }

    setI2CClock(s_clock[index]);

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

    if(!quatIsValid(raw))
    {
        return false;
    }

    out = quatNormalize(raw);

    return true;
}


// --------------- Vector reading ----------------


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

    readVector(
        index,
        Adafruit_BNO055::VECTOR_MAGNETOMETER,
        frame.mag
    );
}


// ----------------- Slow data -------------------


static bool readStatusRegisters(
    uint8_t address,
    uint8_t& sysStatus,
    uint8_t& selfTest,
    uint8_t& sysError
)
{
    const uint8_t reg =
        Adafruit_BNO055::BNO055_SELFTEST_RESULT_ADDR;

    Wire.beginTransmission(address);
    Wire.write(reg);

    if(Wire.endTransmission() != 0)
    {
        return false;
    }

    if(Wire.requestFrom(address, (uint8_t)5) != 5)
    {
        return false;
    }

    selfTest = (uint8_t)Wire.read();

    Wire.read();
    Wire.read();

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

    readStatusRegisters(
        s_address[index],
        frame.sysStatus,
        frame.selfTest,
        frame.sysError
    );
}