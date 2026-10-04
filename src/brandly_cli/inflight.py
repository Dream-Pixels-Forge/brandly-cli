"""Issue #114: durable in-flight video-task ledger.

If the process dies between task create and download (crash, Ctrl-C, timeout
exit), the task id previously existed only inside a plan file - a crashed run
silently stranded generated video that already spent quota server-side.
``brandly video`` now records every created task here BEFORE polling starts
and clears it on a terminal state (downloaded or failed), so
``brandly job-resume --sweep <project>`` can adopt stranded tasks later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brandly_cli import layout

LEDGER_FILENAME = "inflight_jobs.json"


def _ledger_path(root: Path, project_id: str) -> Path:
    return layout.docs_dir(layout.project_dir(root, project_id), "tmp") / LEDGER_FILENAME


def entries(root: Path, project_id: str) -> list[dict[str, Any]]:
    """Read the ledger; corrupted files degrade to an empty ledger."""
    path = _ledger_path(root, project_id)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, dict) and e.get("video_id")]


def add(root: Path, project_id: str, video_id: str, note: str = "") -> None:
    """Record a created task (dedupe by video_id) before polling starts."""
    if not video_id:
        return
    path = _ledger_path(root, project_id)
    current = entries(root, project_id)
    if any(e.get("video_id") == video_id for e in current):
        return
    from brandly_cli.io import now_iso

    current.append(
        {"video_id": video_id, "note": note, "created_at": now_iso()}
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")


def remove(root: Path, project_id: str, video_id: str) -> None:
    """Clear a task that reached a terminal state (downloaded / failed)."""
    path = _ledger_path(root, project_id)
    current = [e for e in entries(root, project_id) if e.get("video_id") != video_id]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
