"""FastAPI server for the brandly timeline editor."""

from __future__ import annotations

import webbrowser
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from brandly_cli import __version__
from brandly_cli.web import deps, security
from brandly_cli.web.routes import clips, export, projects, timeline
from brandly_cli.web.utils.thumbnail import ensure_thumbnail

# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start background tasks, cleanup on shutdown."""
    yield
    # Cleanup on shutdown


def _discover_root(start: Path | None = None) -> Path:
    """Return the nearest ancestor containing ``.brandly``, else ``start``/cwd.

    Mirrors ``brandly_cli.cli._get_root`` so the server and the CLI agree on the
    project root when ``brandly timeline`` runs without ``--root``.
    """
    origin = (start or Path.cwd()).resolve()
    candidate = origin
    for _ in range(10):
        if (candidate / ".brandly").is_dir():
            return candidate
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return origin


def create_app(root: str | Path | None = None, *, token: str | None = None) -> FastAPI:
    """Create the FastAPI application, bound to ``root``.

    The root is owned by the server: routes read it from ``app.state`` and
    ignore any ``?root=`` a client supplies.
    """
    app = FastAPI(
        title="Brandly Timeline Editor",
        description="Visual timeline editor for brandly-cli projects",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.root = Path(root).resolve() if root else _discover_root()
    app.add_middleware(security.LocalGuardMiddleware, token=token)

    # Register routers
    from brandly_cli.web.routes import config as config_route
    app.include_router(config_route.router)
    app.include_router(projects.router)
    app.include_router(timeline.router)
    app.include_router(clips.router)
    app.include_router(export.router)

    # Static files for SPA
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Health endpoint
    @app.get("/health")
    async def health(request: Request) -> dict:
        return {"status": "ok", "root": str(request.app.state.root)}

    # SPA fallback
    @app.get("/")
    @app.get("/index.html")
    async def spa() -> HTMLResponse:
        static_dir = Path(__file__).parent / "static"
        index = static_dir / "index.html"
        if index.exists():
            return HTMLResponse(content=index.read_text(encoding="utf-8"))
        return HTMLResponse(content=_placeholder_html())

    # Clip preview + thumbnail — located via the timeline, never via a raw path
    @app.get("/api/projects/{project_id}/clips/{clip_id}/preview")
    async def preview_clip(project_id: str, clip_id: str, request: Request) -> Any:
        """Stream a clip's video file, located through its timeline entry."""
        media = deps.require_clip_media_file(request.app.state.root, project_id, clip_id)
        return FileResponse(str(media))

    @app.get("/api/projects/{project_id}/clips/{clip_id}/thumb")
    async def thumb_clip(project_id: str, clip_id: str, request: Request) -> Any:
        """Return the clip's first-frame thumbnail, extracting it if needed."""
        proj_dir, media = deps.require_clip_media(request.app.state.root, project_id, clip_id)
        rel = ensure_thumbnail(media, proj_dir)
        thumb = security.safe_join(proj_dir, rel) if rel else None
        if thumb is None or not thumb.is_file():
            raise HTTPException(status_code=404, detail="Thumbnail unavailable")
        return FileResponse(str(thumb), media_type="image/png")

    # WebSocket for generation progress
    @app.websocket("/ws/{project_id}")
    async def websocket_endpoint(websocket: WebSocket, project_id: str) -> None:
        """Register connection then forward generation events."""
        from brandly_cli.web.websocket import register, unregister

        await websocket.accept()
        register(project_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            unregister(project_id, websocket)

    return app


def _placeholder_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brandly Timeline</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 40px; background: #0a0a0a; color: #e0e0e0; }
        h1 { color: #fff; }
        .status { padding: 20px; background: #1a1a1a; border-radius: 8px; margin-top: 20px; }
        .warn { color: #facc15; }
    </style>
</head>
<body>
    <h1>Brandly Timeline Editor</h1>
    <div class="status">
        <p>Backend server is running.</p>
        <p class="warn">Frontend SPA not yet built. Run <code>npm run build</code> in <code>web/</code> to enable the full UI.</p>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def start_server(root: str, port: int = 8765, open_browser: bool = True) -> None:
    """Start the FastAPI server (blocking) with a fresh per-run token."""
    import uvicorn

    token = security.new_token()
    app = create_app(root=root, token=token)

    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}/?token={token}")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
