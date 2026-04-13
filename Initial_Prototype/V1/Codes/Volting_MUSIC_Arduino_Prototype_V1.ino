// --- Required libraries for the BNO055 sensor ---
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

// Create BNO055 object with ID 55
Adafruit_BNO055 bno = Adafruit_BNO055(55);

// --- Define LED pins ---
const int BLUE_LED = 10;
const int GREEN_LED = 11;
const int RED_LED = 12;

// --- Define pins for ultrasonic sensor #1 ---
const int trigPin1 = 6;
const int echoPin1 = 7;

// --- Define pins for ultrasonic sensor #2 ---
const int trigPin2 = 9;
const int echoPin2 = 8;

void setup(void) {
  Serial.begin(115200); // Initialize serial communication at 115200 baud

  // Configure LED pins as outputs
  pinMode(BLUE_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  // Initial state: blue LED ON to indicate initialization
  digitalWrite(BLUE_LED, HIGH);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  // Configure ultrasonic sensor pins
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  // Initialize BNO055 orientation sensor
  if (!bno.begin()) {
    // If sensor is not detected, display error and turn on red LED
    Serial.println("Error: BNO055 sensor not detected.");
    digitalWrite(RED_LED, HIGH);    // error signal
    digitalWrite(BLUE_LED, LOW);
    while (1); // Stop program here
  }

  delay(10);
  bno.setExtCrystalUse(true); // Use external crystal for better accuracy

  // Successful initialization: green LED ON (ready), blue OFF
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BLUE_LED, LOW);
}

void loop(void) {
  // --- Read orientation data from BNO055 ---
  sensors_event_t event;
  bno.getEvent(&event);

  float currentX = event.orientation.x; // Rotation angle around X axis
  float currentZ = event.orientation.z; // Rotation angle around Z axis

  // Print orientation values to serial monitor
  Serial.print("X:");
  Serial.println(currentX);

  Serial.print("Z:");
  Serial.println(currentZ);

  // --- Measure distance with ultrasonic sensor 1 ---
  long distance1 = measureDistance(trigPin1, echoPin1);

  // --- Measure distance with ultrasonic sensor 2 ---
  long distance2 = measureDistance(trigPin2, echoPin2);

  // --- Compute total measured distance ---
  long totalDistance = distance1 + distance2;
  totalDistance = constrain(totalDistance, 0, 400); // Limit to 400 cm (200 cm max per sensor)

  // Print total distance as a "volume" estimation
  Serial.print("Volume:");
  Serial.println(totalDistance);

  delay(10); // Small delay to avoid saturating the serial port
}

// --- Utility function to measure distance with an ultrasonic sensor ---
long measureDistance(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(1);
  digitalWrite(trig, HIGH); // Send a 1 µs pulse
  delayMicroseconds(1);
  digitalWrite(trig, LOW);

  // Measure the time it takes for the echo to return
  long duration = pulseIn(echo, HIGH);

  // Convert to distance (in cm)
  long distance = (duration / 2) / 29.1;

  // Limit distance to 200 cm to avoid abnormal values
  return constrain(distance, 0, 200);
}