"""
WebSocket connection manager.
Single-instance in-memory set of active connections.

Production note: For horizontal scaling (multiple backend instances),
replace with Redis pub/sub so all instances can broadcast to all clients.
"""
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Thread-safe in CPython due to GIL; fine for single-instance async server
_active_connections: set[WebSocket] = set()


async def connect(ws: WebSocket) -> None:
    await ws.accept()
    _active_connections.add(ws)
    logger.debug("WS connected. Total: %d", len(_active_connections))


def disconnect(ws: WebSocket) -> None:
    _active_connections.discard(ws)
    logger.debug("WS disconnected. Total: %d", len(_active_connections))


async def broadcast(event: str, data: dict) -> None:
    """
    Broadcast an event to all connected clients.
    Dead connections are silently removed.
    """
    if not _active_connections:
        return

    message = json.dumps({"event": event, "data": data})
    dead: set[WebSocket] = set()

    for ws in _active_connections:
        try:
            await ws.send_text(message)
        except Exception as exc:
            logger.debug("WS send failed (%s), marking dead", exc)
            dead.add(ws)

    _active_connections -= dead


def connection_count() -> int:
    return len(_active_connections)
