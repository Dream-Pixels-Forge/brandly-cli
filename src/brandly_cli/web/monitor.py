"""Production monitor data for the web UI (issue #126).

Long produce runs already leave everything needed on disk — the plain-text
progress logs (``docs/tmp/produce_progress.txt`` / ``storyboard_progress.txt``),
the durable quality-gate reports (``docs/tmp/gate_*.md``) and the per-video
generation records (``docs/tmp/video_*.json``) — but nothing surfaced it.
This module reads those artifacts into a JSON snapshot the panel renders,
plus a line-offset tail the websocket pushes live.

All reads are project-local and fail soft: a missing or malformed file
degrades to an empty section, never a 500.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from brandly_cli import layout

#: How often the websocket watcher polls the progress logs (issue #126).
TAIL_INTERVAL = 1.5

#: Progress stages the monitor tails (file names are fixed, never user input).
STAGES: tuple[str, ...] = ("produce", "storyboard")

_PROGRESS_FILE = {
    "produce": "produce_progress.txt",
    "storyboard": "storyboard_progress.txt",
}

#: ``<ts> <shot-id> <OK|RETRY|FAIL> exit=<n> [retry=N] [backoff=Xs] [note]``
_LINE_RE = re.compile(
    r"^(?P<ts>\S+)\s+(?P<shot_id>\S+)\s+(?P<status>OK|RETRY|FAIL)\s+exit=(?P<exit>-?\d+)"
    r"(?:\s+retry=(?P<retry>\d+))?(?:\s+backoff=(?P<backoff>\S+))?"
    r"(?P<note>.*)$"
)

#: Gate report header/status lines (``quality_gate.GateResult.markdown()``).
_GATE_HEADER_RE = re.compile(r"^#\s+Quality Gate Report\s+—\s+(?P<element>.+)$")
_GATE_STATUS_RE = re.compile(
    r"\*\*Status:\*\*\s*\S+\s+(?P<status>PASS|WARN|FAIL)\s+\((?P<score>\d+)/100\)"
)

#: Provider error markers worth distinguishing at a glance (issue #126).
_HTTP_RE = re.compile(r"\b(?P<code>429|500|502|503)\b")


def progress_path(root: str | Path, project_id: str, stage: str) -> Path:
    """Absolute path of a stage's progress log (fixed name, no user input)."""
    if stage not in _PROGRESS_FILE:
        raise ValueError(f"unknown monitor stage: {stage!r}")
    proj_dir = layout.project_dir(Path(root), project_id)
    return layout.docs_dir(proj_dir, "tmp") / _PROGRESS_FILE[stage]


def _read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    return [ln for ln in text.splitlines() if ln.strip()]


def tail(root: str | Path, project_id: str, stage: str, offset: int) -> dict[str, Any]:
    """Lines of the stage log after *offset*, plus the new line offset.

    ``offset`` is a line count (not bytes), so it survives file rewrites: when
    a resumed run truncates the log the offset resets and the file replays
    from the top instead of silently dropping everything.
    """
    lines = _read_lines(progress_path(root, project_id, stage))
    start = offset if 0 <= offset <= len(lines) else 0
    return {"lines": lines[start:], "offset": len(lines)}


def _parse_line(line: str) -> dict[str, Any] | None:
    match = _LINE_RE.match(line.strip())
    if not match:
        return None
    groups = match.groupdict()
    return {
        "timestamp": groups["ts"],
        "shot_id": groups["shot_id"],
        "status": groups["status"],
        "exit_code": int(groups["exit"]),
        "retries": int(groups["retry"]) if groups["retry"] else 0,
        "backoff": (groups["backoff"] or "").strip() or None,
        "note": (groups["note"] or "").strip(),
    }


def _stage_state(root: str | Path, project_id: str, stage: str) -> dict[str, dict[str, Any]]:
    """Last line + attempt accounting per shot id for one stage."""
    state: dict[str, dict[str, Any]] = {}
    for line in _read_lines(progress_path(root, project_id, stage)):
        parsed = _parse_line(line)
        if parsed is None:
            continue
        entry = state.setdefault(parsed["shot_id"], {"last": parsed, "lines": 0, "backoff": None})
        entry["last"] = parsed
        entry["lines"] += 1
        if parsed["backoff"]:
            entry["backoff"] = parsed["backoff"]
    return state


