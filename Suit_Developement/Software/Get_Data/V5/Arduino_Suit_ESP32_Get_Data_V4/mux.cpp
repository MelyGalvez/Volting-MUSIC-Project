#include <Wire.h>

#include "mux.h"
#include "config.h"


// ================================================
// MUX.cpp
// ================================================


static uint8_t s_consecutiveFailures = 0;
static uint32_t s_recoveryCount = 0;

static uint32_t s_clockHz = I2C_CLOCK_HZ;


// --------------- Bus recovery ------------------


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

    pinMode(SDA_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(SDA_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(SCL_PIN, HIGH);
    delayMicroseconds(5);
    digitalWrite(SDA_PIN, HIGH);
    delayMicroseconds(5);

    initializeI2C();
}


// --------------- Initialization ----------------


void initializeI2C()
{
    Wire.begin(SDA_PIN, SCL_PIN, I2C_CLOCK_HZ);
    Wire.setTimeOut(I2C_TIMEOUT_MS);

    s_clockHz = I2C_CLOCK_HZ;
}


// ----------------- Bus clock -------------------


void setI2CClock(uint32_t hz)
{
    if(s_clockHz == hz)
    {
        return;
    }

    Wire.setClock(hz);

    s_clockHz = hz;
}


// -------------- Channel selection --------------


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