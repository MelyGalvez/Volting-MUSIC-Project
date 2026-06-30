#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

// ================= CONFIG =================
#define SDA_PIN 21
#define SCL_PIN 22
#define TCA9548A_ADDR 0x70
#define PIEZO_PIN 34
#define LED_PIN 18
#define NUM_IMUS 8

const char* ssid = "ESP32_Test";
const char* password = "12345678";

WebServer server(80);

// ================= STRUCT =================
struct SensorReading {
    int channel;
    float heading_x;
    float pitch_y;
    float roll_z;
    int piezo_value;
};

SensorReading allReadings[NUM_IMUS];
bool actionTriggered = false;

// IMUs
Adafruit_BNO055 imuSensors[NUM_IMUS] = {
    Adafruit_BNO055(), Adafruit_BNO055(),
    Adafruit_BNO055(), Adafruit_BNO055(),
    Adafruit_BNO055(), Adafruit_BNO055(),
    Adafruit_BNO055(), Adafruit_BNO055()
};

// ================= MUX =================
void tcaSelect(uint8_t channel)
{
    Wire.beginTransmission(TCA9548A_ADDR);
    Wire.write(1 << (channel - 1));
    Wire.endTransmission();
}

// ================= SAFE READ IMU =================
bool readIMU(int i, float &h, float &p, float &r)
{
    imu::Vector<3> euler = imuSensors[i].getVector(Adafruit_BNO055::VECTOR_EULER);

    h = euler.x();
    p = euler.y();
    r = euler.z();

    return true;
}

// ================= CAPTURE =================
void captureAllIMUData()
{
    Serial.println("\n[CAPTURE] START");

    for (int i = 0; i < NUM_IMUS; i++)
    {
        uint8_t channel = i + 1;

        Serial.print("Channel ");
        Serial.print(channel);
        Serial.print(" select... ");

        tcaSelect(channel);
        delay(3);

        float h = 0, p = 0, r = 0;

        bool ok = readIMU(i, h, p, r);

        if (!ok)
        {
            Serial.println("FAIL");
            continue;
        }

        allReadings[i].channel = channel;
        allReadings[i].heading_x = h;
        allReadings[i].pitch_y = p;
        allReadings[i].roll_z = r;

        Serial.print("OK H=");
        Serial.print(h);
        Serial.print(" P=");
        Serial.print(p);
        Serial.print(" R=");
        Serial.println(r);
    }

    int piezo = analogRead(PIEZO_PIN);

    for (int i = 0; i < NUM_IMUS; i++)
        allReadings[i].piezo_value = piezo;

    Serial.println("[CAPTURE] END\n");
}

// ================= HTTP DATA =================
void handleData()
{
    Serial.println("\n[HTTP] /data request");

    unsigned long t0 = millis();

    captureAllIMUData();

    unsigned long t1 = millis();

    Serial.print("Capture time ms: ");
    Serial.println(t1 - t0);

    String json = "{";
    json += "\"timestamp\":" + String(millis()) + ",";
    json += "\"imu_data\":[";

    for (int i = 0; i < NUM_IMUS; i++)
    {
        auto &r = allReadings[i];

        json += "{";
        json += "\"channel\":" + String(r.channel) + ",";
        json += "\"heading\":" + String(r.heading_x, 2) + ",";
        json += "\"pitch\":" + String(r.pitch_y, 2) + ",";
        json += "\"roll\":" + String(r.roll_z, 2) + ",";
        json += "\"piezo\":" + String(r.piezo_value);
        json += "}";

        if (i < NUM_IMUS - 1)
            json += ",";
    }

    json += "],";
    json += "\"action_flag\":";
    json += actionTriggered ? "true" : "false";
    json += "}";

    Serial.print("JSON size: ");
    Serial.println(json.length());

    server.send(200, "application/json", json);

    Serial.println("[HTTP] RESPONSE SENT");
}

// ================= LED =================
void handleLed()
{
  if (server.hasArg("on"))
  {
    if (server.arg("on") == "1")
    {
      digitalWrite(LED_PIN, HIGH);
      actionTriggered = true;
    }
    else
    {
      digitalWrite(LED_PIN, LOW);
      actionTriggered = false;
    }
  }
  server.send(200, "text/plain", "OK");
}

// ================= SETUP =================
void setup()
{
    Serial.begin(115200);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    Wire.begin(SDA_PIN, SCL_PIN);

    Serial.println("\n=== INIT IMUS ===");

    for (int i = 0; i < NUM_IMUS; i++)
    {
        uint8_t channel = i + 1;

        tcaSelect(channel);
        delay(10);

        Serial.print("Init channel ");
        Serial.print(channel);
        Serial.print(" ... ");

        if (!imuSensors[i].begin())
        {
            Serial.println("FAILED");
        }
        else
        {
            imuSensors[i].setExtCrystalUse(true);
            Serial.println("OK");
        }
    }

    WiFi.softAP(ssid, password);

    Serial.print("AP IP: ");
    Serial.println(WiFi.softAPIP());

    server.on("/data", HTTP_GET, handleData);
    server.on("/led", HTTP_GET, handleLed);

    server.begin();

    Serial.println("Server started");
}

// ================= LOOP =================
void loop()
{
    server.handleClient();
    delay(5);
}