"""Tests for plan reuse, the production plan (source of truth), keyframe
archiving, and human-in-the-loop gates.

Run under `.venv\\Scripts\\python` (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.utils import (
    _read_production_plan_rows,
    generate_project_id,
    production_plan_path,
    upsert_production_plan,
    write_generation_plan,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Return the .brandly root (new layout: projects at .brandly/{id}/)."""
    return tmp_path / ".brandly"


@pytest.fixture
def runner(project_dir: Path, tmp_path: Path) -> CliRunner:
    """Return a Click test runner pointed at the temp root (where ROOT env is set)."""
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, project_id: str, **overrides: object) -> Path:
    """Write a minimal project.json to disk (.brandly root based)."""
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "id": project_id,
        "name": "Test Project",
        "description": "A test product description for reference workflow",
        "status": "pending",
        "current_phase": "asset",
        "budget": 200,
        "spent": 0,
        "style": "cinematic",
        "shot_count": 3,
        "target_platforms": ["tiktok"],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "phases": {},
    }
    data.update(overrides)
    proj_file.write_text(json.dumps(data))
    return proj_file


def _plan_files(tmp_path: Path, project_id: str, asset_type: str) -> list[Path]:
    return sorted((tmp_path / ".brandly" / project_id / "docs" / "plan")
                  .glob(f"plan_{asset_type}_*.md"))


def _plan_rows(tmp_path: Path, project_id: str) -> dict[str, dict[str, str]]:
    return _read_production_plan_rows(
        production_plan_path(project_id, root=tmp_path)
    )


# ---------------------------------------------------------------------------
# Plan reuse (unchanged config → reuse; changed config → new plan)
# ---------------------------------------------------------------------------


class TestPlanReuse:
    def test_first_run_creates_plan_and_row(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "reuse-1")
        plan, reused = write_generation_plan(
            "reuse-1",
            "video",
            root=tmp_path,
            prompt="a cat",
            model="agnes-video-2.5-flash",
            style="cinematic",
            source="brandly video",
        )
        assert reused is False
        assert plan.name.startswith("plan_video_")
        assert "plan-signature" in plan.read_text(encoding="utf-8")
        row = _plan_rows(tmp_path, "reuse-1")[plan.name]
        assert row["status"] == "PENDING"
        assert row["source"] == "brandly video"

    def test_unchanged_config_reuses_plan(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "reuse-2")
        kwargs = {
            "root": tmp_path,
            "prompt": "a cat",
            "model": "agnes-video-2.5-flash",
            "style": "cinematic",
            "source": "brandly video",
        }
        plan1, reused1 = write_generation_plan("reuse-2", "video", **kwargs)  # type: ignore[arg-type]
        plan2, reused2 = write_generation_plan("reuse-2", "video", **kwargs)  # type: ignore[arg-type]
        assert reused1 is False
        assert reused2 is True
        assert plan1 == plan2
        # No duplicate plan file
        assert len(_plan_files(tmp_path, "reuse-2", "video")) == 1

    def test_changed_config_creates_new_plan(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "reuse-3")
        base = {
            "root": tmp_path,
            "prompt": "a cat",
            "model": "agnes-video-2.5-flash",
            "style": "cinematic",
            "source": "brandly video",
        }
        plan1, _ = write_generation_plan("reuse-3", "video", **base)  # type: ignore[arg-type]
        base["prompt"] = "a dog"  # config changed
        plan2, reused2 = write_generation_plan("reuse-3", "video", **base)  # type: ignore[arg-type]
        assert reused2 is False
        assert plan2 != plan1
        assert len(_plan_files(tmp_path, "reuse-3", "video")) == 2

    def test_failed_status_resets_to_pending_on_reuse(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "reuse-4")
        kwargs = {
            "root": tmp_path,
            "prompt": "a cat",
            "model": "agnes-video-2.5-flash",
            "style": "cinematic",
            "source": "brandly video",
        }
        plan, _ = write_generation_plan("reuse-4", "video", **kwargs)  # type: ignore[arg-type]
        # Simulate a failed generation marking the plan FAILED
        upsert_production_plan(
            "reuse-4",
            root=tmp_path,
            plan_file=str(plan),
            asset_type="video",
            model="agnes-video-2.5-flash",
            status="FAILED",
            source="brandly video",
        )
        assert _plan_rows(tmp_path, "reuse-4")[plan.name]["status"] == "FAILED"
        # Retry with the same config: reuses the plan, back to PENDING
        plan2, reused = write_generation_plan("reuse-4", "video", **kwargs)  # type: ignore[arg-type]
        assert reused is True
        assert plan2 == plan
        assert _plan_rows(tmp_path, "reuse-4")[plan.name]["status"] == "PENDING"


