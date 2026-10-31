#pragma once
// Copy to config.h (ignored by git) and fill from your local test environment.
// Use a dedicated AWS IoT thing certificate and private key for real AWS IoT.
#define WIFI_SSID "your-wifi"
#define WIFI_PASSWORD "your-password"
#define DEVICE_ID "smart-home-esp32-01"
#define HOME_ID "demo-home"
#define MQTT_HOST "example-ats.iot.us-east-1.amazonaws.com"
#define MQTT_PORT 8883
#define DHT_PIN 4
#define MQ135_PIN 34
#define TELEMETRY_INTERVAL_MS 15000
// For deployment, provision certificate material securely; never commit private keys.
