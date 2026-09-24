"""File I/O, timestamps, IDs and misc pure helpers (utils split, P1-5).

Half of the former kitchen-sink ``utils.py``: JSON I/O, downloads,
timestamps, filename sanitizers, project-ID helpers and skill/sheet
discovery. The planning half lives in ``planning.py``; ``utils.py`` keeps
re-export shims for compatibility (deprecated).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from rich.console import Console

from brandly_cli import layout

#: Directory of the installed brandly_cli package — pip installs carry the
#: bundled skills here even without a repo-level ``skills/`` folder.
__package_dir__ = Path(__file__).resolve().parent

_console = Console()  # used only for save_artifact warning output


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
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
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


def find_skills_directory(root: Path | None = None) -> Path:
    """Find the skills directory.

    Checks multiple locations, in priority order:
    1. ./skills/ (project-local — wins so users can override/extend)
    2. <root>/skills/ (explicit root)
    3. ~/.qwen/skills/ (user-level)
    4. ~/.agents/skills/ (agents directory)
    5. the skills shipped inside the installed brandly-cli package
       (pip installs carry no repo-level ``skills/`` folder)

    Falls back to ``./skills`` (which may not exist) when nothing matches.
    """
    candidates = [
        Path("./skills"),
        Path(root / "skills") if root else Path("./skills"),
        Path.home() / ".qwen" / "skills",
        Path.home() / ".agents" / "skills",
        __package_dir__ / "skills",
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


_now_iso = now_iso


# ---------------------------------------------------------------------------
# Artifact persistence (moved out of cli.py — P2-8)
# ---------------------------------------------------------------------------


def save_artifact(
    url: str,
    project_id: str,
    type_label: str,
    *,
    root: Path,
    prompt_hint: str = "",
    category: str | None = None,
    filename: str | None = None,
) -> Path | None:
    """Download a generated asset and save it under
    .brandly/{project_id}/{images|videos|audio}/{category}/.

    ``category`` routes the file into a sub-folder (e.g. 'scenes' for video,
    'prop' for object references, 'soundtrack' for music). Omit it to use
    the 'general' default.

    ``filename`` overrides the default ``<type>_<timestamp>_<hint>`` name (used
    for the deterministic ``Scene-XX-Shot-X-Y.mp4`` clip convention).
    """
    if not url:
        return None
    media_category = category if category else "general"
    artifacts_dir = layout.resolve_media_root(root, project_id, type_label) / media_category
    ext = Path(url.split("?")[0]).suffix or (".mp3" if type_label == "audio" else "")
    if not ext:
        ext = ".bin"
    ts = now_iso().replace(":", "-").replace(".", "_")
    hint = sanitize_filename(prompt_hint)[:20] if prompt_hint else ""
    fname = filename or f"{type_label}_{ts}_{hint}{ext}"
    dest = artifacts_dir / fname
    import asyncio

    try:
        asyncio.run(download_file(url, dest))
        return dest
    except Exception as e:
        _console.print(f"[yellow]⚠ Could not save artifact: {e}[/yellow]")
        return None


class ImageFetchError(RuntimeError):
    """Raised when an image cannot be fetched and validated into the requested path."""


def fetch_image_atomic(
    url: str | None,
    dest_path: Path,
    *,
    b64_json: str | None = None,
) -> dict[str, Any]:
    """Atomically fetch, validate, and save a provider image to ``dest_path``.

    Exactly one of ``url`` or ``b64_json`` must be provided:

    - ``url``: download the payload (redirects followed).
    - ``b64_json``: base64-decode the provider's inline payload.

    The payload is written to a sibling ``<name>.part`` file, fully decoded
    through PIL (rejecting truncated or non-image data), then atomically
    renamed to ``dest_path``. On any failure the ``.part`` file is removed,
    so a partial file never appears at the requested path (issue #73).

    Returns ``{"path", "format", "width", "height"}`` on success and raises
    :class:`ImageFetchError` on failure.
    """
    import base64
    import io as _io

    from PIL import Image

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")

    try:
        if url:
            import asyncio

            import httpx

            async def _dl(u: str) -> bytes:
                async with httpx.AsyncClient(timeout=300) as client:
                    resp = await client.get(u, follow_redirects=True)
                    resp.raise_for_status()
                    return resp.content

            raw = asyncio.run(_dl(url))
        elif b64_json:
            try:
                raw = base64.b64decode(b64_json)
            except Exception as e:
                raise ImageFetchError(f"invalid base64 payload: {e}") from e
        else:
            raise ImageFetchError("one of url or b64_json is required")

        # Validate: full PIL decode — catches truncated, corrupt, or non-image
        # payloads before anything is written to the requested path.
        im = Image.open(_io.BytesIO(raw))
        im.load()

        tmp.write_bytes(raw)
        tmp.replace(dest)
        return {
            "path": dest,
            "format": im.format or "unknown",
            "width": im.size[0],
            "height": im.size[1],
        }
    except ImageFetchError:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise ImageFetchError(f"could not fetch/validate image into {dest.name}: {e}") from e
