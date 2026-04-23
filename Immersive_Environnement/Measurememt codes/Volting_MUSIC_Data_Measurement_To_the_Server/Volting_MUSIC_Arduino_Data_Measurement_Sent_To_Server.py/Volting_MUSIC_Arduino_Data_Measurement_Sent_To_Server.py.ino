#include <Wire.h>
#include <math.h>

// ---------- IMU ----------
#define ADXL345 0x53
#define DATAX0 0x32
#define ITG3200 0x68
#define HMC5883L 0x1E

// ---------- Ultrason ----------
#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5

float roll = 0;
float pitch = 0;
float yaw = 0;

unsigned long lastTime = 0;

// ---------- SAFE ACCEL ----------
bool readAccel(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(ADXL345);
  Wire.write(DATAX0);
  Wire.endTransmission();

  if (Wire.requestFrom(ADXL345, 6) != 6) return false;

  uint8_t b[6];
  for (int i = 0; i < 6; i++) b[i] = Wire.read();

  x = (b[1] << 8) | b[0];
  y = (b[3] << 8) | b[2];
  z = (b[5] << 8) | b[4];

  return true;
}

// ---------- SAFE GYRO ----------
bool readGyro(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(ITG3200);
  Wire.write(0x1D);
  Wire.endTransmission();

  if (Wire.requestFrom(ITG3200, 6) != 6) return false;

  x = Wire.read() << 8 | Wire.read();
  y = Wire.read() << 8 | Wire.read();
  z = Wire.read() << 8 | Wire.read();

  return true;
}

// ---------- SAFE MAG ----------
bool readMag(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(HMC5883L);
  Wire.write(0x03);
  Wire.endTransmission();

  if (Wire.requestFrom(HMC5883L, 6) != 6) return false;

  x = Wire.read() << 8 | Wire.read();
  z = Wire.read() << 8 | Wire.read();
  y = Wire.read() << 8 | Wire.read();

  return true;
}

// ---------- DIST ----------
long measureDistance(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  long duration = pulseIn(echo, HIGH, 30000);
  return constrain((duration * 0.0343) / 2, 0, 200);
}

// ---------- SETUP ----------
void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(TRIG1, OUTPUT);
  pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT);
  pinMode(ECHO2, INPUT);

  lastTime = millis();
}

// ---------- LOOP ----------
void loop() {

  int16_t ax, ay, az;
  int16_t gx, gy, gz;
  int16_t mx, my, mz;

  if (!readAccel(ax, ay, az)) return;
  if (!readGyro(gx, gy, gz)) return;
  if (!readMag(mx, my, mz)) return;

  long d1 = measureDistance(TRIG1, ECHO1);
  long d2 = measureDistance(TRIG2, ECHO2);

  // ---- TIME ----
  unsigned long now = millis();
  float dt = (now - lastTime) / 1000.0;
  lastTime = now;
  if (dt <= 0 || dt > 1) dt = 0.01;

  float gx_dps = gx / 14.375;
  float gy_dps = gy / 14.375;

  float rollAcc = atan2(ay, az);
  float denom = sqrt(ay * ay + az * az);
  if (denom == 0) denom = 0.0001;
  float pitchAcc = atan2(-ax, denom);

  roll  = 0.98 * (roll + gx_dps * dt * DEG_TO_RAD) + 0.02 * rollAcc;
  pitch = 0.98 * (pitch + gy_dps * dt * DEG_TO_RAD) + 0.02 * pitchAcc;

  float mx2 = mx * cos(pitch) + mz * sin(pitch);
  float my2 = mx * sin(roll) * sin(pitch)
            + my * cos(roll)
            - mz * sin(roll) * cos(pitch);

  yaw = atan2(-my2, mx2);

  float rollDeg = roll * 180.0 / PI;
  float pitchDeg = pitch * 180.0 / PI;
  float yawDeg = yaw * 180.0 / PI;
  if (yawDeg < 0) yawDeg += 360;

  // ---------- JSON ----------
  Serial.print("{");
  Serial.print("\"Roll\":"); Serial.print(rollDeg); Serial.print(",");
  Serial.print("\"Pitch\":"); Serial.print(pitchDeg); Serial.print(",");
  Serial.print("\"Yaw\":"); Serial.print(yawDeg); Serial.print(",");
  Serial.print("\"Ax\":"); Serial.print(ax); Serial.print(",");
  Serial.print("\"Ay\":"); Serial.print(ay); Serial.print(",");
  Serial.print("\"Az\":"); Serial.print(az); Serial.print(",");
  Serial.print("\"D1\":"); Serial.print(d1); Serial.print(",");
  Serial.print("\"D2\":"); Serial.print(d2);
  Serial.println("}");

  delay(100);
}