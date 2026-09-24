"""Issue #73: image command structured results + explicit output files.

Acceptance criteria covered:
1. ``brandly image --output <path> --json`` writes a validated image to
   exactly <path> and emits a machine-readable success object.
2. A provider response containing a valid image URL (or base64 payload)
   cannot be classified as missing merely because console formatting differs.
3. Provider errors return nonzero status with a structured error object
   (error_code, error_message, task_id when available).
4. Invalid or truncated downloads do not leave a partial file at the
   requested output path.
5. Existing text output for interactive use is preserved when --json is
   not requested.
"""

from __future__ import annotations

import base64
import io as _io
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _png_bytes() -> bytes:
    buf = _io.BytesIO()
    Image.new("RGB", (64, 48), (1, 2, 3)).save(buf, "PNG")
    return buf.getvalue()


def _patch_client(content: bytes | None = None, raise_for_status: bool = False):
    """Patch httpx.AsyncClient so downloads return the given raw bytes."""
    data = content if content is not None else _png_bytes()

    resp = MagicMock()
    resp.content = data
    if raise_for_status:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock())
    else:
        resp.raise_for_status = MagicMock()

    client = MagicMock()
    client.get = AsyncMock(return_value=resp)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)

    return patch("httpx.AsyncClient", return_value=cm)


# ---------------------------------------------------------------------------
# AC1: --output + --json success
# ---------------------------------------------------------------------------


def test_image_output_json_success(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "plates" / "image_1.png"
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.return_value = {
            "url": "https://cdn.example.com/img.png",
            "b64_json": None,
            "revised_prompt": "rev",
            "model": "agnes-image-2.5-flash",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(
            cli,
            [
                "image",
                "-p",
                "a test plate",
                "--output",
                str(out),
                "--json",
            ],
        )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "success"
    assert data["provider_url"] == "https://cdn.example.com/img.png"
    assert data["path"] == str(out)
    assert data["format"] == "PNG"
    assert data["width"] == 64
    assert data["height"] == 48
    assert data["task_id"] is None
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size == (64, 48)
    # Atomic download: no partial/temp file left behind.
    assert not (out.parent / (out.name + ".part")).exists()


# ---------------------------------------------------------------------------
# AC2: URL-only and base64-only provider responses are not "missing"
# ---------------------------------------------------------------------------


def test_url_only_provider_response_succeeds(runner: CliRunner, tmp_path: Path) -> None:
    """A provider response with a valid image URL is a success, not a miss."""
    out = tmp_path / "out" / "url_only.png"
    with patch("brandly_cli.cmd.generation.generate_image") as gen, _patch_client():
        gen.return_value = {
            "url": "https://cdn.example.com/a.png",
            "b64_json": None,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "x", "--output", str(out), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "success"
    assert out.is_file()


def test_b64_only_provider_response_writes_output(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "b64.png"
    b64 = base64.b64encode(_png_bytes()).decode()
    with patch("brandly_cli.cmd.generation.generate_image") as gen:
        gen.return_value = {
            "url": None,
            "b64_json": b64,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "x", "--output", str(out), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "success"
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size == (64, 48)


def test_no_payload_returns_structured_error(runner: CliRunner, tmp_path: Path) -> None:
    """Provider returned neither URL nor b64 → structured no_image error."""
    out = tmp_path / "out.png"
    with patch("brandly_cli.cmd.generation.generate_image") as gen:
        gen.return_value = {
            "url": None,
            "b64_json": None,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        result = runner.invoke(cli, ["image", "-p", "x", "--output", str(out), "--json"])

    assert result.exit_code == 1, result.output
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["error_code"] == "no_image"
    assert not out.exists()


# ---------------------------------------------------------------------------
# AC3: provider failure → structured error, nonzero exit
# ---------------------------------------------------------------------------


def test_provider_failure_structured_error(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "out.png"
    with patch("brandly_cli.cmd.generation.generate_image") as gen:
        gen.side_effect = RuntimeError("agnes down")
        result = runner.invoke(cli, ["image", "-p", "x", "--output", str(out), "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["error_code"] == "provider_error"
    assert "agnes down" in data["error_message"]
    assert data["task_id"] is None
    assert not out.exists()


# ---------------------------------------------------------------------------
# AC4: invalid / truncated downloads never leave a partial final file
# ---------------------------------------------------------------------------


def test_invalid_image_payload_leaves_no_partial_file(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "bad.png"
    with (
        patch("brandly_cli.cmd.generation.generate_image") as gen,
        _patch_client(content=b"this-is-not-an-image"),
    ):
        gen.return_value = {"url": "https://cdn.example.com/bad.png"}
        result = runner.invoke(cli, ["image", "-p", "x", "--output", str(out), "--json"])

    assert result.exit_code == 1, result.output
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["error_code"] in {"invalid_image", "image_download_failed"}
    assert not out.exists()


def test_truncated_png_leaves_no_partial_file(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "trunc.png"
    # Truncate the PNG mid-stream: PIL full-decode must reject it.
    truncated = _png_bytes()[: len(_png_bytes()) // 2]
    with (
        patch("brandly_cli.cmd.generation.generate_image") as gen,
        _patch_client(content=truncated),
    ):
        gen.return_value = {"url": "https://cdn.example.com/t.png"}
        result = runner.invoke(cli, ["image", "-p", "x", "--output", str(out), "--json"])

    assert result.exit_code == 1, result.output
    assert not out.exists()


# ---------------------------------------------------------------------------
# AC5: text mode still works when --json is not requested
# ---------------------------------------------------------------------------


def test_text_mode_preserved_without_json_flag(runner: CliRunner, tmp_path: Path) -> None:
    fake_saved = tmp_path / ".brandly" / "untitled" / "images" / "general" / "img.png"
    with (
        patch("brandly_cli.cmd.generation.generate_image") as gen,
        patch("brandly_cli.cmd.generation._save_artifact") as save,
    ):
        gen.return_value = {
            "url": "https://cdn.example.com/a.png",
            "b64_json": None,
            "revised_prompt": None,
            "model": "m",
            "generated_at": "2026-01-01T00:00:00Z",
        }
        save.return_value = fake_saved
        result = runner.invoke(cli, ["image", "-p", "x"])

    assert result.exit_code == 0, result.output
    assert "Image generated" in result.output
    assert save.called


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
