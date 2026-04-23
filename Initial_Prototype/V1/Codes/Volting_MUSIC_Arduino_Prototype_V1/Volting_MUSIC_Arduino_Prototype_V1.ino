#include <Wire.h>

// ===== ADXL345 =====
#define ADXL345_ADDR 0x53

// ===== ULTRASON =====
#define trigPin1 2
#define echoPin1 3
#define trigPin2 4
#define echoPin2 5

void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  // Init ADXL345
  writeReg(ADXL345_ADDR, 0x2D, 0x08); // power
  writeReg(ADXL345_ADDR, 0x31, 0x08); // ±2g

  delay(100);
}

void loop() {
  float ax, ay, az;
  readAccel(ax, ay, az);

  // ===== ANGLES =====
  float roll  = atan2(ay, az) * 180.0 / PI;
  float pitch = atan2(-ax, sqrt(ay*ay + az*az)) * 180.0 / PI;

  // ===== NORMALISATION (optionnel) =====
  roll  = normalizeAngle(roll);
  pitch = normalizeAngle(pitch);

  // ===== ULTRASON =====
  long d1 = measureDistance(trigPin1, echoPin1);
  long d2 = measureDistance(trigPin2, echoPin2);
  long volume = constrain(d1 + d2, 0, 400);

  // ===== SERIAL =====
  Serial.print("ROLL:");
  Serial.println(roll);

  Serial.print("PITCH:");
  Serial.println(pitch);

  Serial.print("Volume:");
  Serial.println(volume);

  delay(20);
}

// ===== NORMALIZE 0–360 =====
float normalizeAngle(float a) {
  while (a < 0) a += 360;
  while (a >= 360) a -= 360;
  return a;
}

// ===== READ ACCEL =====
void readAccel(float &ax, float &ay, float &az) {
  Wire.beginTransmission(ADXL345_ADDR);
  Wire.write(0x32);
  Wire.endTransmission();
  Wire.requestFrom(ADXL345_ADDR, 6);

  int16_t x = Wire.read() | (Wire.read() << 8);
  int16_t y = Wire.read() | (Wire.read() << 8);
  int16_t z = Wire.read() | (Wire.read() << 8);

  ax = x * 0.004;
  ay = y * 0.004;
  az = z * 0.004;
}

// ===== ULTRASON =====
long measureDistance(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);

  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  long duration = pulseIn(echo, HIGH, 30000);
  long distance = (duration * 0.0343) / 2;

  return constrain(distance, 0, 200);
}

// ===== WRITE REG =====
void writeReg(byte addr, byte reg, byte val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}