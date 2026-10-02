"""Image converter — shrink local reference images to smaller formats.

Agnes models consume images as ``data:`` URLs (OpenAI-compatible API), so
both JPEG and WebP are accepted as standard image MIME types. JPEG gives
the smallest universally-safe payload for opaque images; WebP is used when
the source has alpha transparency (JPEG would destroy it).

Conversion only happens when it actually saves space (>= ``min_save`` bytes)
and can be disabled with ``BRANDLY_IMAGE_CONVERT=off``.

Related issues: #24 (create timeouts from multi-MB reference plates),
#20 (payload bloat from auto-injected references).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from brandly_cli import layout

# Only bother converting when this many bytes (or more) are saved.
DEFAULT_MIN_SAVE = 10 * 1024
# Files below this size are left alone entirely.
DEFAULT_THRESHOLD = 256 * 1024
DEFAULT_QUALITY = 85

_MIN_JPEG_SAVE = DEFAULT_MIN_SAVE
_MIN_WEBP_SAVE = DEFAULT_MIN_SAVE

_FORMAT_BY_EXTENSION = {
    ".png": None,  # decide by alpha content
    ".bmp": "jpeg",
    ".tiff": "jpeg",
    ".tif": "jpeg",
    ".gif": "webp",
}

# HQ reference split: keep a small working JPG in the category folder and
# archive the high-quality original under pre-production/<id>/hq/.
HQ_MAX_DIM = 1280
HQ_QUALITY = 80
HQ_MIN_BYTES = 256 * 1024


def pick_target_format(src: Path | str) -> str | None:
    """Pick the best smaller format for ``src``.

    - Images with alpha → ``webp`` (keeps transparency)
    - Opaque images → ``jpeg`` (smallest widely-accepted format)
    - ``None`` when the file is not a convertible image.
    """
    p = Path(src)
    try:
        with Image.open(p) as img:
            if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
                return "webp"
            return "jpeg"
    except Exception:
        return None


def convert_image(
    src: Path | str,
    *,
    fmt: str | None = None,
    quality: int = DEFAULT_QUALITY,
    min_save: int = DEFAULT_MIN_SAVE,
) -> Path | None:
    """Convert ``src`` to a smaller webp/jpeg copy next to the original.

    Args:
        fmt: Target format ("webp" or "jpeg"); None = auto-pick.
        quality: Encoder quality (1-95).
        min_save: Minimum byte savings for the conversion to be worthwhile.

    Returns:
        Path of the converted file, or None when conversion is not possible
        or does not save at least ``min_save`` bytes. The source file is
        never modified.
    """
    p = Path(src)
    if not p.is_file():
        return None

    target_fmt = (fmt or pick_target_format(p) or "").lower()
    if target_fmt not in ("webp", "jpeg"):
        return None

    suffix = ".webp" if target_fmt == "webp" else ".jpg"
    dest = p.with_suffix(suffix)
    if dest == p:
        return None

    try:
        with Image.open(p) as source_img:
            img: Any = source_img
            if target_fmt == "jpeg":
                if img.mode in ("RGBA", "LA", "P", "PA"):
                    img = img.convert("RGBA")
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(dest, "JPEG", quality=quality, optimize=True)
            else:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
                img.save(dest, "WEBP", quality=quality, method=6)
    except Exception:
        # Never fail generation because of a conversion problem — clean up
        # any partial output and let the caller send the original file.
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    saved = p.stat().st_size - dest.stat().st_size
    if saved < min_save:
        try:
            dest.unlink()
        except OSError:
            pass
        return None
    return dest


def _encode_data_url(path: Path) -> str:
    import base64
    import mimetypes

    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def maybe_convert(
    path_or_url: str,
    *,
    threshold_bytes: int = DEFAULT_THRESHOLD,
    quality: int = DEFAULT_QUALITY,
) -> str:
    """Convert a local image to webp/jpeg when it is large enough to matter.

    - HTTP(S) URLs are returned unchanged.
    - Files below ``threshold_bytes`` are returned unchanged.
    - When conversion saves space, a ``data:`` URL of the converted copy is
      returned (ready to send to the API).
    - Anything else (missing files, corrupt images, disabled via env) is
      returned unchanged.

    Set ``BRANDLY_IMAGE_CONVERT=off`` to disable conversion entirely.
    """
    if os.getenv("BRANDLY_IMAGE_CONVERT", "").strip().lower() == "off":
        return path_or_url
    if path_or_url.startswith(("http://", "https://", "data:")):
        return path_or_url

    p = Path(path_or_url)
    if not p.is_file():
        return path_or_url
    try:
        if p.stat().st_size < threshold_bytes:
            return path_or_url
    except OSError:
        return path_or_url

    converted: Path | None = convert_image(p, quality=quality)
    if converted is None:
        return path_or_url

    saved = p.stat().st_size - converted.stat().st_size
    print(
        f"[convert] {p.name} ({p.stat().st_size // 1024}KB) -> "
        f"{converted.name} ({converted.stat().st_size // 1024}KB, "
        f"saved {saved // 1024}KB)"
    )
    return _encode_data_url(converted)


# ---------------------------------------------------------------------------
# HQ reference split — small working JPG + archived high-quality master
# ---------------------------------------------------------------------------


def _hq_enabled() -> bool:
    """The HQ reference split is on unless ``BRANDLY_HQ_REFS=off``."""
    return os.getenv("BRANDLY_HQ_REFS", "").strip().lower() != "off"


def _is_large(path: Path, max_dim: int, min_bytes: int) -> bool:
    """True when the image is big enough to be worth splitting.

    "Large" means either at least ``min_bytes`` on disk, or a long side over
    ``max_dim`` pixels — either way the small JPG is a meaningful win.
    """
    try:
        if path.stat().st_size >= min_bytes:
            return True
        with Image.open(path) as im:
            w, h = im.size
        return max(w, h) > max_dim
    except Exception:
        return False


def _write_small_jpg(src: Path, dest: Path, max_dim: int, quality: int) -> bool:
    """Write a down-scaled RGB JPG (long side <= ``max_dim``) to ``dest``.

    Returns True on success; never leaves a partial file behind on failure.
    """
    try:
        with Image.open(src) as im:
            img = im.convert("RGB")
            w, h = img.size
            scale = max_dim / max(w, h)
            if scale < 1:
                img = img.resize(
                    (max(1, int(w * scale)), max(1, int(h * scale))),
                    Image.Resampling.LANCZOS,
                )
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, "JPEG", quality=quality, optimize=True)
        return True
    except Exception:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def ensure_hq_split(
    image: Path | str,
    hq_root: Path | str,
    images_root: Path | str,
    *,
    max_dim: int = HQ_MAX_DIM,
    quality: int = HQ_QUALITY,
    min_bytes: int = HQ_MIN_BYTES,
    dry_run: bool = False,
) -> dict[str, str] | None:
    """Split one reference image into a small JPG + an HQ master under ``hq/``.

    * Copies the high-quality original into ``hq_root/<category>/<name>``
      (the master is never modified or deleted).
    * Writes a small down-scaled JPG next to the original in the category
      folder — that small JPG becomes the working reference.
    * Removes the now-redundant large original from the category folder *only*
      once it has been safely archived in ``hq/`` and the small JPG written.

    No-op (returns None) when the feature is disabled, the file is missing,
    already lives under ``hq/``, is not under ``images_root``, or is not
    large enough to be worth splitting.
    """
    if not _hq_enabled():
        return None
    image = Path(image)
    if not image.is_file():
        return None
    if not _is_large(image, max_dim, min_bytes):
        return None

    # Resolve the containing category (top-level folder under the images root).
    base = Path(images_root).resolve()
    try:
        rel = image.resolve().relative_to(base)
    except ValueError:
        return None  # not under this images root (e.g. a legacy v1 plate)
    if not rel.parts or rel.parts[0] == layout.HQ_DIRNAME:
        return None
    category = rel.parts[0] if len(rel.parts) > 1 else "general"

    hq_root = Path(hq_root)
    master = hq_root / category / image.name
    small = image.parent / (image.stem + ".jpg")

    if not dry_run:
        master.parent.mkdir(parents=True, exist_ok=True)
        if not master.exists():
            shutil.copy2(image, master)
        wrote_small = _write_small_jpg(image, small, max_dim, quality)
        if wrote_small and small != image:
            # Original is preserved in hq/; drop the big source so only the
            # small JPG remains as the live reference in the category folder.
            image.unlink(missing_ok=True)

    return {
        "image": str(image),
        "master": str(master),
        "small": str(small),
        "category": category,
    }


def optimize_references(
    root: str | Path,
    project_id: str,
    *,
    max_dim: int = HQ_MAX_DIM,
    quality: int = HQ_QUALITY,
    min_bytes: int = HQ_MIN_BYTES,
    dry_run: bool = False,
) -> list[dict[str, str]]:
    """Split every large reference image found on the project's directory.

    Walks the reference plates discovered under ``pre-production/<id>/``
    (the ``hq/`` folder is already excluded by discovery) and applies
    :func:`ensure_hq_split` to each. Idempotent and non-destructive; returns a
    summary list (empty when nothing needed splitting or when disabled).
    """
    if not _hq_enabled():
        return []
    images_root = layout.resolve_media_root(Path(root), project_id, "images")
    hq_root = layout.hq_dir(Path(root), project_id)
    results: list[dict[str, str]] = []
    for img in layout.discover_project_plates(root, project_id):
        res = ensure_hq_split(
            img,
            hq_root,
            images_root,
            max_dim=max_dim,
            quality=quality,
            min_bytes=min_bytes,
            dry_run=dry_run,
        )
        if res is not None:
            results.append(res)
    return results
