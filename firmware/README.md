# Firmware
Configure private `config.h` and a securely provisioned certificate header containing `AWS_ROOT_CA`, `DEVICE_CERT`, and `DEVICE_PRIVATE_KEY`. The example header intentionally contains no credentials. PlatformIO compilation requires a local toolchain; Wokwi requires its own project configuration. Never use an insecure TLS mode.
