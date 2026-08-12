# ARP-2040 Connect — HAL Specification
## Hardware Abstraction Layer Interface Contracts
*These interfaces are FROZEN. Do not modify without a 6-month deprecation cycle.*

---

## Interfaces

| Interface | File | Purpose |
|---|---|---|
| `ISensor` | `hal/ISensor.h` | All sensor drivers (IMU, mic, temp, etc.) |
| `IRadio` | `hal/IRadio.h` | Wi-Fi + BLE via NINA-W102 |
| `ICrypto` | `hal/ICrypto.h` | ATECC608A hardware crypto |
| `IStorage` | `hal/IStorage.h` | QSPI flash + LittleFS |
| `IPower` | `hal/IPower.h` | Power states, battery monitor |
| `IAudio` | `hal/IAudio.h` | PDM microphone |
| `IDisplay` | `hal/IDisplay.h` | OLED/LCD displays |
| `IActuator` | `hal/IActuator.h` | LED, vibration motor, GPIO |

## Dependency rule

No HAL implementation may depend on any agent, AI model, transport, or scripting module. The HAL is the foundation; everything else depends on it, never the reverse.
