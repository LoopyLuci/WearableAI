# ARP-2040 Connect — Wire Protocol Specification
## Device ↔ Mobile/Desktop Communication
*Version 1.0 — FROZEN*

---

## Framing

All TCP messages are length-prefixed:
```
[1B version_major] [1B version_minor] [1B type] [2B payload_len LE] [4B timestamp_s LE] [4B message_id LE] [N bytes payload]
```

Total header: 12 bytes. Max payload: 512 bytes.

BLE uses chunked ATT MTU (negotiated up to 512 bytes). Large payloads (models, scripts) are split into 512-byte chunks with sequence numbers.

## Version negotiation

1. Device sends `VERSION_ANNOUNCE` with its supported versions bitmask
2. Server responds with `VERSION_ACK` selecting the highest common version
3. All subsequent messages use the negotiated version

## Message types

| Type | Code | Direction | Purpose |
|---|---|---|---|
| `VOICE_EVENT` | 0x01 | Device → Server | KWS result |
| `SENSOR_SNAPSHOT` | 0x02 | Device → Server | Context state |
| `IMU_BUFFER` | 0x03 | Device → Server | IMU window |
| `AUDIO_BLOB` | 0x04 | Device → Server | Compressed audio |
| `ALERT` | 0x05 | Device → Server | Emergency alert |
| `MODEL_DELTA` | 0x06 | Device → Server | Federated delta |
| `HEARTBEAT` | 0x07 | Device → Server | Keep-alive |
| `COMMAND` | 0x81 | Server → Device | Structured intent |
| `MODEL_PUSH` | 0x82 | Server → Device | Full model OTA |
| `CONFIG_PUSH` | 0x83 | Server → Device | Config update |
| `GRAPH_PUSH` | 0x84 | Server → Device | Control graph |
| `SCRIPT_PUSH` | 0x85 | Server → Device | Bytecode script |
| `TIME_SYNC` | 0x86 | Server → Device | Timestamp correction |
| `ROLLBACK` | 0x88 | Server → Device | Rollback request |

## Security

- BLE: LE Secure Connections (ECDH key exchange, MITM protection)
- TCP/TLS: mbedTLS with device certificate signed by ATECC608A
- All signed payloads include: message type + payload + timestamp + monotonic counter
