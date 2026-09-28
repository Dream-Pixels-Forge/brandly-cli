"""Review queue for the web UI (issue #127).

Human-in-the-loop gates (reference, storyboard, video, ``brandly gate``)
auto-approve in non-interactive/piped runs — which is exactly how agent-driven
production runs execute. This module queues everything that auto-approved
since the last human review session so the UI can approve/reject it
asynchronously:

- storyboard keyframes (``pre-production/<id>/images/storyboard/``)
- generated clips (``production/<id>/videos/scenes/``, gate score/issues from
  the durable ``gate_*.md`` reports)
- reference sheets (``pre-production/<id>/images/<category>/``)

Decisions live project-local in ``.brandly/<id>/docs/tmp/review_queue.json``
(the queue's source of truth); a reject writes the standard review note and
un-completes the shot in the progress log so the next run picks it up, an
approve stamps reviewer + timestamp into the generation record when one exists.

All reads are project-local and fail soft.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brandly_cli import layout
from brandly_cli.web import deps, monitor

REVIEW_FILENAME = "review_queue.json"

#: Queued stages and the media top folder each resolves against.
STAGES: dict[str, str] = {
    "storyboard": "images",
    "video": "videos",
    "reference": "images",
}

_ITEM_RE = re.compile(r"^(?P<stage>storyboard|video|reference):(?P<stem>.+)$")
_SCENE_RE = re.compile(r"^Scene-(?P<scene>\d{1,3})-")
_IMAGE_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.webp")


def _review_path(root: str | Path, project_id: str) -> Path:
    proj_dir = layout.project_dir(Path(root), project_id)
    return layout.docs_dir(proj_dir, "tmp") / REVIEW_FILENAME


def _decisions(root: str | Path, project_id: str) -> dict[str, dict[str, Any]]:
    """Decided items keyed by item_id (corrupt files degrade to empty)."""
    path = _review_path(root, project_id)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, list):
        return {}
    return {
        item["item_id"]: item
        for item in data
        if isinstance(item, dict) and item.get("item_id")
    }


def _record_decision(
    root: str | Path,
    project_id: str,
    item_id: str,
    *,
    decision: str,
    reviewer: str,
    note: str = "",
) -> None:
    """Append a decision to the project-local review state."""
    path = _review_path(root, project_id)
    decisions = list(_decisions(root, project_id).values())
    decisions = [d for d in decisions if d.get("item_id") != item_id]
    decisions.append(
        {
            "item_id": item_id,
            "decision": decision,
            "reviewer": reviewer,
            "note": note,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decisions, indent=2), encoding="utf-8")


def _scene_of(stem: str) -> int | None:
    match = _SCENE_RE.match(stem)
    return int(match.group("scene")) if match else None


def _shot_id_map(root: str | Path, project_id: str) -> dict[str, str]:
    """Clip stem -> shot-list id, so a rejected item re-flags the right shot.

    Built through the exact ``flatten_shots`` path the runners use; a shot
    list with missing plates or duplicate ids degrades to an empty mapping
    (the queue still renders, it just can't pre-fill the resume command).
    """
    from brandly_cli import shot_runner

    path = layout.project_dir(Path(root), project_id) / "shots.json"
    if not path.is_file():
        return {}
    try:
        data = shot_runner.load_shots_file(path)
        images_dir = layout.resolve_media_root(Path(root), project_id, "images")
        shots = shot_runner.flatten_shots(data, images_dir)
    except (OSError, ValueError):
        return {}
    mapping: dict[str, str] = {}
    for shot in shots:
        stem = Path(shot.clip_name.replace("\\", "/")).stem
        mapping.setdefault(stem, shot.id)
    return mapping


def _stage_bases(root_path: Path, project_id: str, stage: str) -> list[Path]:
    """Media bases for a stage, v2 first, legacy ``.brandly/<id>/`` second.

    Every candidate path is stored base-relative, so the media endpoint
    re-resolves it through ``safe_join`` against the same bases — a crafted
    item id can never reach outside the project.
    """
    proj_dir = layout.project_dir(root_path, project_id)
    if stage == "video":
        return [
            layout.resolve_media_root(root_path, project_id, "videos"),
            proj_dir / "videos",
        ]
    return [
        layout.resolve_media_root(root_path, project_id, "images"),
        proj_dir / "images",
    ]


def _candidates(root: str | Path, project_id: str, stage: str) -> list[tuple[Path, str]]:
    """(file, base-relative path) for every queued artifact of one stage.

    The v2 media root is scanned first (that's where the runners write); a
    duplicate stem resolves to the v2 file.
    """
    root_path = Path(root)
    found: list[tuple[Path, str]] = []
    seen: set[str] = set()

    if stage == "storyboard":
        for base in _stage_bases(root_path, project_id, stage):
            for ext in _IMAGE_EXTS:
                for img in sorted((base / "storyboard").glob(ext)):
                    if img.stem in seen:
                        continue
                    seen.add(img.stem)
                    found.append((img, f"storyboard/{img.name}"))
        return found

    if stage == "video":
        for base in _stage_bases(root_path, project_id, stage):
            for clip in sorted((base / "scenes").glob("*.mp4")):
                if clip.stem in seen:
                    continue
                seen.add(clip.stem)
                found.append((clip, f"scenes/{clip.name}"))
        return found

    if stage == "reference":
        for base in _stage_bases(root_path, project_id, stage):
            if not base.is_dir():
                continue
            for category in sorted(p for p in base.iterdir() if p.is_dir()):
                if category.name == "storyboard":
                    continue  # keyframes are their own stage
                for ext in _IMAGE_EXTS:
                    for img in sorted(category.glob(ext)):
                        key = str(img.resolve())
                        if key in seen:
                            continue
                        seen.add(key)
                        found.append((img, f"{category.name}/{img.name}"))
        return found

    raise ValueError(f"unknown review stage: {stage!r}")


def _items(root: str | Path, project_id: str) -> list[dict[str, Any]]:
    """Every auto-approved-not-yet-reviewed item across the three stages."""
    decisions = _decisions(root, project_id)
    gates = monitor.gate_scores(root, project_id)
    shot_map = _shot_id_map(root, project_id)

    items: list[dict[str, Any]] = []
    for stage in STAGES:
        for file, rel in _candidates(root, project_id, stage):
            if not file.is_file():
                continue
            item_id = f"{stage}:{file.stem}"
            if item_id in decisions:
                continue  # already reviewed by a human
            items.append(
                {
                    "item_id": item_id,
                    "stage": stage,
                    "path": rel,
                    "scene": _scene_of(file.stem),
                    "gate": (
                        {k: v for k, v in gates[file.stem].items() if k != "report"}
                        if stage in ("storyboard", "video") and file.stem in gates
                        else None
                    ),
                    "shot_id": shot_map.get(file.stem),
                    "decided": False,
                    "decided_at": None,
                    "modified": datetime.fromtimestamp(
                        file.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
    items.sort(key=lambda i: (i["stage"], str(i["item_id"])))
    return items


def queue(
    root: str | Path,
    project_id: str,
    *,
    stage: str | None = None,
    scene: int | None = None,
    below_threshold: int | None = None,
) -> dict[str, Any]:
    """The review queue with optional stage/scene/gate-threshold filters."""
    deps.require_project_dir(Path(root), project_id)
    items = _items(root, project_id)
    if stage is not None:
        items = [i for i in items if i["stage"] == stage]
    if scene is not None:
        items = [i for i in items if i["scene"] == scene]
    if below_threshold is not None:
        items = [
            i
            for i in items
            if i["gate"] is not None and int(i["gate"]["score"]) < below_threshold
        ]
    counts: dict[str, int] = dict.fromkeys(STAGES, 0)
    for item in items:
        counts[item["stage"]] += 1
    return {"project_id": project_id, "items": items, "counts": counts}


def _find_item(root: str | Path, project_id: str, item_id: str) -> dict[str, Any] | None:
    for item in _items(root, project_id):
        if item["item_id"] == item_id:
            return item
    return None


def _resolve_item_file(root: str | Path, project_id: str, item: dict[str, Any]) -> Path | None:
    """Resolve a queued item's file inside the project (containment enforced).

    Re-resolves the stored base-relative path against the stage's bases
    (v2 first, legacy second) through ``safe_join`` — the same pairing
    ``_candidates`` used to find it.
    """
    from brandly_cli.web.security import safe_join

    root_path = Path(root)
    for base in _stage_bases(root_path, project_id, item["stage"]):
        candidate = safe_join(base, item["path"])
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def _stamp_generation_record(
    root: str | Path,
    project_id: str,
    item: dict[str, Any],
    reviewer: str,
) -> bool:
    """Stamp reviewer + timestamp into the item's generation record (if any).

    Video clips and reference sheets have generation records
    (``docs/tmp/{video,reference}_<ts>.json``); storyboard keyframes do not —
    their decision lives in the review state alone.
    """
    asset_type = {"video": "video", "reference": "reference"}.get(item["stage"])
    if asset_type is None:
        return False
    docs_tmp = layout.docs_dir(layout.project_dir(Path(root), project_id), "tmp")
    if not docs_tmp.is_dir():
        return False
    stem = item["item_id"].split(":", 1)[1]
    stamped = False
    for record in sorted(docs_tmp.glob(f"{asset_type}_*.json")):
        try:
            data = json.loads(record.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        output = str(data.get("output_file", "")).replace("\\", "/")
        if Path(output).stem != stem:
            continue
        data["review"] = {
            "reviewer": reviewer,
            "decision": "approved",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        record.write_text(json.dumps(data, indent=2), encoding="utf-8")
        stamped = True  # later records win
    return stamped


def approve(root: str | Path, project_id: str, item_id: str, reviewer: str) -> dict[str, Any]:
    """Approve a queued item: stamp the record, remove it from the queue."""
    deps.require_project_dir(Path(root), project_id)
    item = _find_item(root, project_id, item_id)
    if item is None:
        return {"status": "error", "error": f"Unknown review item: {item_id}"}
    stamped = _stamp_generation_record(root, project_id, item, reviewer)
    _record_decision(
        root, project_id, item_id, decision="approved", reviewer=reviewer
    )
    return {
        "status": "approved",
        "item_id": item_id,
        "shot_id": item["shot_id"],
        "stamped": stamped,
    }


def reject(
    root: str | Path,
    project_id: str,
    item_id: str,
    note: str,
    reviewer: str,
) -> dict[str, Any]:
    """Reject a queued item: review note + re-flag the shot for a re-run."""
    deps.require_project_dir(Path(root), project_id)
    item = _find_item(root, project_id, item_id)
    if item is None:
        return {"status": "error", "error": f"Unknown review item: {item_id}"}

    from brandly_cli.gates import write_review_note

    note_path = write_review_note(
        Path(root),
        project_id,
        item["stage"],
        note or "no note",
        extra=f"**Item:** {item_id}\n**Reviewer:** {reviewer}",
    )
    unflagged = _unflag_shot(root, project_id, item)
    _record_decision(
        root, project_id, item_id, decision="rejected", reviewer=reviewer, note=note or ""
    )
    return {
        "status": "rejected",
        "item_id": item_id,
        "shot_id": item["shot_id"],
        "note_path": str(note_path),
        "unflagged": unflagged,
    }


def _unflag_shot(root: str | Path, project_id: str, item: dict[str, Any]) -> bool:
    """Un-complete the shot in its progress log so the next run re-runs it.

    The progress logs match by bare shot id (``<ts> <id> <OK|RETRY|FAIL>``
    per ``ProgressLog``), so removing every line for the shot makes it
    pending again — the next ``produce --only <id>`` / storyboard re-run
    picks it up.
    """
    stage = item["stage"]
    progress_stage = "produce" if stage == "video" else "storyboard"
    shot_id = item.get("shot_id")
    if not shot_id:
        return False
    path = monitor.progress_path(root, project_id, progress_stage)
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    kept: list[str] = []
    removed = False
    for line in lines:
        parsed = monitor.parse_line(line)
        if parsed is not None and parsed["shot_id"] == shot_id:
            removed = True
            continue
        kept.append(line)
    if removed:
        path.write_text(
            ("\n".join(kept) + "\n") if kept else "", encoding="utf-8"
        )
    return removed


def media_file(root: str | Path, project_id: str, item_id: str) -> Path:
    """Resolve a queued item's media file for the preview route, or raise 404."""
    deps.require_project_dir(Path(root), project_id)
    item = _find_item(root, project_id, item_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Review item not found: {item_id}")
    media = _resolve_item_file(root, project_id, item)
    if media is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Review item file not found: {item_id}")
    return media


__all__ = [
    "REVIEW_FILENAME",
    "STAGES",
    "approve",
    "media_file",
    "queue",
    "reject",
]
