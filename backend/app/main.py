from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from app.websocket_manager import manager
from app.config import settings
from app.utils.logger import logger

app = FastAPI(title="Jarvis IoT Backend")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Jarvis IoT Backend is running"}

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str, api_key: str = None):
    # Basic Authentication via query parameter
    if api_key != settings.api_key:
        logger.warning(f"Unauthorized connection attempt from {device_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, device_id)
    try:
        while True:
            # Receive data. Can be text (JSON) or binary (Audio PCM)
            message = await websocket.receive()
            
            if "bytes" in message:
                await manager.handle_binary_audio(device_id, message["bytes"])
            elif "text" in message:
                await manager.handle_text_message(device_id, message["text"])
                
    except WebSocketDisconnect:
        manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"Error in websocket for {device_id}: {str(e)}")
        manager.disconnect(device_id)
