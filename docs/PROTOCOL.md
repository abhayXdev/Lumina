# Communication Protocol

The system utilizes a single persistent WebSocket connection per device. The protocol uses **Binary frames** for audio data and **Text frames (JSON)** for control messages.

## 1. Connection & Authentication
**Endpoint:** `wss://<backend-url>/ws/<device_id>?api_key=<your_api_key>`
- The ESP32 connects to the endpoint.
- Authentication is handled via the `api_key` query parameter. If invalid, the server drops the connection with `WS_1008_POLICY_VIOLATION`.

## 2. Heartbeat Process
ESP32 must send a heartbeat every 30 seconds to keep the connection alive.
**Direction:** ESP32 -> Server
```json
{
  "type": "heartbeat",
  "device_id": "esp32_001"
}
```

## 3. Audio Streaming Process
Audio is streamed continuously as raw bytes.
**Direction:** ESP32 -> Server
**Format:** Binary Frame (1024 bytes)
**Payload:** Raw 16-bit PCM audio, 16kHz, Mono.

## 4. Command Process
When the backend detects the wake word, it issues a command.
**Direction:** Server -> ESP32
```json
{
  "type": "command",
  "command": "led_on" 
  // or "led_off"
}
```

## 5. Status Reporting Process
ESP32 reports its status (e.g., after acting on a command or upon booting).
**Direction:** ESP32 -> Server
```json
{
  "type": "status",
  "device_id": "esp32_001",
  "status": "led_turned_on"
}
```

## Reconnection Strategy
If the WebSocket disconnects, the ESP32 will attempt to reconnect using an exponential backoff strategy (1s, 2s, 4s, 8s, capped at 10s).