# ---------------------------------------------------------------------------
# Production plan upsert (source of truth)
# ---------------------------------------------------------------------------


class TestUpsertProductionPlan:
    def test_create_then_update_keeps_created_time(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "prod-1")
        path = upsert_production_plan(
            "prod-1",
            root=tmp_path,
            plan_file="plan_video_20260101.md",
            asset_type="video",
            model="agnes-video-2.5-flash",
            status="PENDING",
            source="brandly video",
        )
        assert path.is_file()
        before = _read_production_plan_rows(path)["plan_video_20260101.md"]
        upsert_production_plan(
            "prod-1",
            root=tmp_path,
            plan_file="plan_video_20260101.md",
            asset_type="video",
            model="agnes-video-2.5-flash",
            status="COMPLETED",
            source="brandly video",
        )
        after = _read_production_plan_rows(path)["plan_video_20260101.md"]
        assert after["status"] == "COMPLETED"
        assert after["created"] == before["created"]

    def test_empty_source_keeps_previous_source(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "prod-2")
        upsert_production_plan(
            "prod-2",
            root=tmp_path,
            plan_file="plan_image_1.md",
            asset_type="image",
            model="agnes-image-2.5-flash",
            status="PENDING",
            source="brandly image",
        )
        upsert_production_plan(
            "prod-2",
            root=tmp_path,
            plan_file="plan_image_1.md",
            asset_type="image",
            model="agnes-image-2.5-flash",
            status="COMPLETED",
            source="",  # keep the original source
        )
        row = _plan_rows(tmp_path, "prod-2")["plan_image_1.md"]
        assert row["source"] == "brandly image"
        assert row["status"] == "COMPLETED"

    def test_update_one_row_does_not_touch_others(
        self, tmp_path: Path, project_dir: Path
    ) -> None:
        _write_project(project_dir, "prod-3")
        upsert_production_plan(
            "prod-3",
            root=tmp_path,
            plan_file="plan_a.md",
            asset_type="image",
            model="m1",
            status="PENDING",
            source="brandly image",
        )
        upsert_production_plan(
            "prod-3",
            root=tmp_path,
            plan_file="plan_b.md",
            asset_type="video",
            model="m2",
            status="PENDING",
            source="brandly video",
        )
        upsert_production_plan(
            "prod-3",
            root=tmp_path,
            plan_file="plan_a.md",
            asset_type="image",
            model="m1",
            status="FAILED",
            source="brandly image",
        )
        rows = _plan_rows(tmp_path, "prod-3")
        assert rows["plan_a.md"]["status"] == "FAILED"
        assert rows["plan_b.md"]["status"] == "PENDING"
        assert rows["plan_b.md"]["source"] == "brandly video"


# ---------------------------------------------------------------------------
# Keyframe archiving (video command copies local frames to images/keyframe/)
# ---------------------------------------------------------------------------


