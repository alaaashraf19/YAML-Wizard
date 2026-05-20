from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .connection_manager import ws_manager

router = APIRouter()

@router.websocket("/ws/{repo_id}")
async def websocket_endpoint(websocket: WebSocket, repo_id: int):
    await ws_manager.connect(websocket, repo_id)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, repo_id)