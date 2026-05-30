from typing import Dict, Any
from app.utils.logger import logger

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}

    def register_device(self, device_id: str, connection: Any):
        self.devices[device_id] = {
            "connection": connection,
            "online": True,
            "led_state": False # Start assuming LED is off
        }
        logger.info(f"Device registered: {device_id}")

    def unregister_device(self, device_id: str):
        if device_id in self.devices:
            self.devices[device_id]["online"] = False
            self.devices[device_id]["connection"] = None
            logger.info(f"Device unregistered: {device_id}")

    def update_heartbeat(self, device_id: str):
        if device_id in self.devices:
            logger.debug(f"Heartbeat received for {device_id}")
            # Could add last_heartbeat timestamp here

    def toggle_led_state(self, device_id: str) -> str:
        if device_id in self.devices:
            current_state = self.devices[device_id]["led_state"]
            new_state = not current_state
            self.devices[device_id]["led_state"] = new_state
            return "on" if new_state else "off"
        return "off"
        
    def get_connection(self, device_id: str):
        if device_id in self.devices and self.devices[device_id]["online"]:
            return self.devices[device_id]["connection"]
        return None

device_manager = DeviceManager()
