"""Test for F2: Layout-based reference discovery.

This test verifies that the reference discovery works correctly even when
the stored image_path in project.json is not accurate, as long as the
reference exists in the expected pre-production location.
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


class TestLayoutBasedReferenceDiscovery:
    """Test that reference discovery works via layout-based approach."""

    def test_reference_found_via_layout_when_stored_path_is_wrong(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """When project.json has primary_reference with incorrect image_path,
        but the reference exists in the expected pre-production location,
        it should still be detected as valid.
        """
        # Setup: create project
        _write_project(project_dir, "test-proj")

        # Add a reference image to pre-production location (v2 layout)
        # This is where the reference ACTUALLY is
        actual_ref_img = _add_image_to_preproduction(tmp_path, "test-proj", "location", "reference_location_test.jpg")

        # But let's say the project.json has an OLD or INCORRECT image_path
        # (e.g., from when the project was in a different location, or after a move)
        incorrect_old_path = "/some/old/path/that/does/not/exist/anymore.jpg"

        # Set up project.json with the incorrect image_path
        project_json = project_dir / "test-proj" / "project.json"
        project_data = json.loads(project_json.read_text())
        project_data["primary_reference"] = {
            "subject_type": "location",
            "skill": "location",
            "subject": "Test Location",
            "image_path": incorrect_old_path,  # This path doesn't exist
            "source_url": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "model": "test",
            "style_preset": "cinematic",
        }
        project_json.write_text(json.dumps(project_data, indent=2))

        # Verify our setup: the stored image_path is wrong, but the actual reference exists
        assert not Path(incorrect_old_path).exists(), "The stored image_path should not exist"
        assert actual_ref_img.exists(), "The actual reference image should exist"
        assert actual_ref_img.parent == tmp_path / "pre-production" / "test-proj" / "images" / "location"

        # Ensure we have a production plan
        _ensure_plan(tmp_path, "test-proj")

        # Now test that video generation STILL detects the reference correctly
        # thanks to our layout-based discovery fix
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
                    "test-proj",
                    "-p",
                    "Test video",
                    "--no-wait",
                    "--no-gate",
                ],
            )

            # The key assertion: should NOT see "No primary reference" warning
            # Because even though the stored image_path is wrong, we should find
            # the reference via layout-based discovery in pre-production/
            assert "No primary reference" not in result.output, (
                f"Unexpected 'No primary reference' warning in output: {result.output}\n"
                f"Full output: {result.output}"
            )

    def test_reference_not_found_when_truly_missing(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """When there is genuinely no reference available, the warning should appear."""
        # Setup: create project with no reference images
        _write_project(project_dir, "test-proj-no-ref")

        # Don't add any reference images to pre-production/

        # But let's say project.json claims there is a reference (with fake path)
        project_json = project_dir / "test-proj-no-ref" / "project.json"
        project_data = json.loads(project_json.read_text())
        project_data["primary_reference"] = {
            "subject_type": "location",
            "skill": "location",
            "subject": "Test Location",
            "image_path": "/fake/path/to/reference.jpg",
            "source_url": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "model": "test",
            "style_preset": "cinematic",
        }
        project_json.write_text(json.dumps(project_data, indent=2))

        # Ensure we have a production plan
        _ensure_plan(tmp_path, "test-proj-no-ref")

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
                    "test-proj-no-ref",
                    "-p",
                    "Test video",
                    "--no-wait",
                    "--no-gate",
                ],
            )

            # Should see the warning because there's genuinely no reference
            assert "No primary reference" in result.output, (
                f"Expected 'No primary reference' warning not found in output: {result.output}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
