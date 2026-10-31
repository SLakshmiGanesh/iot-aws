#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <MQTT.h>
#include <DHT.h>
#include <time.h>

#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

#ifndef DHT_TYPE
#define DHT_TYPE DHT22
#endif

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClientSecure tls;
MQTTClient mqtt(512);
unsigned long lastPublish = 0;
unsigned long retryAt = 0;
uint32_t backoffMs = 1000;
bool clockConfigured = false;
bool pendingTelemetry = false;
char pendingPayload[256];

String baseTopic() {
  return String("home/") + HOME_ID + "/devices/" + DEVICE_ID;
}

bool synchronizeClock() {
  if (!clockConfigured) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    clockConfigured = true;
  }
  const unsigned long started = millis();
  while (time(nullptr) < 1700000000 && millis() - started < 10000) {
    delay(250);
  }
  return time(nullptr) >= 1700000000;
}

bool connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.println("Connecting to configured Wi-Fi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) delay(250);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi connection timed out");
    return false;
  }
  Serial.println("Wi-Fi connected");
  return synchronizeClock();
}

void scheduleRetry() {
  retryAt = millis() + backoffMs;
  backoffMs = min(backoffMs * 2, 60000UL);
}

void connectMqtt() {
  if (mqtt.connected() || millis() < retryAt) return;
  if (!connectWifi()) {
    scheduleRetry();
    return;
  }

  const String statusTopic = baseTopic() + "/status";
  const char willPayload[] = "{\"device_id\":\"" DEVICE_ID "\",\"status\":\"offline\"}";
  mqtt.setWill(statusTopic.c_str(), willPayload, true, 1);
  if (mqtt.connect(DEVICE_ID)) {
    mqtt.publish(statusTopic.c_str(), "{\"status\":\"online\"}", true, 1);
    backoffMs = 1000;
    Serial.println("MQTT connected with TLS");
  } else {
    Serial.printf("MQTT connect failed (error %d)\n", static_cast<int>(mqtt.lastError()));
    scheduleRetry();
  }
}

bool publishPending() {
  if (!pendingTelemetry || !mqtt.connected()) return false;
  const String topic = baseTopic() + "/telemetry";
  const bool sent = mqtt.publish(topic.c_str(), pendingPayload,
                                 static_cast<int>(strlen(pendingPayload)), false, 1);
  if (sent) {
    pendingTelemetry = false;
    Serial.println("QoS 1 telemetry acknowledged");
    return true;
  }
  Serial.println("QoS 1 publish failed; retaining message for retry");
  return false;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  tls.setCACert(AWS_ROOT_CA);
  tls.setCertificate(DEVICE_CERT);
  tls.setPrivateKey(DEVICE_PRIVATE_KEY);
  mqtt.begin(MQTT_HOST, MQTT_PORT, tls);
  mqtt.setOptions(30, true, 2000);
  mqtt.setTimeout(3000);
  connectWifi();
}

void loop() {
  connectMqtt();
  mqtt.loop();
  publishPending();

  if (mqtt.connected() && !pendingTelemetry &&
      millis() - lastPublish >= TELEMETRY_INTERVAL_MS) {
    lastPublish = millis();
    const float temperature = dht.readTemperature();
    const float humidity = dht.readHumidity();
    const int airQuality = analogRead(MQ135_PIN);
    if (isnan(temperature) || isnan(humidity) ||
        temperature < -40 || temperature > 85 || humidity < 0 || humidity > 100) {
      Serial.println("Invalid sensor reading; telemetry skipped");
      delay(20);
      return;
    }

    const time_t now = time(nullptr);
    snprintf(pendingPayload, sizeof(pendingPayload),
             "{\"device_id\":\"%s\",\"timestamp\":\"%lu\","
             "\"temperature\":%.1f,\"humidity\":%.1f,"
             "\"air_quality\":%d,\"status\":\"online\"}",
             DEVICE_ID, static_cast<unsigned long>(now),
             temperature, humidity, airQuality);
    pendingTelemetry = true;
    publishPending();
  }
  delay(20);
}
