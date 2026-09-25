"""G7 PR 1 (issue #98): brand-kit model + persistence + prompt-layer lock.

The kit is stored **project-level** (``.brandly/<project>/brand.json``) —
never in user config or ``.env`` (F2 rule, DEV-G7-001). This PR ships the
model, the ``brandly brand`` command group, and the prompt-layer lock
(:func:`brand_constraints` / :func:`apply_brand_lock`); the gate-layer claim
check and the export-layer logo overlay ship in G7 PR 2.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from brandly_cli.constants import STYLE_PRESET_OPTIONS
from brandly_cli.style_presets import MediaMode, apply_style_preset

#: Version of the on-disk ``brand.json`` schema.
SCHEMA_VERSION = 1

#: Where the kit lives inside a project directory.
BRAND_FILE = "brand.json"

_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")

#: Valid logo overlay corners (used by the G7 PR 2 ffmpeg composite).
OVERLAY_CORNERS: tuple[str, ...] = (
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
)


class BrandLockConflictError(ValueError):
    """A requested style conflicts with the kit's ``style_lock``."""


@dataclass(frozen=True)
class OverlaySpec:
    """Where a logo lands on export (consumed by G7 PR 2)."""

    corner: str = "bottom-right"
    safe_zone: float = 0.1
    opacity: float = 1.0


@dataclass(frozen=True)
class BrandKit:
    """A brand kit: palette, claim allowlist, pinned style, logo, overlay."""

    colors: tuple[str, ...]
    claims: tuple[str, ...]
    style_lock: str
    logo: str = ""
    overlay: OverlaySpec = field(default_factory=OverlaySpec)
    version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_overlay(raw: Any) -> OverlaySpec:
    spec = OverlaySpec()
    if isinstance(raw, dict):
        corner = str(raw.get("corner", spec.corner))
        safe_zone = float(raw.get("safe_zone", spec.safe_zone))
        opacity = float(raw.get("opacity", spec.opacity))
        spec = OverlaySpec(corner=corner, safe_zone=safe_zone, opacity=opacity)
    if spec.corner not in OVERLAY_CORNERS:
        raise ValueError(f"overlay.corner must be one of {OVERLAY_CORNERS}")
    if not 0 < spec.safe_zone <= 0.3:
        raise ValueError("overlay.safe_zone must be in (0, 0.3]")
    if not 0 <= spec.opacity <= 1:
        raise ValueError("overlay.opacity must be in [0, 1]")
    return spec


def parse_brand_kit(raw: dict[str, Any]) -> BrandKit:
    """Parse a raw ``brand.json`` dict; raise ``ValueError`` when invalid."""
    colors = [str(c).strip() for c in raw.get("colors", [])]
    if not colors:
        raise ValueError("brand kit needs at least one color")
    for color in colors:
        if not _HEX_RE.match(color):
            raise ValueError(f"invalid hex color: {color!r}")
    claims = [str(c).strip() for c in raw.get("claims", []) if str(c).strip()]
    if not claims:
        raise ValueError("brand kit needs at least one claim")
    style_lock = str(raw.get("style_lock", ""))
    if style_lock not in STYLE_PRESET_OPTIONS:
        raise ValueError(f"style_lock must be one of {STYLE_PRESET_OPTIONS}, got {style_lock!r}")
    return BrandKit(
        colors=tuple(colors),
        claims=tuple(claims),
        style_lock=style_lock,
        logo=str(raw.get("logo", "")),
        overlay=_parse_overlay(raw.get("overlay")),
        version=int(raw.get("version", SCHEMA_VERSION)),
    )


def save_brand_kit(proj_dir: Path, kit: BrandKit) -> Path:
    """Write the kit to ``<proj_dir>/brand.json`` (project-level only)."""
    path = Path(proj_dir) / BRAND_FILE
    path.write_text(
        json.dumps(kit.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_brand_kit(proj_dir: Path) -> BrandKit | None:
    """Read the project's kit; ``None`` when no ``brand.json`` exists.

    Raises ``ValueError`` when the file exists but is malformed
    (fail-closed — a corrupt kit must not pass silently).
    """
    path = Path(proj_dir) / BRAND_FILE
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return parse_brand_kit(raw)


def verify_kit(kit: BrandKit, proj_dir: Path | None = None) -> list[str]:
    """Deterministic verification; returns the issue list (empty = valid).

    Structural validation already happened in :func:`parse_brand_kit` — this
    adds the semantic checks that need on-disk context (logo resolvability).
    """
    issues: list[str] = []
    if kit.logo:
        target = Path(kit.logo)
        if not target.is_absolute() and proj_dir is not None:
            target = Path(proj_dir) / target
        if not target.is_file():
            issues.append(f"logo not found: {kit.logo}")
    return issues


def brand_constraints(kit: BrandKit) -> str:
    """The prompt-layer brand lock: palette + claims + third-party ban."""
    palette = ", ".join(kit.colors)
    claims = " / ".join(kit.claims)
    lines = [
        "\n\nBrand lock",
        f"- Palette: {palette} — keep these colors dominant in every frame",
        f'- On-screen copy is restricted to: "{claims}"',
        "- No third-party logos, trademarks, or watermarks",
    ]
    if kit.logo:
        lines.append("- Use only the provided brand mark for any logo")
    return "\n".join(lines)


def apply_brand_lock(
    prompt: str,
    kit: BrandKit,
    *,
    style: str | None = None,
    media: MediaMode = "video",
) -> str:
    """Apply the pinned style preset, then append the brand lock.

    Raises :class:`BrandLockConflictError` when the requested style disagrees with
    ``kit.style_lock`` (DEV-G7-002 — fail closed, never blend styles).
    """
    if style is not None and style != "none" and style != kit.style_lock:
        raise BrandLockConflictError(
            f"style {style!r} conflicts with brand kit style_lock {kit.style_lock!r}"
        )
    out = apply_style_preset(prompt, kit.style_lock, media=media)
    return out + brand_constraints(kit)
