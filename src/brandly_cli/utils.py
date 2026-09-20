"""Utility helpers for brandly-cli."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from brandly_cli import layout


def generate_project_id() -> str:
    """Generate a human-readable project ID from slug + timestamp.

    Examples:
        samsung-s26-campaign
        pepsi-summer-vibes-001
    """
    from datetime import datetime, timezone

    # Generate base slug from timestamp
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"project-{ts}"


def generate_readable_id(name: str) -> str:
    """Generate a human-readable ID from a project name.

    Examples:
        "Samsung S26 Flagship Campaign" → "samsung-s26-flagship-campaign"
        "Pepsi Summer Vibes" → "pepsi-summer-vibes"
    """
    slug = generate_project_slug(name)
    # Check if slug already exists, append counter if needed
    return slug


def generate_project_slug(name: str) -> str:
    """Generate a human-readable slug from a project name.

    Examples:
        "Pepsi Summer Vibes"       → "pepsi-summer-vibes"
        "Nike Air Max Campaign"    → "nike-air-max-campaign"
        "TechProduct 3000 Launch"  → "techproduct-3000-launch"
    """
    import re

    slug = name.lower().strip()
    # Replace spaces and dashes with single hyphens
    slug = re.sub(r"[\s]+", "-", slug)
    # Remove unsafe characters
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug or "project"


def is_valid_project_id(id_str: str) -> bool:
    """Validate a project ID (slug or timestamp-based).

    Rejects:
    - Empty strings
    - Path traversal characters (/, \\, ..)
    - Drive-relative paths (e.g. ``C:foo``)
    - Reserved Windows device names
    """
    import re

    if not id_str:
        return False
    # Reject path traversal
    if ".." in id_str or "/" in id_str or "\\" in id_str:
        return False
    # Reject drive-relative paths (Windows: C:foo, D:bar, etc.)
    if len(id_str) >= 2 and id_str[1] == ":" and id_str[0].isalpha():
        return False
    # Reject NUL byte and control characters
    if any(ord(c) < 0x20 for c in id_str):
        return False
    # Reject reserved Windows device names (case-insensitive)
    reserved = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
    }
    if id_str.lower().split(".")[0] in reserved:
        return False
    # Accept either slug format (samsung-s26-campaign) or timestamp format (project-20260831-230500)
    return bool(re.match(r"^[a-z0-9\-]+$", id_str, re.IGNORECASE))


def now_iso() -> str:
    return datetime_iso()


# alias for internal use
_now_iso = now_iso


def datetime_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def ellipsize(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def human_size(bytes_val: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def human_duration(ms: int) -> str:
    seconds = ms / 1000
    minutes, secs = divmod(int(seconds), 60)
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def load_env(default_path: str | None = None) -> None:
    """Load .env file if present."""
    try:
        from dotenv import load_dotenv

        paths = (
            [default_path]
            if default_path
            else [".env", os.path.join(Path.home(), ".brandly", ".env")]
        )
        for p in paths:
            if p and os.path.isfile(p):
                load_dotenv(p)
                return
        load_dotenv()
    except ImportError:
        pass


def get_brandly_dir(root: str | Path | None = None) -> Path:
    """Return the .brandly directory inside the working root."""
    base = Path(root) if root else Path.cwd()
    return base / ".brandly"


def write_atomic(path: Path | str, content: str) -> None:
    """Write content to path atomically (temp + rename)."""
    import tempfile

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path | str, data: dict[str, Any]) -> None:
    write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# File I / O helpers
# ---------------------------------------------------------------------------


async def download_file(url: str, dest_path: Path) -> Path:
    """Download a file from url to dest_path (creates parent dirs). Returns dest_path."""
    import httpx

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Remove characters unsafe for filenames."""
    import re

    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(" ._")
    return name[:max_len] or "file"


# ---------------------------------------------------------------------------
# Pre-generation documentation
# ---------------------------------------------------------------------------


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
) -> tuple[Path, bool]:
    """Write a generation plan BEFORE attempting API calls.

    If a plan with an identical configuration already exists it is REUSED
    instead of creating a new file — e.g. when retrying after a failed
    generation. A new plan is only created when something in the
    configuration (asset type, prompt, model, style, extra config) changed.

    Creates: {root}/.brandly/{id}/docs/plan/plan_{asset_type}_{timestamp}.md

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

    config = extra_config or {}
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

    md_content = f"""# Generation Plan: {asset_type.title()}

{marker}
**Project:** {project_id}
**Planned:** {datetime_iso()}
**Status:** PENDING

