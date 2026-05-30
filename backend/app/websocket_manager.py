from fastapi import WebSocket, WebSocketDisconnect
import json
from app.models import AuthMessage, HeartbeatMessage, StatusMessage, CommandMessage
from app.wakeword import WakeWordDetector
from app.device_manager import device_manager
from app.config import settings
from app.utils.logger import logger

class ConnectionManager:
    def __init__(self):
        self.wakeword_detectors = {} # Map device_id to its WakeWordDetector

    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        device_manager.register_device(device_id, websocket)
        self.wakeword_detectors[device_id] = WakeWordDetector()
        logger.info(f"WebSocket connected for {device_id}")

    def disconnect(self, device_id: str):
        device_manager.unregister_device(device_id)
        if device_id in self.wakeword_detectors:
            del self.wakeword_detectors[device_id]
        logger.info(f"WebSocket disconnected for {device_id}")

    async def handle_binary_audio(self, device_id: str, data: bytes):
        detector = self.wakeword_detectors.get(device_id)
        if not detector:
            return

        # Process audio chunk
        is_detected = detector.process_audio(data)
        
        if is_detected:
            # Wake word found! Toggle LED.
            new_state = device_manager.toggle_led_state(device_id)
            command = {"type": "command", "command": f"led_{new_state}"}
            await self.send_json(device_id, command)
            logger.info(f"Sent command to {device_id}: {command}")

    async def handle_text_message(self, device_id: str, text: str):
        try:
            data = json.loads(text)
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                device_manager.update_heartbeat(device_id)
            elif msg_type == "status":
                logger.info(f"Status from {device_id}: {data.get('status')}")
            else:
                logger.warning(f"Unknown message type from {device_id}: {text}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {device_id}: {text}")

    async def send_json(self, device_id: str, message: dict):
        connection = device_manager.get_connection(device_id)
        if connection:
            await connection.send_json(message)

manager = ConnectionManager()
