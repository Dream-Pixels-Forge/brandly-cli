"""Server configuration endpoint — tells the SPA which root it is serving."""

from __future__ import annotations

from fastapi import APIRouter, Request

from brandly_cli import __version__
from brandly_cli.stitch import TRANSITIONS
from brandly_cli.web.state import MAX_CLIP_DURATION

router = APIRouter(tags=["config"])


@router.get("/api/config")
async def config(request: Request) -> dict:
    """Return the bound root plus the CLI's model constraints.

    ``transitions`` and ``max_clip_duration`` come from the CLI modules so the
    UI cannot drift from what ``brandly stitch`` and the Agnes model support.
    """
    return {
        "root": str(request.app.state.root),
        "version": __version__,
        "transitions": list(TRANSITIONS),
        "max_clip_duration": MAX_CLIP_DURATION,
    }
