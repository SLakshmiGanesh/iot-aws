#pragma once
// Copy to config.h and replace placeholders. Never commit real credentials/certificates.
#define WIFI_SSID "your-wifi"
#define WIFI_PASSWORD "your-password"
#define DEVICE_ID "smart-home-esp32-01"
#define HOME_ID "demo-home"
#define MQTT_HOST "example-ats.iot.us-east-1.amazonaws.com"
#define MQTT_PORT 8883
#define DHT_PIN 4
#define MQ135_PIN 34
#define TELEMETRY_INTERVAL_MS 15000

// Buildable placeholders for CI only. Replace with AWS IoT root CA, device certificate,
// and matching private key before attempting a real AWS IoT connection.
#define AWS_ROOT_CA "-----BEGIN CERTIFICATE-----\nREPLACE_WITH_AWS_ROOT_CA\n-----END CERTIFICATE-----\n"
#define DEVICE_CERT "-----BEGIN CERTIFICATE-----\nREPLACE_WITH_DEVICE_CERTIFICATE\n-----END CERTIFICATE-----\n"
#define DEVICE_PRIVATE_KEY "-----BEGIN PRIVATE KEY-----\nREPLACE_WITH_DEVICE_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