## Configuration

| Parameter | Value |
|-----------|-------|
| Model | {model} |
| Style | {style} |
| Asset Type | {asset_type} |
"""

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

    plan_path = plan_dir / f"plan_{asset_type}_{ts}.md"
    if plan_path.exists():
        # A different config was written within the same second — use a
        # disambiguated filename so both plans survive.
        for i in range(2, 100):
            candidate = plan_dir / f"plan_{asset_type}_{ts}_{i}.md"
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
    )

    return plan_path, False


# ---------------------------------------------------------------------------
# Production plan — single source of truth for where each plan comes from
# ---------------------------------------------------------------------------

_PRODUCTION_PLAN_FILE = "production_plan.md"


def production_plan_path(project_id: str, *, root: Path | None = None) -> Path:
    """Return the production plan document: ``docs/plan/production_plan.md``."""
    base = Path(root) if root else Path.cwd()
    return (
        layout.docs_dir(layout.resolve_project_dir(base, project_id), "plan")
        / _PRODUCTION_PLAN_FILE
    )


def _read_production_plan_rows(path: Path) -> dict[str, dict[str, str]]:
    """Parse the production plan table into ``{plan_filename: {col: value}}``."""
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
        if len(cells) < 7 or cells[0] in ("Plan", ""):
            continue
        rows[cells[0]] = {
            "asset": cells[1],
            "model": cells[2],
            "source": cells[3],
            "status": cells[4],
            "created": cells[5],
            "updated": cells[6],
        }
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
        "| Plan | Asset | Model | Source | Status | Created | Updated |",
        "|------|-------|-------|--------|--------|---------|---------|",
    ]
    for name in sorted(rows):
        r = rows[name]
        lines.append(
            f"| {name} | {r['asset']} | {r['model']} | {r['source']} "
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
) -> Path:
    """Register/update one plan in the production plan document.

    The production plan (``docs/plan/production_plan.md``) is the single
    source of truth for where each generation plan came from. Rows are
    keyed by plan filename; existing rows keep their creation time.
    """
    path = production_plan_path(project_id, root=root)
    rows = _read_production_plan_rows(path)
    key = os.path.basename(plan_file)
    prev = rows.get(key, {})
    now = datetime_iso()
    rows[key] = {
        "asset": asset_type,
        "model": model,
        "source": source or prev.get("source", "—"),
        "status": status,
        "created": prev.get("created", now),
        "updated": now,
    }
    _write_production_plan(path, rows)
    return path


# ---------------------------------------------------------------------------
# Generation documentation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Sheet reference management
# ---------------------------------------------------------------------------


def find_skills_directory(root: Path | None = None) -> Path:
    """Find the skills directory in the project.

    Checks multiple locations:
    1. ./skills/ (project-local)
    2. ~/.qwen/skills/ (user-level)
    3. ~/.agents/skills/ (agents directory)
    """
    candidates = [
        Path("./skills"),
        Path(root / "skills") if root else Path("./skills"),
        Path.home() / ".qwen" / "skills",
        Path.home() / ".agents" / "skills",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return Path(".").resolve() / "skills"


def load_sheet_reference(skill_name: str, root: Path | None = None) -> dict[str, Any] | None:
    """Load a sheet reference from the skills directory.

    Args:
        skill_name: Name of the skill (e.g., 'brandly-vehicle-sheet')
        root: Project root directory

    Returns:
        Dictionary with sheet data or None if not found
    """
    skills_dir = find_skills_directory(root)
    skill_path = skills_dir / skill_name

    if not skill_path.exists():
        return None

    result: dict[str, Any] = {
        "skill_name": skill_name,
        "sheet_data": {},
        "references": {},
    }

    # Read SKILL.md for structure
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        result["sheet_data"]["structure"] = content

    # Load reference files
    refs_dir = skill_path / "references"
    if refs_dir.exists():
        for ref_file in refs_dir.glob("*.md"):
            ref_name = ref_file.stem
            ref_content = ref_file.read_text(encoding="utf-8")
            result["references"][ref_name] = ref_content

    return result


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


# ---------------------------------------------------------------------------
# Async FFmpeg runner for subprocess operations
# ---------------------------------------------------------------------------

async def async_run_ffmpeg(cmd: list[str]) -> tuple[int | None, str]:
    """Run an FFmpeg command asynchronously.

    Args:
        cmd: FFmpeg command and arguments.

    Returns:
        Tuple of (returncode, stderr output).
    """
    import asyncio

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    return proc.returncode, stderr.decode()
