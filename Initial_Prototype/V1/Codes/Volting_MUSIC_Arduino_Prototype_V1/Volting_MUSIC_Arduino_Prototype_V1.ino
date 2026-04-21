#include <Wire.h>

// ---------- ADXL345 ----------
#define ADXL345 0x53
#define DATAX0 0x32

// ---------- Ultrason ----------
#define trigPin1 2
#define echoPin1 3
#define trigPin2 4
#define echoPin2 5

// ---------- LEDs ----------
#define BLUE_LED 8
#define GREEN_LED 9
#define RED_LED 10

void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(BLUE_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  digitalWrite(BLUE_LED, HIGH);

  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  // ---------- CHECK ADXL345 ----------
  Wire.beginTransmission(ADXL345);
  byte error = Wire.endTransmission();

  if (error != 0) {
    Serial.println("ADXL345 NOT DETECTED");
    digitalWrite(RED_LED, HIGH);
    while (1);
  }

  // ---------- INIT ADXL345 ----------
  writeReg(ADXL345, 0x2D, 0x00); // reset
  delay(10);
  writeReg(ADXL345, 0x2D, 0x08); // power on
  writeReg(ADXL345, 0x31, 0x0B); // full res + ±16g

  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BLUE_LED, LOW);
}

void loop() {
  int16_t ax, ay, az;
  readAccel(ax, ay, az);

  // DEBUG (IMPORTANT)
  Serial.print("AX:");
  Serial.println(ax);

  Serial.print("AY:");
  Serial.println(ay);

  long distance1 = measureDistance(trigPin1, echoPin1);
  long distance2 = measureDistance(trigPin2, echoPin2);

  long totalDistance = constrain(distance1 + distance2, 0, 400);

  Serial.print("Volume:");
  Serial.println(totalDistance);

  delay(10);
}

// ---------- ULTRASON ----------
long measureDistance(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  long duration = pulseIn(echo, HIGH, 30000);

  if (duration == 0) return 0; // sécurité

  long distance = (duration * 0.0343) / 2;
  return constrain(distance, 0, 200);
}

// ---------- ACCEL ----------
void readAccel(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(ADXL345);
  Wire.write(DATAX0);
  Wire.endTransmission();
  Wire.requestFrom(ADXL345, 6);

  uint8_t b[6];

  for (int i = 0; i < 6; i++) {
    if (Wire.available()) {
      b[i] = Wire.read();
    }
  }

  x = (b[1] << 8) | b[0];
  y = (b[3] << 8) | b[2];
  z = (b[5] << 8) | b[4];
}

// ---------- I2C WRITE ----------
void writeReg(byte addr, byte reg, byte val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}