# Firmware
The ESP32 firmware uses PlatformIO, DHT22, analog MQ-135-style sensor input, and the 256dpi MQTT client for TLS-protected QoS 1 telemetry, retained online status, Last Will offline status, reconnect backoff, and pending-message retry.

Copy `include/config.example.h` to `include/config.h`, then replace Wi-Fi, endpoint, AWS IoT root CA, certificate, and private key placeholders. The example values allow CI compilation but cannot connect to AWS. Never commit `config.h` or real device material. The firmware uses NTP to produce valid Unix timestamps; network time must be available before telemetry is sent.
