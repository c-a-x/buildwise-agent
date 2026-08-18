#pragma once

// Copy this file to wifi_config.h and fill in your local values before flashing.
// Do not commit wifi_config.h because it contains private network information.
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Use the computer's WLAN/LAN IPv4 address. Do not use localhost here:
// localhost means the ESP32 itself, not the computer running BuildWise.
const char* SERVER_URL = "http://YOUR_COMPUTER_IP:8000/api/v1/hardware/telemetry";
