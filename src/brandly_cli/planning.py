"""Generation plans, production plans and generation docs (utils split, P1-5).

The planning half of the former kitchen-sink ``utils.py``: pre-generation
plan files, the production-plan table (single source of truth for where
each plan came from), generation docs and project artifact detection.
``utils.py`` keeps re-export shims for compatibility (deprecated).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from brandly_cli import layout
from brandly_cli.io import (
    datetime_iso,
    human_size,
    sanitize_filename,
    write_json,
)

_PRODUCTION_PLAN_FILE = "production_plan.md"

def _plan_signature(
    asset_type: str,
    prompt: str,
    model: str,
    style: str,
    config: dict[str, Any],
) -> str:
    """Stable hash of a generation config — detects an unchanged plan."""
    payload = json.dumps(
        {
            "asset": asset_type,
            "prompt": prompt,
            "model": model,
            "style": style,
            "config": config,
        },
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def write_generation_plan(
    project_id: str,
    asset_type: str,
    *,
    root: Path | None = None,
    prompt: str,
    model: str,
    style: str,
    extra_config: dict[str, Any] | None = None,
    source: str = "",
    shot_id: str | None = None,
    scene: int | None = None,
    act: str | None = None,
) -> tuple[Path, bool]:
    """Write a generation plan BEFORE attempting API calls.

    If a plan with an identical configuration already exists it is REUSED
    instead of creating a new file — e.g. when retrying after a failed
    generation. A new plan is only created when something in the
    configuration (asset type, prompt, model, style, extra config) changed.

    Creates: {root}/.brandly/{id}/docs/plan/plan_{asset_type}[_{shot_id}]_{timestamp}.md

    When ``shot_id`` is given it is embedded in the file name and recorded
    in the plan metadata + production plan table (issue #37), so a reviewer
    can match a plan file to its shot without reading the file. ``scene``
    and ``act`` are recorded as plan metadata when provided.

    This ensures we have a record of what we INTENDED to generate,
    even if the API call fails. Every plan is registered in the production
    plan document (``docs/plan/production_plan.md``) with its origin.

    Args:
        source: Which command/workflow created this plan
            (e.g. ``"brandly video"``) — recorded in the production plan.

    Returns:
        (plan_path, reused) where ``reused`` is True when an existing plan
        with the same configuration was returned.
    """
    from datetime import datetime, timezone

    base = Path(root) if root else Path.cwd()
    plan_dir = layout.docs_dir(
        layout.resolve_project_dir(base, project_id), "plan"
    )
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = dict(extra_config or {})
    if shot_id:
        config["Shot ID"] = str(shot_id)
    if scene is not None:
        config["Scene"] = str(scene)
    if act:
        config["Act"] = str(act)
    signature = _plan_signature(asset_type, prompt, model, style, config)

    # Reuse an existing plan when nothing changed (retry after failure)
    marker = f"<!-- plan-signature: {signature} -->"
    rows = _read_production_plan_rows(
        production_plan_path(project_id, root=root)
    )
    for plan_file in sorted(plan_dir.glob(f"plan_{asset_type}_*.md")):
        try:
            content = plan_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if marker in content:
            prev_status = rows.get(plan_file.name, {}).get("status", "PENDING")
            status = "PENDING" if prev_status in ("", "FAILED") else prev_status
            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan_file),
                asset_type=asset_type,
                model=model,
                status=status,
                source=source,
            )
            return plan_file, True

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # Issue #37: shot-id plans are named plan_{asset_type}_{shot_id}_{ts}.md
    name_tag = f"{asset_type}_{sanitize_filename(str(shot_id))}" if shot_id else asset_type

    md_content = f"""# Generation Plan: {asset_type.title()}

{marker}
**Project:** {project_id}
**Planned:** {datetime_iso()}
**Status:** PENDING
"""
    if shot_id:
        md_content += f"**Shot ID:** {shot_id}\n"
    if scene is not None:
        md_content += f"**Scene:** {scene}\n"
    if act:
        md_content += f"**Act:** {act}\n"
    md_content += "\n"

    md_content += "## Configuration\n\n"
    md_content += (
        "| Parameter | Value |\n"
        "|-----------|-------|\n"
        f"| Model | {model} |\n"
        f"| Style | {style} |\n"
        f"| Asset Type | {asset_type} |\n"
    )

    # Add extra config
    for key, value in config.items():
        md_content += f"| {key.title()} | {value} |\n"

    md_content += f"""
## Prompt

```
{prompt}
```

## Notes

- Plan written before API call
- Will be updated with results after generation
- Use this to track generation intent vs actual output
"""

    plan_path = plan_dir / f"plan_{name_tag}_{ts}.md"
    if plan_path.exists():
        # A different config was written within the same second — use a
        # disambiguated filename so both plans survive.
        for i in range(2, 100):
            candidate = plan_dir / f"plan_{name_tag}_{ts}_{i}.md"
            if not candidate.exists():
                plan_path = candidate
                break
    plan_path.write_text(md_content, encoding="utf-8")

    upsert_production_plan(
        project_id,
        root=root,
        plan_file=str(plan_path),
        asset_type=asset_type,
        model=model,
        status="PENDING",
        source=source,
        shot_id=str(shot_id) if shot_id else "",
    )

    return plan_path, False


def production_plan_path(project_id: str, *, root: Path | None = None) -> Path:
    """Return the production plan document: ``docs/plan/production_plan.md``."""
    base = Path(root) if root else Path.cwd()
    return (
        layout.docs_dir(layout.resolve_project_dir(base, project_id), "plan")
        / _PRODUCTION_PLAN_FILE
    )


def _read_production_plan_rows(path: Path) -> dict[str, dict[str, str]]:
    """Parse the production plan table into ``{plan_filename: {col: value}}``.

    Handles both the legacy 7-column table and the current 8-column table
    (with a ``Shot ID`` column, issue #37).
    """
    rows: dict[str, dict[str, str]] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|--") or line.startswith(
            "| Plan"
        ):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] in ("Plan", ""):
            continue
        if len(cells) == 8:
            # | Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |
            if len(cells) < 8:
                continue
            rows[cells[0]] = {
                "asset": cells[1],
                "shot_id": cells[2],
                "model": cells[3],
                "source": cells[4],
                "status": cells[5],
                "created": cells[6],
                "updated": cells[7],
            }
        elif len(cells) == 7:
            rows[cells[0]] = {
                "asset": cells[1],
                "shot_id": "",
                "model": cells[2],
                "source": cells[3],
                "status": cells[4],
                "created": cells[5],
                "updated": cells[6],
            }
        else:
            continue
    return rows


def _write_production_plan(
    path: Path, rows: dict[str, dict[str, str]]
) -> None:
    lines = [
        "# Production Plan",
        "",
        "Single source of truth for every generation plan in this project.",
        "Each row records where the plan came from (source command) and its status.",
        "",
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |",
        "|------|-------|---------|-------|--------|--------|---------|---------|",
    ]
    for name in sorted(rows):
        r = rows[name]
        lines.append(
            f"| {name} | {r['asset']} | {r.get('shot_id', '—') or '—'} | {r['model']} | {r['source']} "
            f"| {r['status']} | {r['created']} | {r['updated']} |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def upsert_production_plan(
    project_id: str,
    *,
    root: Path | None = None,
    plan_file: str,
    asset_type: str,
    model: str,
    status: str,
    source: str = "",
    shot_id: str = "",
) -> Path:
    """Register/update one plan in the production plan document.

    The production plan (``docs/plan/production_plan.md``) is the single
    source of truth for where each generation plan came from. Rows are
    keyed by plan filename; existing rows keep their creation time.
    ``shot_id`` (issue #37) identifies which shot a video plan belongs to,
    so a reviewer can match plan files to shots without opening them.
    """
    path = production_plan_path(project_id, root=root)
    rows = _read_production_plan_rows(path)
    key = os.path.basename(plan_file)
    prev = rows.get(key, {})
    now = datetime_iso()
    rows[key] = {
        "asset": asset_type,
        "shot_id": shot_id or prev.get("shot_id", ""),
        "model": model,
        "source": source or prev.get("source", "—"),
        "status": status,
        "created": prev.get("created", now),
        "updated": now,
    }
    _write_production_plan(path, rows)
    return path


def write_generation_doc(
    project_id: str,
    asset_type: str,
    output_path: Path,
    *,
    root: Path | None = None,
    prompt: str,
    model: str,
    style: str | None = None,
    metadata: dict[str, Any] | None = None,
    source: str = "",
    plan_file: str | None = None,
) -> Path:
    """Write a generation document (JSON + Markdown) for user reference.

    Creates:
    - {root}/.brandly/{id}/docs/tmp/{type}_{timestamp}.json
    - {root}/.brandly/{id}/docs/tmp/{type}_{timestamp}.md

    Also updates any pending plan files for this asset type, and marks
    the matching plan COMPLETED in the production plan document
    (the source of truth for where each plan came from) when
    ``plan_file`` is given.
    """
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = Path(root) if root else Path.cwd()
    docs_dir = layout.docs_dir(
        layout.resolve_project_dir(base, project_id), "tmp"
    )
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Build metadata
    doc_meta = {
        "project_id": project_id,
        "asset_type": asset_type,
        "model": model,
        "style": style or "default",
        "prompt": prompt,
        "output_file": str(output_path),
        "output_size_bytes": output_path.stat().st_size if output_path.exists() else 0,
        "generated_at": datetime_iso(),
        "status": "completed",
        "metadata": metadata or {},
    }
    _file_size = int(doc_meta["output_size_bytes"])  # type: ignore[call-overload]

    # Write JSON doc
    json_path = docs_dir / f"{asset_type}_{ts}.json"
    write_json(json_path, doc_meta)

    # Write Markdown doc
    md_path = docs_dir / f"{asset_type}_{ts}.md"
    md_content = f"""# {asset_type.title()} Generation Record

**Project:** {project_id}
**Generated:** {datetime_iso()}
**Model:** {model}
**Style:** {style or "default"}
**Status:** ✓ Completed

## Prompt

```
{prompt}
```

## Output

- **File:** `{output_path}`
- **Size:** {human_size(_file_size)}

## Metadata

```json
{json.dumps(metadata or {}, indent=2)}
```
"""
    md_path.write_text(md_content, encoding="utf-8")

    # Update any pending plans
    _update_plans(project_id, asset_type, output_path, doc_meta)

    # Mark the plan COMPLETED in the production plan (source of truth)
    if plan_file:
        upsert_production_plan(
            project_id,
            root=root,
            plan_file=plan_file,
            asset_type=asset_type,
            model=model,
            status="COMPLETED",
            source=source,
        )

    return json_path


def _update_plans(
    project_id: str,
    asset_type: str,
    output_path: Path,
    result_meta: dict[str, Any],
    root: Path | None = None,
) -> None:
    """Update any pending plan files to mark them completed."""
    base = Path(root) if root else Path.cwd()
    plan_dir = layout.docs_dir(layout.resolve_project_dir(base, project_id), "plan")
    if not plan_dir.exists():
        return

    for plan_file in plan_dir.glob(f"plan_{asset_type}_*.md"):
        try:
            content = plan_file.read_text(encoding="utf-8")
            # Replace PENDING status with COMPLETED
            content = content.replace("**Status:** PENDING", "**Status:** ✓ COMPLETED")
            content = content.replace("**Status:** pending", "**Status:** ✓ completed")
            # Append result info
            content += (
                f"\n\n## Result\n\n"
                f"- **Output:** `{output_path}`\n"
                f"- **Generated:** {result_meta.get('generated_at', 'unknown')}\n"
            )
            plan_file.write_text(content, encoding="utf-8")
        except Exception:
            pass  # Don't fail if plan update has issues


def detect_project_artifacts(project_id: str, root: Path | None = None) -> dict[str, list[str]]:
    """Detect existing artifacts in a project that can be used as references.

    Reference images live under ``images/`` (in the matching sub-folder),
    so a single scan of the images tree finds everything.

    Args:
        project_id: Project ID
        root: Project root directory

    Returns:
        Dictionary mapping artifact type to list of file paths
    """
    base = Path(root) if root else Path.cwd()
    proj_dir = layout.resolve_project_dir(base, project_id)
    result: dict[str, list[str]] = {
        "images": [],
    }

    for img in layout.discover_images(proj_dir):
        result["images"].append(str(img))

    return result


def get_reference_image_urls(project_id: str, root: Path | None = None) -> list[str]:
    """Get URLs/paths for reference images from a project.

    Returns absolute paths that can be used as reference.
    """
    artifacts = detect_project_artifacts(project_id, root)
    return artifacts.get("images", [])
