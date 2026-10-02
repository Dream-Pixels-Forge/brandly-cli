r"""v2 media layout: media and exports never land under ``.brandly/<id>/``.

Issue #117 moved image/video/audio creation to the v2 roots
(``pre-production/<id>/`` and ``production/<id>/videos|audio``), but several
writers and readers were left behind, so real projects end up with
``.brandly/<id>/images|videos|export`` trees that the v2 readers never scan:

- ``brandly reference --image`` imported plates into ``.brandly/<id>/images/``
- ``brandly export`` / ``export-platforms`` / ``thumbnail`` scanned the dead
  legacy media tree and defaulted their outputs to ``.brandly/<id>/export/``
- ``brandly stitch`` defaulted its output to ``.brandly/<id>/export/final.mp4``
- ``ensure_project_tree()`` created ``.brandly/<id>/export/`` on every project

Contract: images → ``pre-production/<id>/<category>/``, videos →
``production/<id>/videos/``, exports → ``production/<id>/export/``.
``.brandly/<id>/`` is project state only (docs/, project.json, cost.json).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from brandly_cli import layout
from brandly_cli.cli import cli
from brandly_cli.project_manager import ProjectData, ProjectManager
from brandly_cli.utils import generate_project_id

PID = "layout-proj"


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(tmp_path: Path, pid: str = PID) -> None:
    pm = ProjectManager(tmp_path)
    asyncio.run(pm.create(ProjectData(id=pid, name="T", description="d")))


def _add_v2_image(tmp_path: Path, pid: str, category: str, name: str) -> Path:
    p = tmp_path / "pre-production" / pid / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return p


def _add_v2_clip(tmp_path: Path, pid: str, name: str) -> Path:
    p = tmp_path / "production" / pid / "videos" / "scenes" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"fake-clip")
    return p


# ---------------------------------------------------------------------------
# ensure_project_tree / export_dir
# ---------------------------------------------------------------------------


def test_ensure_project_tree_puts_export_under_production(tmp_path: Path) -> None:
    layout.ensure_project_tree(tmp_path, PID)
    assert (tmp_path / "production" / PID / "export").is_dir()
    assert not (tmp_path / ".brandly" / PID / "export").exists()


def test_ensure_project_tree_never_creates_brandly_media(tmp_path: Path) -> None:
    layout.ensure_project_tree(tmp_path, PID)
    assert not (tmp_path / ".brandly" / PID / "images").exists()
    assert not (tmp_path / ".brandly" / PID / "videos").exists()
    assert not (tmp_path / ".brandly" / PID / "audio").exists()


def test_export_dir_helper(tmp_path: Path) -> None:
    assert layout.export_dir(tmp_path, PID) == (
        tmp_path / "production" / PID / "export"
    )


# ---------------------------------------------------------------------------
# brandly reference --image imports plates into the v2 images root
# ---------------------------------------------------------------------------


def test_reference_import_writes_plate_to_v2_images_root(
    tmp_path: Path, runner: CliRunner
) -> None:
    pid = generate_project_id()
    _write_project(tmp_path, pid)
    src = tmp_path / "plate.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    result = runner.invoke(
        cli,
        ["reference", pid, "--subject-type", "character", "--subject", "Rebel",
         "--image", str(src)],
    )
    assert result.exit_code == 0, result.output
    images_root = tmp_path / "pre-production" / pid / "character"
    imported = list(images_root.glob("reference_character_*.png"))
    assert imported, f"plate not imported under {images_root}"
    assert not (tmp_path / ".brandly" / pid / "images").exists()


# ---------------------------------------------------------------------------
# brandly export scans the v2 media roots and exports to production/<id>/export
# ---------------------------------------------------------------------------


def test_export_scans_v2_roots_and_writes_to_production_export(
    tmp_path: Path, runner: CliRunner
) -> None:
    _write_project(tmp_path)
    _add_v2_image(tmp_path, PID, "general", "still.png")
    _add_v2_clip(tmp_path, PID, "Scene-01-Shot-1-1.mp4")
    result = runner.invoke(cli, ["export", PID])
    assert result.exit_code == 0, result.output
    out_dir = tmp_path / "production" / PID / "export"
    assert (out_dir / "export-manifest.json").is_file()
    assert (out_dir / "images" / "general" / "still.png").is_file()
    assert (out_dir / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4").is_file()
    assert not (tmp_path / ".brandly" / PID / "export").exists()


# ---------------------------------------------------------------------------
# export-platforms / thumbnail read the v2 media roots
# ---------------------------------------------------------------------------


def test_export_platforms_finds_v2_video_and_outputs_to_production_export(
    tmp_path: Path, runner: CliRunner
) -> None:
    _write_project(tmp_path)
    _add_v2_clip(tmp_path, PID, "final.mp4")
    captured: dict[str, Any] = {}

    def fake_export(video_path, platform, out_dir, **kw):  # noqa: ANN001
        captured["out_dir"] = out_dir
        return {"output_path": str(out_dir / f"final_{platform}.mp4"),
                "duration_seconds": 1.0}

    with patch(
        "brandly_cli.export_platforms.export_for_platform", side_effect=fake_export
    ):
        result = runner.invoke(
            cli, ["export-platforms", PID, "--platforms", "tiktok", "--root",
                  str(tmp_path)]
        )
    assert result.exit_code == 0, result.output
    assert captured["out_dir"] == tmp_path / "production" / PID / "export"


def test_thumbnail_reads_v2_video_and_writes_to_preproduction(
    tmp_path: Path, runner: CliRunner
) -> None:
    _write_project(tmp_path)
    _add_v2_clip(tmp_path, PID, "Scene-01-Shot-1-1.mp4")
    captured: dict[str, Any] = {}

    def fake_thumbs(video_path, output_dir, **kw):  # noqa: ANN001
        captured["output_dir"] = output_dir
        return {"count": 1, "thumbnails": [{"path": str(output_dir / "t.png")}]}

    with patch(
        "brandly_cli.thumbnails.generate_thumbnails", side_effect=fake_thumbs
    ):
        result = runner.invoke(
            cli, ["thumbnail", PID, "--root", str(tmp_path)]
        )
    assert result.exit_code == 0, result.output
    assert captured["output_dir"] == (
        tmp_path / "pre-production" / PID / "general"
    )
    assert not (tmp_path / ".brandly" / PID / "images").exists()


# ---------------------------------------------------------------------------
# brandly stitch / assemble defaults its output to production/<id>/export
# ---------------------------------------------------------------------------


def test_assemble_default_output_under_production_export(
    tmp_path: Path, runner: CliRunner
) -> None:
    _write_project(tmp_path)
    _add_v2_clip(tmp_path, PID, "Scene-01-Shot-1-1-shots.mp4")
    shots_file = tmp_path / "shots.json"
    shots_file.write_text(
        json.dumps([{"id": "Scene-01-Shot-1-1", "prompt": "x", "duration": 5}])
    )
    captured: dict[str, Any] = {}

    def fake_assemble(plan, out, **kw):  # noqa: ANN001
        captured["out"] = out
        return {"output_path": str(out), "duration_seconds": 1.0}

    with patch("brandly_cli.assemble.assemble_project", side_effect=fake_assemble):
        result = runner.invoke(
            cli, ["assemble", PID, "--shots", str(shots_file)]
        )
    assert result.exit_code == 0, result.output
    assert captured["out"] == (
        tmp_path / "production" / PID / "export" / "final.mp4"
    )
    assert not (tmp_path / ".brandly" / PID / "export").exists()

# ---------------------------------------------------------------------------
# brandly publish reads the v2 export/videos roots
# ---------------------------------------------------------------------------


def test_publish_finds_video_in_v2_export(tmp_path: Path, runner: CliRunner) -> None:
    _write_project(tmp_path)
    exported = tmp_path / "production" / PID / "export" / "master_tiktok.mp4"
    exported.parent.mkdir(parents=True, exist_ok=True)
    exported.write_bytes(b"fake-video")

    class FakeAdapter:
        def build_payload(self, video, **kw):  # noqa: ANN001, ANN003
            return {"video": str(video)}

    with patch(
        "brandly_cli.publish.get_adapter", return_value=FakeAdapter()
    ):
        result = runner.invoke(
            cli, ["publish", PID, "--platform", "tiktok", "--dry-run"]
        )
    assert result.exit_code == 0, result.output
    assert "No video found" not in result.output
    assert "master_tiktok.mp4" in result.output

