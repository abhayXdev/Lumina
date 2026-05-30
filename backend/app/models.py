from pydantic import BaseModel
from typing import Optional, Literal

class Message(BaseModel):
    type: str

class HeartbeatMessage(Message):
    type: Literal["heartbeat"] = "heartbeat"
    device_id: str

class AuthMessage(Message):
    type: Literal["auth"] = "auth"
    device_id: str
    api_key: str

class CommandMessage(Message):
    type: Literal["command"] = "command"
    command: str

class StatusMessage(Message):
    type: Literal["status"] = "status"
    device_id: str
    status: str
