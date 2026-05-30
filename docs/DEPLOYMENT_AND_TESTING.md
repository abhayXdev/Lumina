# Deployment, Security & Testing Guide

## Render Deployment
The backend is configured for deployment on Render using the `render.yaml` Blueprint.

### Prerequisites
1. A Render.com account.
2. The code pushed to a GitHub/GitLab repository.

### Steps
1. In Render, create a new "Blueprint Instance".
2. Connect your repository.
3. Render will parse the `render.yaml` file.
4. It will automatically:
   - Install Python 3.12.
   - Run `pip install -r requirements.txt`.
   - Download the openWakeWord models via the build command.
   - Start Uvicorn bound to `$PORT`.
5. Once deployed, note your Render URL (e.g., `https://jarvis-iot.onrender.com`).
6. Update the `WEBSOCKET_URL` in the ESP32 `main.c` with this URL (using `wss://`).

### Scaling & Limitations
- **WebSockets:** Render supports WebSockets on all tiers. However, free tiers spin down after 15 minutes of inactivity. For a persistent IoT device, you must use a paid tier (Starter or above).
- **Latency:** openWakeWord takes < 50ms to infer on a standard CPU. Network latency (ESP32 -> Render -> ESP32) will be the primary source of delay (approx 100-300ms depending on location).

## Security Implementation
1. **API Key Authentication:** Devices must provide an `api_key` in the WebSocket connection URI. In production, change the default key using Render Environment Variables.
2. **Secure WebSockets (WSS):** Render automatically provisions TLS certificates. The ESP32 must connect via `wss://`.
3. **Environment Variables:** Secrets (like `API_KEY`) are kept out of source code and injected via the cloud environment.
4. **Input Validation:** The backend uses Pydantic models to strictly validate incoming JSON payloads. Invalid JSON or incorrect schemas will not crash the server.

## Testing Strategy

### 1. Unit Testing
- **Wake Word Logic:** Write tests passing pre-recorded `16-bit PCM` audio of the word "Jarvis" to `WakeWordDetector.process_audio()` and assert it returns `True`.
- **Device Management:** Test `register_device`, `unregister_device`, and `toggle_led_state` to ensure internal state maps are updated correctly.

### 2. Integration Testing
- Use a Python WebSocket client (e.g., `websockets` library) to mock the ESP32.
- Send a valid authentication request, stream a chunk of dummy audio data, and send a JSON heartbeat.
- Verify the server does not drop the connection and appropriately registers the mocked device.

### 3. Hardware Testing
1. **Flash Firmware:** Flash the ESP32 via `idf.py build flash monitor`.
2. **Wi-Fi Reconnect:** Turn off your local router. Verify the ESP32 logs show disconnection. Turn it back on and verify it reconnects.
3. **Backend Restart:** Restart the Render backend. The ESP32 should log `WEBSOCKET_EVENT_DISCONNECTED` and automatically reconnect when the backend comes back online.
4. **Audio Quality:** If detection is poor, modify `AUDIO_CHUNK_SIZE` or verify INMP441 wiring (especially the L/R pin being pulled to GND for the correct channel).
