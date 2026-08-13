#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

// ===== WiFi and BuildWise backend =====
const char* WIFI_SSID = "CMCC-4FCC";
const char* WIFI_PASSWORD = "sbct2522";

// Change this if your computer's WLAN IPv4 address changes.
// Do not use localhost here: localhost means the ESP32 itself.
const char* SERVER_URL = "http://192.168.1.11:8010/api/v1/hardware/telemetry";
const char* DEVICE_ID = "esp32-site-01";

// ===== Pins =====
const int DHT_PIN = 23;
const int BUZZER_PIN = 25;
const int RGB_R_PIN = 26;
const int RGB_G_PIN = 27;
const int RGB_B_PIN = 14;

// Most 4-pin RGB LED modules are common cathode. Set true for common anode.
const bool RGB_COMMON_ANODE = false;

// ===== Thresholds =====
const float TEMP_ALARM_C = 35.0;
const float HUMIDITY_ALARM_PCT = 80.0;
const unsigned long POST_INTERVAL_MS = 10000;

DHT dht(DHT_PIN, DHT11);
LiquidCrystal_I2C lcd(0x27, 16, 2);

unsigned long lastPostAt = 0;
bool lastPostOk = false;

void writeRgb(bool red, bool green, bool blue) {
  const int onLevel = RGB_COMMON_ANODE ? LOW : HIGH;
  const int offLevel = RGB_COMMON_ANODE ? HIGH : LOW;
  digitalWrite(RGB_R_PIN, red ? onLevel : offLevel);
  digitalWrite(RGB_G_PIN, green ? onLevel : offLevel);
  digitalWrite(RGB_B_PIN, blue ? onLevel : offLevel);
}

void showLine(int row, const String& text) {
  lcd.setCursor(0, row);
  String padded = text;
  while (padded.length() < 16) padded += " ";
  lcd.print(padded.substring(0, 16));
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  showLine(0, "WiFi connecting");
  showLine(1, WIFI_SSID);
  writeRgb(false, false, true);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    showLine(0, "WiFi connected");
    showLine(1, WiFi.localIP().toString());
    writeRgb(false, true, false);
  } else {
    showLine(0, "WiFi failed");
    showLine(1, "check password");
    writeRgb(true, false, true);
  }
  delay(1200);
}

String makePayload(float temperature, float humidity, bool alarm, const String& ledState) {
  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"temperature_c\":" + String(temperature, 1) + ",";
  payload += "\"humidity_pct\":" + String(humidity, 0) + ",";
  payload += "\"heat_alarm\":" + String(alarm ? "true" : "false") + ",";
  payload += "\"buzzer_on\":" + String(alarm ? "true" : "false") + ",";
  payload += "\"led_state\":\"" + ledState + "\",";
  payload += "\"ip_address\":\"" + WiFi.localIP().toString() + "\",";
  payload += "\"rssi_dbm\":" + String(WiFi.RSSI()) + ",";
  payload += "\"uptime_ms\":" + String(millis());
  payload += "}";
  return payload;
}

bool postTelemetry(float temperature, float humidity, bool alarm, const String& ledState) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  const String payload = makePayload(temperature, humidity, alarm, ledState);
  const int statusCode = http.POST(payload);
  http.end();
  return statusCode >= 200 && statusCode < 300;
}

void applyOutputs(float temperature, float humidity, bool alarm) {
  if (alarm) {
    writeRgb(true, false, false);
    digitalWrite(BUZZER_PIN, HIGH);
  } else {
    writeRgb(false, true, false);
    digitalWrite(BUZZER_PIN, LOW);
  }
}

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RGB_R_PIN, OUTPUT);
  pinMode(RGB_G_PIN, OUTPUT);
  pinMode(RGB_B_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  writeRgb(false, false, false);

  Serial.begin(115200);
  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  dht.begin();

  showLine(0, "BuildWise ESP32");
  showLine(1, "sensor node");
  delay(1000);
  connectWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  const float temperature = dht.readTemperature();
  const float humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    digitalWrite(BUZZER_PIN, LOW);
    writeRgb(true, false, true);
    showLine(0, "DHT11 read fail");
    showLine(1, "check wiring");
    delay(2000);
    return;
  }

  const bool alarm = temperature >= TEMP_ALARM_C || humidity >= HUMIDITY_ALARM_PCT;
  const String ledState = alarm ? "red_alarm" : "green_normal";
  applyOutputs(temperature, humidity, alarm);

  showLine(0, "T:" + String(temperature, 1) + "C H:" + String(humidity, 0) + "%");

  const unsigned long now = millis();
  if (now - lastPostAt >= POST_INTERVAL_MS || lastPostAt == 0) {
    lastPostAt = now;
    lastPostOk = postTelemetry(temperature, humidity, alarm, ledState);
  }

  if (alarm) {
    showLine(1, lastPostOk ? "ALARM POST OK" : "ALARM POST FAIL");
  } else {
    showLine(1, lastPostOk ? "NORMAL POST OK" : "NORMAL POSTFAIL");
  }

  Serial.print("temperature=");
  Serial.print(temperature, 1);
  Serial.print("C humidity=");
  Serial.print(humidity, 0);
  Serial.print("% post=");
  Serial.println(lastPostOk ? "ok" : "fail");

  delay(2000);
}
