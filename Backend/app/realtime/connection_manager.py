import json
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:

    """Manages WebSocket connections per repository"""

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, repo_id: int) -> None:

        await websocket.accept()
        self._connections[repo_id].append(websocket)

    def disconnect(self, websocket: WebSocket, repo_id: int) -> None:
        
        self._connections[repo_id] = [
            ws for ws in self._connections[repo_id] if ws is not websocket
        ]

    async def broadcast(self, repo_id: int, data: dict) -> None:

        """Send data to all clients watching a repository."""

        message = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in self._connections[repo_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, repo_id)

    @property
    def active_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


ws_manager = ConnectionManager()