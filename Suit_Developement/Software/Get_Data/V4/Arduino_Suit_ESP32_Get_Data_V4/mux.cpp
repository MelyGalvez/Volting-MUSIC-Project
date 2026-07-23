#include <Wire.h>

#include "mux.h"
#include "config.h"


// ================================================
// MUX.cpp
//
// TCA9548A channel selection with error detection
// and I2C bus recovery. A BNO055 interrupted mid-
// transfer can hold SDA low and deadlock the bus;
// the standard fix is to clock SCL up to 9 times so
// the slave finishes its byte, then issue a STOP.
// ================================================


static uint8_t s_consecutiveFailures = 0;
static uint32_t s_recoveryCount = 0;


// ---------------- Bus recovery ------------------


void recoverI2CBus()
{
    s_recoveryCount++;

    Serial.printf(
        "[I2C] Bus recovery #%lu\n",
        (unsigned long)s_recoveryCount
    );

    Wire.end();

    pinMode(SDA_PIN, INPUT_PULLUP);
    pinMode(SCL_PIN, OUTPUT_OPEN_DRAIN);

    // Clock out any byte a slave is still driving.
    for(uint8_t i = 0; i < 9; i++)
    {
        if(digitalRead(SDA_PIN) == HIGH)
        {
            break;
        }

        digitalWrite(SCL_PIN, LOW);
        delayMicroseconds(5);
        digitalWrite(SCL_PIN, HIGH);
        delayMicroseconds(5);
    }

    // Generate a STOP condition: SDA low -> high while
    // SCL is high.
    pinMode(SDA_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(SDA_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(SCL_PIN, HIGH);
    delayMicroseconds(5);
    digitalWrite(SDA_PIN, HIGH);
    delayMicroseconds(5);

    initializeI2C();
}


// ---------------- Initialization ----------------


void initializeI2C()
{
    Wire.begin(SDA_PIN, SCL_PIN, I2C_CLOCK_HZ);
    Wire.setTimeOut(I2C_TIMEOUT_MS);
}


// --------------- Channel selection --------------


bool selectMuxChannel(uint8_t channel)
{
    if(channel >= NUM_IMUS)
    {
        return false;
    }

    Wire.beginTransmission(TCA9548A_ADDR);
    Wire.write((uint8_t)(1 << channel));

    if(Wire.endTransmission() == 0)
    {
        s_consecutiveFailures = 0;
        return true;
    }

    if(++s_consecutiveFailures >= MUX_FAILS_BEFORE_RECOVERY)
    {
        s_consecutiveFailures = 0;
        recoverI2CBus();
    }

    return false;
}
