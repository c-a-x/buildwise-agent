# ESP32 DevKit hardware wiring

This wiring matches the board labels visible in the user's photo.

Visible pins:

- Left side: `3V3`, `GND`, `D15`, `D2`, `D4`, `RX2`, `TX2`, `D5`, `D18`, `D19`, `D21`, `RX0`, `TX0`, `D22`, `D23`
- Right side: `VIN`, `GND`, `D13`, `D12`, `D14`, `D27`, `D26`, `D25`, `D33`, `D32`, `D35`, `D34`, `VN`, `VP`, `EN`

The sketch avoids boot-sensitive pins `D2`, `D4`, `D12`, and `D15`.

| Module | Module pin | ESP32 board label | ESP32 GPIO |
|---|---|---:|---:|
| DHT11 | VCC / + | 3V3 | 3.3V |
| DHT11 | GND / - | GND | GND |
| DHT11 | DATA / OUT / S | D23 | GPIO23 |
| LCD1602 I2C | VCC | 3V3 | 3.3V |
| LCD1602 I2C | GND | GND | GND |
| LCD1602 I2C | SDA | D21 | GPIO21 |
| LCD1602 I2C | SCL | D22 | GPIO22 |
| Active buzzer | VCC | 3V3 or VIN | 3.3V or 5V |
| Active buzzer | GND | GND | GND |
| Active buzzer | SIG / S | D25 | GPIO25 |
| RGB LED | R | D26 | GPIO26 |
| RGB LED | G | D27 | GPIO27 |
| RGB LED | B | D14 | GPIO14 |
| RGB LED | GND / - | GND | GND |

If the RGB module has a common `VCC` or `+` pin instead of `GND` or `-`, connect the common pin to `3V3` and change:

```cpp
const bool RGB_COMMON_ANODE = false;
```

to:

```cpp
const bool RGB_COMMON_ANODE = true;
```

The ESP32 pins are not 5V tolerant. Power the LCD I2C module from `3V3` first. If the LCD is too dim, adjust the contrast potentiometer on the back of the LCD backpack before considering 5V power.
