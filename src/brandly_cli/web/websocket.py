"""WebSocket broadcast helpers for the timeline editor.

Maintains a per-project registry of active ``WebSocket`` connections so the
regenerate route can push progress events without owning the connection pool.
Connections are stored on the ``FastAPI.app.state`` and cleaned up when the
server shuts down; no explicit unregistration is needed — dead connections
self-heal on the next send attempt.
"""

from __future__ import annotations

from typing import Any

_connections: dict[str, set] = {}


def register(project_id: str, ws: Any) -> None:
    group = _connections.setdefault(project_id, set())
    group.add(ws)


def unregister(project_id: str, ws: Any) -> None:
    group = _connections.get(project_id)
    if group:
        group.discard(ws)
        if not group:
            del _connections[project_id]


async def broadcast(project_id: str, event: dict[str, Any]) -> None:
    """Send *event* to every live WebSocket for *project_id*."""
    group = _connections.get(project_id)
    if not group:
        return
    gone = set()
    for ws in group:
        try:
            await ws.send_json(event)
        except Exception:
            gone.add(ws)
    for ws in gone:
        group.discard(ws)
    if not group:
        _connections.pop(project_id, None)


def clients(project_id: str) -> int:
    return len(_connections.get(project_id, set()))
