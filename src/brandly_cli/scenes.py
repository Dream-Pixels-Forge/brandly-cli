"""Explicit scene model + scene completeness evaluation (Goal 3).

Audit F6: scene identity used to be a list position (``shot_runner`` defaulted
``scene`` to the act's position), two acts each owned their own ``scene 1..N``,
and no authoritative answer existed to "which shots make up scene N?".

Audit F7: no gate ever checked that every shot of a scene exists, is the current
take, and passed QC — status surfaces showed flat counts only.

This module makes scenes first-class data:

* ``scenes.json`` (``docs/plan/``, next to ``production_plan.md``) is written by
  ``brandly produce`` and is the source of truth for scene membership.
* Scene ids are project-unique (``S01``, ``S02``, …) in first-appearance order
  even when two acts both declare ``scene 1``; the original ``act`` and scene
  number are preserved in the manifest.
* ``status()`` computes the per-scene matrix (expected / present / missing /
  stale); ``evaluate()``/``evaluate_all()`` add the quality gate via an injected
  runner (so this module never imports ffmpeg paths itself).

Verdicts mirror the existing element gate: ``pass`` → exit 0, ``warn`` → 1,
``fail`` → 2.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from brandly_cli import layout, shot_runner

SCENES_FILE = "scenes.json"
SCENES_VERSION = 1

#: Returns "pass" | "warn" | "fail" for one clip path (case-insensitive).
QualityRunner = Callable[[Path], str]


def scenes_path(project_id: str, *, root: Path | str | None = None) -> Path:
    """Where the manifest lives: ``docs/plan/scenes.json``."""
    base = Path(root) if root else Path.cwd()
    return layout.docs_dir(layout.resolve_project_dir(base, project_id), "plan") / SCENES_FILE


def build_scenes(
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    root: Path | str | None = None,
) -> dict[str, Any]:
    """Build the scene manifest from a flat list or a structured ``{"acts": …}`` shot list.

    Clip names mirror exactly what ``brandly produce`` produces for that input:
    * flat lists → ``clip_filename(scene, shot)`` (the flat plan loop passes
      ``scene``/``shot_number`` into the video command's save-time naming);
    * structured lists → ``Shot.clip_name`` (act-slug disambiguation, issue #50).
    """
    base = Path(root) if root else Path.cwd()
    images_dir = layout.resolve_media_root(base, project_id, "images")

    # (act, scene_number) in first-appearance order → list of shot expectations
    grouped: dict[tuple[str, int], list[dict[str, str]]] = {}

    if isinstance(data, list):
        for position, shot in enumerate(data, start=1):
            scene_number = shot_runner.as_int(shot.get("scene"), 1)
            index = shot_runner.as_int(shot.get("shot"), position)
            shot_id = str(shot.get("id") or shot.get("name") or f"shot-{position}")
            grouped.setdefault(("", scene_number), []).append(
                {
                    "id": shot_id,
                    "clip": shot_runner.clip_filename(scene_number, index),
                    "folder": "scenes",
                }
            )
    else:
        for shot_obj in shot_runner.flatten_shots(data, images_dir):
            grouped.setdefault((shot_obj.act, shot_obj.scene), []).append(
                {"id": shot_obj.id, "clip": shot_obj.clip_name, "folder": shot_obj.folder}
            )

    scenes_list: list[dict[str, Any]] = []
    for sequence, ((act, scene_number), shots) in enumerate(grouped.items(), start=1):
        scenes_list.append(
            {"id": f"S{sequence:02d}", "scene": scene_number, "act": act, "shots": shots}
        )

    return {"version": SCENES_VERSION, "project_id": project_id, "scenes": scenes_list}


def write_scenes(
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    root: Path | str | None = None,
) -> dict[str, Any]:
    """Build and atomically write the manifest. Returns the manifest dict."""
    manifest = build_scenes(project_id, data, root=root)
    path = scenes_path(project_id, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return manifest


def load_scenes(project_id: str, *, root: Path | str | None = None) -> dict[str, Any] | None:
    """Read the manifest, or ``None`` when absent/unreadable."""
    path = scenes_path(project_id, root=root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _require_manifest(project_id: str, *, root: Path | str | None = None) -> dict[str, Any]:
    manifest = load_scenes(project_id, root=root)
    if manifest is None:
        raise ValueError(
            f"scene manifest not found: {scenes_path(project_id, root=root)} — "
            "run `brandly produce <id> --shots shots.json` to register the shot list"
        )
    return manifest


def _find_clip(videos_root: Path, shot: dict[str, Any]) -> Path | None:
    """Locate a shot's current take (canonical folder first, then anywhere)."""
    folder = videos_root / str(shot.get("folder") or "scenes")
    candidate = folder / str(shot["clip"])
    if candidate.is_file() and candidate.stat().st_size > 0:
        return candidate
    if videos_root.is_dir():
        for found in videos_root.rglob(str(shot["clip"])):
            if found.is_file() and found.stat().st_size > 0:
                return found
    return None


def _stale_extras(videos_root: Path, shot: dict[str, Any]) -> list[str]:
    """Superseded takes beside the canonical clip (audit F7 / DoD "stale").

    ``stem-2.mp4``-style extra takes from one run (``name_clips``) are legitimate
    and excluded; anything else matching ``stem*`` is a leftover from an older
    naming scheme or another act.
    """
    folder = videos_root / str(shot.get("folder") or "scenes")
    if not folder.is_dir():
        return []
    stem = Path(str(shot["clip"])).stem
    extras: list[str] = []
    for found in sorted(folder.glob(stem + "*")):
        if found.suffix.lower() != ".mp4" or found.name == shot["clip"]:
            continue
        if re.fullmatch(rf"{re.escape(stem)}-\d+", Path(found.name).stem):
            continue  # legit extra take from the same run
        extras.append(found.name)
    return extras


def _scene_report(videos_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    shots_report: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    stale: list[dict[str, Any]] = []
    present_paths: dict[str, Path] = {}

    for shot in entry.get("shots", []):
        path = _find_clip(videos_root, shot)
        if path is None:
            shots_report.append({"id": shot["id"], "clip": shot["clip"], "state": "missing"})
            missing.append({"id": shot["id"], "clip": shot["clip"]})
            continue
        present_paths[shot["id"]] = path
        extras = _stale_extras(videos_root, shot)
        state = "present"
        if extras:
            stale.append({"id": shot["id"], "clip": shot["clip"], "files": extras})
            state = "stale"
        shots_report.append({"id": shot["id"], "clip": shot["clip"], "state": state})

    return {
        "id": entry.get("id", ""),
        "scene": entry.get("scene"),
        "act": entry.get("act", ""),
        "expected": len(entry.get("shots", [])),
        "present": len(present_paths),
        "missing": missing,
        "stale": stale,
        "shots": shots_report,
        "verdict": "fail" if (missing or stale) else "pass",
        "_paths": present_paths,  # internal: consumed by evaluate(), stripped for output
    }


_VERDICT_RANK = {"pass": 0, "warn": 1, "fail": 2}


def _worst(verdicts: list[str]) -> str:
    return max(verdicts, key=lambda v: _VERDICT_RANK.get(v, 2)) if verdicts else "pass"


def _public(report: dict[str, Any]) -> dict[str, Any]:
    """Strip internal keys before a report reaches a CLI/JSON consumer."""
    return {k: v for k, v in report.items() if not k.startswith("_")}


def status(project_id: str, *, root: Path | str | None = None) -> dict[str, Any]:
    """Full per-scene matrix: expected / present / missing / stale (no QC)."""
    manifest = _require_manifest(project_id, root=root)
    videos_root = layout.resolve_media_root(Path(root) if root else Path.cwd(), project_id, "videos")
    scene_reports = [_scene_report(videos_root, e) for e in manifest.get("scenes", [])]
    return {
        "project_id": project_id,
        "verdict": _worst([r["verdict"] for r in scene_reports]),
        "scenes": [_public(r) for r in scene_reports],
    }


def resolve_scene(manifest: dict[str, Any], ref: str) -> dict[str, Any]:
    """Look up one scene by id (``S01``) or by unique number (``1``)."""
    scenes_list = manifest.get("scenes", [])
    text = str(ref).strip()
    for entry in scenes_list:
        if entry.get("id") == text:
            return entry
    if text.isdigit():
        matches = [e for e in scenes_list if str(e.get("scene")) == text]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            ids = ", ".join(e.get("id", "?") for e in matches)
            raise ValueError(f"scene {text} is ambiguous across acts — use a scene id ({ids})")
    available = ", ".join(e.get("id", "?") for e in scenes_list) or "none"
    raise ValueError(f"unknown scene {ref!r} — available: {available}")


def _with_quality(report: dict[str, Any], gate_runner: QualityRunner) -> dict[str, Any]:
    """Run the deterministic quality gate over every present clip of a scene."""
    failures: list[dict[str, Any]] = []
    checked = 0
    for shot_id, path in report.get("_paths", {}).items():
        checked += 1
        try:
            # GateResult.status is lowercase ("pass"/"warn"/"fail") — normalize.
            status = gate_runner(path).strip().lower()
        except Exception as exc:  # a gate crash must fail the scene, not the CLI
            failures.append({"id": shot_id, "clip": path.name, "status": "fail", "error": str(exc)})
            continue
        if status in ("fail", "warn"):
            failures.append({"id": shot_id, "clip": path.name, "status": status})

    report["quality"] = {"checked": checked, "failures": failures, "skipped": False}
    if any(f["status"] == "fail" for f in failures):
        report["verdict"] = "fail"
    elif failures:  # WARN only — never promotes a fail, keeps pass→warn
        report["verdict"] = _worst([report["verdict"], "warn"])
    return report


def _evaluate_one(
    videos_root: Path,
    entry: dict[str, Any],
    gate_runner: QualityRunner | None,
) -> dict[str, Any]:
    report = _scene_report(videos_root, entry)
    if gate_runner is not None and report["present"] > 0:
        report = _with_quality(report, gate_runner)
    else:
        report["quality"] = {"checked": 0, "failures": [], "skipped": True}
    return _public(report)


def evaluate(
    project_id: str,
    ref: str,
    *,
    root: Path | str | None = None,
    gate_runner: QualityRunner | None = None,
) -> dict[str, Any]:
    """Gate one scene: completeness (+ stale detection), then quality if a runner is given."""
    manifest = _require_manifest(project_id, root=root)
    entry = resolve_scene(manifest, ref)
    videos_root = layout.resolve_media_root(Path(root) if root else Path.cwd(), project_id, "videos")
    return _evaluate_one(videos_root, entry, gate_runner)


def evaluate_all(
    project_id: str,
    *,
    root: Path | str | None = None,
    gate_runner: QualityRunner | None = None,
) -> dict[str, Any]:
    """Gate every scene of the project; the verdict is the worst scene verdict."""
    manifest = _require_manifest(project_id, root=root)
    videos_root = layout.resolve_media_root(Path(root) if root else Path.cwd(), project_id, "videos")
    reports = [
        _evaluate_one(videos_root, entry, gate_runner) for entry in manifest.get("scenes", [])
    ]
    return {
        "project_id": project_id,
        "verdict": _worst([r["verdict"] for r in reports]),
        "scenes": reports,
    }