def _shot_ids(root: str | Path, project_id: str) -> list[dict[str, Any]]:
    """Shot list rows for the monitor matrix, without resolving plates.

    Mirrors ``shot_runner.flatten_shots`` id resolution (``id`` / ``name`` /
    positional fallback) but never touches the filesystem beyond the list, so
    a shot list whose plates are missing still renders in the panel.
    """
    path = layout.project_dir(Path(root), project_id) / "shots.json"
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    shots: list[tuple[Any, dict[str, Any]]] = []
    if isinstance(raw, list):
        shots = [(1, s) for s in raw if isinstance(s, dict)]
    elif isinstance(raw, dict) and isinstance(raw.get("acts"), dict):
        for position, (act_key, act) in enumerate(raw["acts"].items(), start=1):
            if not isinstance(act, dict):
                continue
            scene = act.get("scene", act_key if str(act_key).isdigit() else position)
            for shot in act.get("shots", []) or []:
                if isinstance(shot, dict):
                    shots.append((scene, shot))
    else:
        return []

    rows: list[dict[str, Any]] = []
    for position, (scene, shot) in enumerate(shots, start=1):
        sid = shot.get("id") or shot.get("name") or f"shot-{position}"
        rows.append({"shot_id": str(sid), "scene": scene})
    return rows


def gate_scores(root: str | Path, project_id: str) -> dict[str, dict[str, Any]]:
    """Newest gate report per take, keyed by clip stem.

    ``gate_<kind>_<YYYYmmdd-HHMMSS>.md`` sorts chronologically, so later
    reports overwrite earlier ones for the same take.
    """
    docs_tmp = layout.docs_dir(layout.project_dir(Path(root), project_id), "tmp")
    if not docs_tmp.is_dir():
        return {}
    gates: dict[str, dict[str, Any]] = {}
    for report in sorted(docs_tmp.glob("gate_*.md")):
        try:
            text = report.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        element: str | None = None
        status: str | None = None
        score: int | None = None
        issues: list[str] = []
        in_failures = False
        for line in text.splitlines():
            header = _GATE_HEADER_RE.match(line)
            if header:
                element = header.group("element").strip()
                continue
            verdict = _GATE_STATUS_RE.search(line)
            if verdict:
                status = verdict.group("status").lower()
                score = int(verdict.group("score"))
                continue
            stripped = line.strip()
            if stripped.startswith("## "):
                in_failures = stripped == "## Failures"
                continue
            if in_failures and stripped.startswith("- "):
                issues.append(stripped[2:].strip())
        if not element or status is None or score is None:
            continue
        stem = Path(element.replace("\\", "/")).stem
        gates[stem] = {
            "score": score,
            "status": status,
            "issues": issues,
            "report": str(report),
        }
    return gates


def shot_rows(root: str | Path, project_id: str) -> list[dict[str, Any]]:
    """Per-shot monitor rows: stage status, retries, gate score, resume cmd."""
    produce = _stage_state(root, project_id, "produce")
    storyboard = _stage_state(root, project_id, "storyboard")
    gates = gate_scores(root, project_id)

    rows: list[dict[str, Any]] = []
    for shot in _shot_ids(root, project_id):
        sid = shot["shot_id"]
        p = produce.get(sid)
        s = storyboard.get(sid)
        last = p["last"] if p else (s["last"] if s else None)
        retries = int(last["retries"]) if last else 0
        line_count = (p["lines"] if p else 0) + (s["lines"] if s else 0)
        produce_status = p["last"]["status"] if p else "pending"
        rows.append(
            {
                "shot_id": sid,
                "scene": shot["scene"],
                "produce": produce_status,
                "storyboard": s["last"]["status"] if s else "pending",
                "attempts": max(line_count, retries + 1) if line_count else 0,
                "retries": retries,
                "backoff": (p or {}).get("backoff") or (s or {}).get("backoff"),
                "note": (p["last"]["note"] if p else "") or (s["last"]["note"] if s else ""),
                "exit_code": last["exit_code"] if last else None,
                "timestamp": last["timestamp"] if last else None,
                "gate": (
                    {k: v for k, v in gates[sid].items() if k != "report"}
                    if sid in gates
                    else None
                ),
                "resume_command": (
                    f"brandly produce {project_id} --only {sid}"
                    if produce_status in ("FAIL", "RETRY")
                    else None
                ),
            }
        )
    return rows


