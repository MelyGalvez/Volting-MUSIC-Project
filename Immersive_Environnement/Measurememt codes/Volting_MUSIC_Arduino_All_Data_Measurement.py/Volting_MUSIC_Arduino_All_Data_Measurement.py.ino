#include <Wire.h>

// ---------- ADXL345 ----------
#define ADXL345 0x53
#define DATAX0 0x32

// ---------- ITG3200 ----------
#define ITG3200 0x68

// ---------- HMC5883L ----------
#define HMC5883L 0x1E

// ---------- Ultrason ----------
#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5

// ---------- Boutons ----------
#define BTN1 6
#define BTN2 7

// ---------- LEDs ----------
#define BLUE_LED 8
#define GREEN_LED 9
#define RED_LED 10

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // LEDs
  pinMode(BLUE_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  digitalWrite(BLUE_LED, HIGH); // init

  // Ultrason
  pinMode(TRIG1, OUTPUT);
  pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT);
  pinMode(ECHO2, INPUT);

  // Boutons (pull-down externe)
  pinMode(BTN1, INPUT);
  pinMode(BTN2, INPUT);

  // Init ADXL345
  writeReg(ADXL345, 0x2D, 0x08);
  writeReg(ADXL345, 0x31, 0x08);

  // Init HMC5883L
  writeReg(HMC5883L, 0x00, 0x70);
  writeReg(HMC5883L, 0x01, 0x20);
  writeReg(HMC5883L, 0x02, 0x00);

  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BLUE_LED, LOW);
}

// ---------- LOOP ----------
void loop() {

  // ---------- IMU ----------
  int16_t ax, ay, az;
  readAccel(ax, ay, az);

  int16_t gx, gy, gz;
  readGyro(gx, gy, gz);

  int16_t mx, my, mz;
  readMag(mx, my, mz);

  // ---------- ULTRASON ----------
  long d1 = measureDistance(TRIG1, ECHO1);
  long d2 = measureDistance(TRIG2, ECHO2);

  // ---------- BOUTONS ----------
  bool b1 = digitalRead(BTN1);
  bool b2 = digitalRead(BTN2);

  // ---------- LEDs ----------
  digitalWrite(BLUE_LED, b1);
  digitalWrite(GREEN_LED, b2);
  digitalWrite(RED_LED, b1 && b2);

  // ---------- SERIAL OUTPUT ----------
  Serial.print("ACC: ");
  Serial.print(ax); Serial.print(", ");
  Serial.print(ay); Serial.print(", ");
  Serial.println(az);

  Serial.print("GYRO: ");
  Serial.print(gx); Serial.print(", ");
  Serial.print(gy); Serial.print(", ");
  Serial.println(gz);

  Serial.print("MAG: ");
  Serial.print(mx); Serial.print(", ");
  Serial.print(my); Serial.print(", ");
  Serial.println(mz);

  Serial.print("D1: "); Serial.println(d1);
  Serial.print("D2: "); Serial.println(d2);

  Serial.print("BTN: ");
  Serial.print(b1); Serial.print(", ");
  Serial.println(b2);

  Serial.println("---");

  delay(100);
}

// ---------- ULTRASON ----------
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

// ---------- ACCEL ----------
void readAccel(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(ADXL345);
  Wire.write(DATAX0);
  Wire.endTransmission();
  Wire.requestFrom(ADXL345, 6);

  uint8_t b[6];
  for (int i = 0; i < 6; i++) b[i] = Wire.read();

  x = (b[1] << 8) | b[0];
  y = (b[3] << 8) | b[2];
  z = (b[5] << 8) | b[4];
}

// ---------- GYRO ----------
void readGyro(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(ITG3200);
  Wire.write(0x1D);
  Wire.endTransmission();
  Wire.requestFrom(ITG3200, 6);

  x = Wire.read() << 8 | Wire.read();
  y = Wire.read() << 8 | Wire.read();
  z = Wire.read() << 8 | Wire.read();
}

// ---------- MAG ----------
void readMag(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(HMC5883L);
  Wire.write(0x03);
  Wire.endTransmission();
  Wire.requestFrom(HMC5883L, 6);

  x = Wire.read() << 8 | Wire.read();
  z = Wire.read() << 8 | Wire.read();
  y = Wire.read() << 8 | Wire.read();
}

// ---------- I2C WRITE ----------
void writeReg(byte addr, byte reg, byte val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}