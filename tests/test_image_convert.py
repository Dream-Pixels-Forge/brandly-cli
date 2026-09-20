"""Tests for the image converter (shrink local reference images to webp/jpeg).

Related: issue #24 ("smaller reference images"), issue #20 (payload bloat).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from brandly_cli.image_convert import (
    DEFAULT_QUALITY,
    convert_image,
    maybe_convert,
    pick_target_format,
)


def _noisy_png(tmp_path: Path, name: str = "plate.png", size: int = 512) -> Path:
    """Create a large (noisy) PNG — noise makes it compress poorly."""
    import random

    random.seed(42)
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            px[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    target = tmp_path / name
    img.save(target, "PNG")
    return target


def _alpha_png(tmp_path: Path, name: str = "alpha.png", size: int = 256) -> Path:
    """Create a PNG with real alpha (checkerboard transparency)."""
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            if (x // 8 + y // 8) % 2 == 0:
                px[x, y] = (255, 0, 0, 255)
            else:
                px[x, y] = (255, 0, 0, 0)
    target = tmp_path / name
    img.save(target, "PNG")
    return target


class TestPickTargetFormat:
    def test_opaque_image_gets_jpeg(self, tmp_path: Path) -> None:
        src = _noisy_png(tmp_path)
        assert pick_target_format(src) == "jpeg"

    def test_alpha_image_gets_webp(self, tmp_path: Path) -> None:
        src = _alpha_png(tmp_path)
        assert pick_target_format(src) == "webp"


class TestConvertImage:
    def test_noisy_png_converts_smaller_to_jpeg(self, tmp_path: Path) -> None:
        src = _noisy_png(tmp_path)
        out = convert_image(src)
        assert out is not None
        assert out.suffix.lower() in (".jpg", ".jpeg")
        assert out != src
        assert out.stat().st_size < src.stat().st_size
        # Source must remain untouched.
        assert src.exists()

    def test_alpha_png_converts_to_webp_keeping_alpha(self, tmp_path: Path) -> None:
        src = _alpha_png(tmp_path)
        out = convert_image(src, min_save=1)
        assert out is not None
        assert out.suffix.lower() == ".webp"
        with Image.open(out) as img:
            assert img.mode == "RGBA"

    def test_already_small_format_passthrough(self, tmp_path: Path) -> None:
        # A tiny PNG below the min-save threshold should not be converted.
        img = Image.new("RGB", (8, 8), (255, 255, 255))
        src = tmp_path / "tiny.png"
        img.save(src, "PNG")
        assert convert_image(src, min_save=10_000) is None

    def test_convert_not_worthwhile_returns_none(self, tmp_path: Path) -> None:
        # A flat PNG is already tiny in PNG; JPEG won't save 10 KB.
        img = Image.new("RGB", (64, 64), (200, 200, 200))
        src = tmp_path / "flat.png"
        img.save(src, "PNG")
        assert convert_image(src) is None

    def test_explicit_format(self, tmp_path: Path) -> None:
        src = _noisy_png(tmp_path)
        out = convert_image(src, fmt="webp")
        assert out is not None
        assert out.suffix.lower() == ".webp"

    def test_corrupt_file_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "broken.png"
        src.write_bytes(b"\x89PNG\r\n\x1a\nnot really a png")
        assert convert_image(src) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert convert_image(tmp_path / "nope.png") is None


class TestMaybeConvert:
    def test_large_png_becomes_smaller_data_url(self, tmp_path: Path) -> None:
        src = _noisy_png(tmp_path, "big.png")
        result = maybe_convert(str(src), threshold_bytes=1024)
        assert result is not None
        assert result.startswith("data:image/")
        # Must be smaller than the raw base64 of the original.
        raw_len = len("data:image/png;base64,") + (src.stat().st_size * 4 // 3 + 3)
        assert len(result) < raw_len

    def test_small_file_returned_as_plain_path(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (16, 16), (10, 10, 10))
        src = tmp_path / "small.png"
        img.save(src, "PNG")
        result = maybe_convert(str(src), threshold_bytes=1024)
        # Below threshold — returned unchanged (no data URL, no conversion).
        assert result == str(src)

    def test_remote_url_passthrough(self) -> None:
        url = "https://example.com/x.png"
        assert maybe_convert(url) == url

    def test_missing_file_passthrough(self, tmp_path: Path) -> None:
        missing = str(tmp_path / "missing.png")
        assert maybe_convert(missing) == missing

    def test_env_disable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = _noisy_png(tmp_path, "big2.png")
        monkeypatch.setenv("BRANDLY_IMAGE_CONVERT", "off")
        assert maybe_convert(str(src), threshold_bytes=1024) == str(src)

    def test_env_bad_value_treated_as_enabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = _noisy_png(tmp_path, "big3.png")
        monkeypatch.setenv("BRANDLY_IMAGE_CONVERT", "yes")
        result = maybe_convert(str(src), threshold_bytes=1024)
        assert result.startswith("data:image/")

    def test_quality_constant_sane(self) -> None:
        assert 50 <= DEFAULT_QUALITY <= 95