def provider_health(root: str | Path, project_id: str) -> dict[str, Any]:
    """Quota + last provider error, so quota/down/rate-storm reads at a glance.

    The numbers come from #118 (``video_seconds_today`` across all projects —
    the quota is per account); the error comes from the newest ``FAIL`` line
    in the produce log, with its HTTP marker (429/503) lifted out so the
    panel can label the failure instead of showing raw text.
    """
    from brandly_cli.cost_tracker import (
        NOMINAL_VIDEO_SECONDS_PER_DAY,
        video_seconds_today,
    )

    quota = video_seconds_today(root)
    last_error: dict[str, Any] | None = None
    for line in _read_lines(progress_path(root, project_id, "produce")):
        parsed = _parse_line(line)
        if parsed and parsed["status"] == "FAIL":
            marker = _HTTP_RE.search(parsed["note"] or "")
            last_error = {
                "shot_id": parsed["shot_id"],
                "timestamp": parsed["timestamp"],
                "note": parsed["note"],
                "http_status": int(marker.group("code")) if marker else None,
            }

    if quota["seconds"] >= NOMINAL_VIDEO_SECONDS_PER_DAY > 0:
        status = "quota_exhausted"
    elif last_error is None:
        status = "ok"
    elif last_error["http_status"] == 429:
        status = "rate_limit"
    elif (last_error["http_status"] or 0) >= 500:
        status = "server_error"
    else:
        status = "failed"

    return {
        "status": status,
        "video_seconds_today": quota["seconds"],
        "quota_seconds": NOMINAL_VIDEO_SECONDS_PER_DAY,
        "records": quota["records"],
        "last_error": last_error,
    }


def snapshot(root: str | Path, project_id: str) -> dict[str, Any]:
    """Everything the Production Monitor panel needs in one GET."""
    return {
        "project_id": project_id,
        "shots": shot_rows(root, project_id),
        "provider": provider_health(root, project_id),
        "gates": gate_scores(root, project_id),
        "tail": {stage: tail(root, project_id, stage, 0) for stage in STAGES},
    }


async def watch(
    root: str | Path,
    project_id: str,
    ws: Any,
    *,
    interval: float | None = None,
) -> None:
    """Push new progress lines to *ws* as ``monitor_tail`` events (issue #126).

    History belongs to the snapshot the panel already fetched, so offsets
    start at the current end of each log and only *new* lines stream. Exits
    quietly once the socket goes away or the task is cancelled.
    """
    import asyncio

    iv = TAIL_INTERVAL if interval is None else interval
    offsets = {stage: tail(root, project_id, stage, 0)["offset"] for stage in STAGES}
    try:
        while True:
            await asyncio.sleep(iv)
            for stage in STAGES:
                chunk = tail(root, project_id, stage, offsets[stage])
                offsets[stage] = chunk["offset"]
                if not chunk["lines"]:
                    continue
                await ws.send_json(
                    {
                        "type": "monitor_tail",
                        "stage": stage,
                        "lines": chunk["lines"],
                        "offset": chunk["offset"],
                    }
                )
    except asyncio.CancelledError:
        raise
    except Exception:
        # Dead socket: stop watching; the endpoint cleans up on disconnect.
        return


__all__ = [
    "STAGES",
    "TAIL_INTERVAL",
    "gate_scores",
    "progress_path",
    "provider_health",
    "shot_rows",
    "snapshot",
    "tail",
    "watch",
]
