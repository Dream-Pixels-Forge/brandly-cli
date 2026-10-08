"""Final verification test for F2: Reference injection fix (#245, #252).

This test demonstrates that the fix works for the exact scenario described:
- asset phase warns "No primary reference" despite approved reference in `pre-production/` + `primary_reference` in `project.json`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli.cli import cli


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path / ".brandly"


@pytest.fixture
def runner(project_dir: Path, tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, project_id: str, **overrides: object) -> Path:
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "id": project_id,
        "name": "Test Project",
        "description": "A test product description",
        "status": "pending",
        "current_phase": "asset",
        "budget": 200,
        "spent": 0,
        "style": "cinematic",
        "shot_count": 1,
        "target_platforms": ["tiktok"],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "phases": {},
    }
    data.update(overrides)
    proj_file.write_text(json.dumps(data))
    return proj_file


def _add_image_to_preproduction(tmp_path: Path, project_id: str, category: str, name: str) -> Path:
    """Add an image to the v2 pre-production location."""
    d = tmp_path / "pre-production" / project_id / "images" / category
    d.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (16, 16), (10, 10, 10))
    p = d / name
    img.save(p, "PNG")
    return p


def _ensure_plan(tmp_path: Path, project_id: str) -> None:
    """Write a minimal production plan so brandly video passes its gate."""
    plan_dir = tmp_path / ".brandly" / project_id / "docs" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "production_plan.md").write_text(
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


class TestF2ReferenceInjectionFix:
    """Final verification that F2 fixes the reference injection issue."""

    def test_f2_fixes_reference_warning_with_preproduction_reference(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """Test that when project has primary_reference pointing to an image in pre-production/,
        the asset phase does NOT warn 'No primary reference'.
        This verifies the fix for issues #245 and #252.
        """
        # Setup: create project
        _write_project(project_dir, "test-project")

        # Add a reference image to the CORRECT pre-production location
        # This simulates having an "approved reference in pre-production/"
        ref_img = _add_image_to_preproduction(tmp_path, "test-project", "location", "reference_location_final.jpg")

        # Set up project.json with primary_reference pointing to this image
        # This simulates having "primary_reference in project.json"
        project_json = project_dir / "test-project" / "project.json"
        project_data = json.loads(project_json.read_text())
        project_data["primary_reference"] = {
            "subject_type": "location",
            "skill": "location",
            "subject": "Final Test Location",
            "image_path": str(ref_img),  # Correct path to the image in pre-production/
            "source_url": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "model": "test",
            "style_preset": "cinematic",
        }
        project_json.write_text(json.dumps(project_data, indent=2))

        # Verify our setup is correct
        assert ref_img.exists(), "Reference image should exist in pre-production/"
        assert ref_img.parent == tmp_path / "pre-production" / "test-project" / "images" / "location"

        # Ensure we have a production plan (needed for video generation)
        _ensure_plan(tmp_path, "test-project")

        # Now test that video generation correctly detects the reference
        # and does NOT show the "No primary reference" warning
        with patch(
            "brandly_cli.cmd.generation.create_video_task",
            return_value={"id": "test-task", "status": "pending"},
        ), patch(
            "brandly_cli.cmd.generation.poll_video",
            return_value={"url": "http://example.com/video.mp4", "status": "completed"},
        ):
            # Run video generation
            result = runner.invoke(
                cli,
                [
                    "video",
                    "test-project",
                    "-p",
                    "Test video for F2 verification",
                    "--no-wait",
                    "--no-gate",
                ],
            )

            # The key verification: should NOT see "No primary reference" warning
            # Because we HAVE a valid reference in pre-production/ with primary_reference in project.json
            assert "No primary reference" not in result.output, (
                f"Unexpected 'No primary reference' warning in output:\n{result.output}"
            )

            # Additional verification: we should see that reference images were found
            # (This confirms our reference detection is working)
            assert "Reference images: 1" in result.output, (
                f"Expected to find reference images, but didn't see 'Reference images: 1' in output:\n{result.output}"
            )

    def test_f2_still_shows_warning_when_no_reference_exists(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """Test that when there is genuinely NO reference available,
        the warning still appears correctly (we didn't break the error case).
        """
        # Setup: create project with NO reference images
        _write_project(project_dir, "test-project-no-ref")

        # Do NOT add any reference images to pre-production/

        # But let's say project.json claims there is a reference (with fake path)
        project_json = project_dir / "test-project-no-ref" / "project.json"
        project_data = json.loads(project_json.read_text())
        project_data["primary_reference"] = {
            "subject_type": "location",
            "skill": "location",
            "subject": "Test Location",
            "image_path": "/fake/path/that/does/not/exist.jpg",
            "source_url": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "model": "test",
            "style_preset": "cinematic",
        }
        project_json.write_text(json.dumps(project_data, indent=2))

        # Ensure we have a production plan
        _ensure_plan(tmp_path, "test-project-no-ref")

        # Now test that video generation correctly warns about missing reference
        with patch(
            "brandly_cli.cmd.generation.create_video_task",
            return_value={"id": "test-task", "status": "pending"},
        ), patch(
            "brandly_cli.cmd.generation.poll_video",
            return_value={"url": "http://example.com/video.mp4", "status": "completed"},
        ):
            # Run video generation
            result = runner.invoke(
                cli,
                [
                    "video",
                    "test-project-no-ref",
                    "-p",
                    "Test video with no reference",
                    "--no-wait",
                    "--no-gate",
                ],
            )

            # Should see the warning because there's genuinely no reference
            assert "No primary reference" in result.output, (
                f"Expected 'No primary reference' warning not found in output:\n{result.output}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
