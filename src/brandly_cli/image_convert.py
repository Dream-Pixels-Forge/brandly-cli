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
from pathlib import Path
from typing import Any

from PIL import Image

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