class TestKeyframeArchiving:
    def test_video_archives_local_keyframes(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        start = tmp_path / "start_kitchen.png"
        end = tmp_path / "end_exterior.png"
        start.write_bytes(b"\x89PNG\r\n\x1a\nstart")
        end.write_bytes(b"\x89PNG\r\n\x1a\nend")

        fake_result = {
            "video_id": "video-task-kf",
            "url": "https://example.invalid/clip.mp4",
            "status": "queued",
            "progress": 0,
        }
        with patch(
            "brandly_cli.cli.create_video_task", AsyncMock(return_value=fake_result)
        ):
            result = runner.invoke(
                cli,
                [
                    "video",
                    pid,
                    "-p",
                    "kitchen to exterior transition",
                    "--style",
                    "cinematic",
                    "--first-frame",
                    str(start),
                    "--last-frame",
                    str(end),
                    "--no-wait",
                ],
            )
        assert result.exit_code == 0, f"video failed: {result.output}"
        assert "Keyframe archived" in result.output

        kf_dir = project_dir / pid / "images" / "keyframe"
        files = {p.name for p in kf_dir.glob("*.png")}
        assert "start_frame_start_kitchen.png" in files
        assert "end_frame_end_exterior.png" in files
        assert all((kf_dir / n).stat().st_size > 0 for n in files)
        # Keyframe mode resolved and recorded
        assert "Keyframe" in result.output or "keyframe" in result.output

    def test_video_url_frames_not_archived(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake_result = {
            "video_id": "video-task-kf2",
            "url": "https://example.invalid/clip.mp4",
            "status": "queued",
            "progress": 0,
        }
        with patch(
            "brandly_cli.cli.create_video_task", AsyncMock(return_value=fake_result)
        ):
            result = runner.invoke(
                cli,
                [
                    "video",
                    pid,
                    "-p",
                    "transition",
                    "--first-frame",
                    "https://example.invalid/frame.png",
                    "--no-wait",
                ],
            )
        assert result.exit_code == 0, f"video failed: {result.output}"
        kf_dir = project_dir / pid / "images" / "keyframe"
        assert not any(kf_dir.glob("start_frame_*.png"))


# ---------------------------------------------------------------------------
# Human-in-the-loop gates
# ---------------------------------------------------------------------------


class TestHitlGate:
    def test_reference_rejection_writes_note_and_keeps_plan_pending(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake_result = {"url": "https://example.invalid/reference.png", "id": "ref-1"}

        def fake_save(url, project_id, kind, root=None, prompt_hint="", category=None):
            target_dir = root / ".brandly" / project_id / "images" / (category or "general")
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"prop_test_{project_id}.png"
            target.write_bytes(b"\x89PNG\r\n\x1a\nfake")
            return target

        with (
            patch("brandly_cli.cli.generate_image", AsyncMock(return_value=fake_result)),
            patch("brandly_cli.cli._save_artifact", side_effect=fake_save),
        ):
            result = runner.invoke(
                cli,
                [
                    "reference",
                    pid,
                    "--subject-type",
                    "object",
                    "--subject",
                    "Test product",
                ],
                input="n\nproduct looks wrong\n",
            )

        assert result.exit_code == 1
        assert "rejected at the human gate" in result.output
        # Review note written under docs/tmp
        notes = list((project_dir / pid / "docs" / "tmp").glob("review_reference_*.md"))
        assert len(notes) == 1
        assert "product looks wrong" in notes[0].read_text(encoding="utf-8")
        # The plan stays PENDING (not COMPLETED) so a retry reuses it
        row = _plan_rows(tmp_path, pid)
        assert row, "expected a plan row in the production plan"
        statuses = [r["status"] for r in row.values()]
        assert "COMPLETED" not in statuses
        assert "PENDING" in statuses

    def test_reference_approval_completes_plan(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake_result = {"url": "https://example.invalid/reference.png", "id": "ref-2"}

        def fake_save(url, project_id, kind, root=None, prompt_hint="", category=None):
            target_dir = root / ".brandly" / project_id / "images" / (category or "general")
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"prop_test_{project_id}.png"
            target.write_bytes(b"\x89PNG\r\n\x1a\nfake")
            return target

        with (
            patch("brandly_cli.cli.generate_image", AsyncMock(return_value=fake_result)),
            patch("brandly_cli.cli._save_artifact", side_effect=fake_save),
        ):
            result = runner.invoke(
                cli,
                [
                    "reference",
                    pid,
                    "--subject-type",
                    "object",
                    "--subject",
                    "Test product",
                ],
                input="y\ny\n",
            )

        assert result.exit_code == 0, f"reference failed: {result.output}"
        assert "Human gate passed" in result.output
        row = _plan_rows(tmp_path, pid)
        assert row, "expected a plan row in the production plan"
        assert "COMPLETED" in [r["status"] for r in row.values()]
