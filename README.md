# Jarvis IoT Voice Assistant
A production-style voice-controlled IoT system using ESP32, INMP441 I2S microphone, and a Python FastAPI backend with openWakeWord.

## Folder Structure
- `backend/`: FastAPI application, WebSockets, and AI Wake-Word detection.
- `esp32_firmware/`: ESP-IDF C code for Wi-Fi, I2S Audio Streaming, and WebSocket client.
- `docs/`: Architecture diagrams, communication protocols, and deployment guides.

## Quick Start
1. Wire the INMP441 to the ESP32 (See `docs/ARCHITECTURE.md`).
2. Deploy the backend to Render using `render.yaml` (See `docs/DEPLOYMENT_AND_TESTING.md`).
3. Update `WIFI_SSID`, `WIFI_PASS`, and `WEBSOCKET_URL` in `esp32_firmware/main/main.c`.
4. Compile and flash the ESP32:
   ```bash
   cd esp32_firmware
   idf.py set-target esp32
   idf.py build flash monitor
   ```

Say "Jarvis", and the built-in LED on the ESP32 will toggle!
