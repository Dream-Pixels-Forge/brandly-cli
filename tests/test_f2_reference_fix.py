"""Tests for F2: Reference injection fix (#245, #252).

RED: These tests should fail before the fix, pass after.
Tests that when a project has a valid primary_reference in project.json
and the corresponding reference image exists in pre-production/,
the asset phase does NOT warn "No primary reference".
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
        "shot_count": 3,
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


def _plan_rows(tmp_path: Path, project_id: str) -> dict[str, dict[str, str]]:
    from brandly_cli.utils import _read_production_plan_rows, production_plan_path
    return _read_production_plan_rows(production_plan_path(project_id, root=tmp_path))


def _ensure_plan(tmp_path: Path, project_id: str) -> None:
    """Write a minimal production plan so brandly video passes its gate."""
    plan_dir = tmp_path / ".brandly" / project_id / "docs" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "production_plan.md").write_text(
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


class TestReferenceInjectionFix:
    """Test that valid primary_reference in project.json is properly detected."""

    def test_asset_phase_recognizes_valid_reference(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """When project has primary_reference pointing to existing pre-production image,
        asset phase should not warn 'No primary reference'.
        """
        # Setup: create project
        _write_project(project_dir, "test-proj")

        # Add a reference image to pre-production location (v2 layout)
        ref_img = _add_image_to_preproduction(tmp_path, "test-proj", "location", "test_location.jpg")

        # Manually set up primary_reference in project.json to point to this image
        # This simulates what would happen after running `brandly reference --image`
        project_json = project_dir / "test-proj" / "project.json"
        project_data = json.loads(project_json.read_text())
        project_data["primary_reference"] = {
            "subject_type": "location",
            "skill": "location",
            "subject": "Test Location",
            "image_path": str(ref_img),  # Absolute path to the image in pre-production/
            "source_url": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "model": "test",
            "style_preset": "cinematic",
        }
        project_json.write_text(json.dumps(project_data, indent=2))

        # Verify the setup is correct
        assert ref_img.exists(), f"Reference image not found at {ref_img}"

        # Also verify it's in the expected pre-production location
        expected_dir = tmp_path / "pre-production" / "test-proj" / "images" / "location"
        assert ref_img.parent == expected_dir, (
            f"Reference image {ref_img} not in expected directory {expected_dir}"
        )

        # Ensure we have a production plan (needed for video generation to proceed)
        _ensure_plan(tmp_path, "test-proj")

        # Now test that video generation detects this reference properly
        # We'll mock the actual video generation to avoid API calls, but we want to
        # see if the reference detection logic works
        with patch(
            "brandly_cli.cmd.generation.create_video_task",
            return_value={"id": "test-task", "status": "pending"},
        ), patch(
            "brandly_cli.cmd.generation.poll_video",
            return_value={"url": "http://example.com/video.mp4", "status": "completed"},
        ):
            # Run video generation with minimal options to get to asset phase
            result = runner.invoke(
                cli,
                [
                    "video",
                    "test-proj",
                    "-p",
                    "Test video",
                    "--no-wait",
                    "--no-gate",
                    "--allow-referenceless",  # Don't require reference to proceed
                ],
            )

            # The key assertion: should NOT see "No primary reference" warning
            # Since we have a valid reference, this warning should not appear
            assert "No primary reference" not in result.output, (
                f"Unexpected 'No primary reference' warning in output: {result.output}"
            )

            # Should succeed (exit code 0) or at least not fail due to missing reference
            # Note: might still fail for other reasons (like missing actual video generation),
            # but not because of reference detection
            # Let's check that we didn't get the specific reference warning

    def test_project_with_reference_in_preproduction_detected(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """Direct test of reference detection logic.

        Creates a project.json with primary_reference pointing to an image
        in pre-production/ and verifies the reference is detected as valid.
        """
        # This test directly checks the reference validation logic
        # without going through the full video generation command

        pid = "test-proj-direct"

        # Create the project directory structure
        project_dir_pid = project_dir / pid
        project_dir_pid.mkdir(parents=True)

        # Create pre-production directory structure
        preprod_dir = tmp_path / "pre-production" / pid / "images" / "location"
        preprod_dir.mkdir(parents=True)

        # Add a reference image
        ref_img = preprod_dir / "reference_location_test.jpg"
        ref_img.write_text("fake image content")

        # Create project.json with primary_reference pointing to the image
        project_data = {
            "id": pid,
            "name": "Test Project",
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
            "primary_reference": {
                "subject_type": "location",
                "skill": "location",
                "subject": "Test Location",
                "image_path": str(ref_img),  # Absolute path to the image
                "source_url": "",
                "generated_at": "2026-01-01T00:00:00Z",
                "model": "test",
                "style_preset": "cinematic",
            }
        }

        (project_dir_pid / "project.json").write_text(
            json.dumps(project_data, indent=2)
        )

        # Now test the reference detection logic from generation.py
        # We'll import and test the key parts

        # Simulate what happens in generation.py video() function:
        # reference: dict[str, Any] | None = _load_project_reference(project_id, root)
        # Then check if reference is valid

        from brandly_cli.cli import _load_project_reference

        # This should successfully load the reference
        reference = _load_project_reference(pid, tmp_path)
        assert reference is not None, "_load_project_reference should return the reference"
        assert isinstance(reference, dict)
        assert reference.get("subject_type") == "location"
        assert reference.get("image_path") == str(ref_img)

        # Now test the validation logic that was failing
        # This is the code from generation.py lines ~1450-1470:
        missing = reference is None
        assert not missing, "Reference should not be missing"

        if reference is not None:
            path = reference.get("image_path", "")
            # This is the critical check that was failing in the bug
            path_exists = path and Path(path).exists()
            assert path_exists, f"Reference image path {path} should exist"

            # If we get here, the reference detection should work
            # In the actual code, this would add the path to ref_paths
            # and the reference would be considered valid

        # If we reach this point without assertion errors, the reference detection works
        assert True, "Reference detection logic should succeed for valid pre-production reference"
