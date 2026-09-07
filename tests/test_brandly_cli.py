"""Tests for brandly-cli core logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brandly_cli.constants import (
    PHASE_ORDER,
    SHOT_COSTS,
    STYLE_COSTS,
    STYLE_PRESET_OPTIONS,
    VIDEO_STYLES,
)
from brandly_cli.memory import UserPreferences
from brandly_cli.style_presets import apply_style_preset, get_negative_prompt
from brandly_cli.types import CostEstimate, PhaseResult, ProjectData
from brandly_cli.utils import (
    generate_project_id,
    is_valid_project_id,
    read_json,
    write_atomic,
    write_json,
)

# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    def test_video_styles_complete(self) -> None:
        assert len(VIDEO_STYLES) == 10

    def test_style_costs_all_defined(self) -> None:
        for style in VIDEO_STYLES:
            assert style in STYLE_COSTS, f"Missing cost for {style}"

    def test_shot_costs_defined(self) -> None:
        assert SHOT_COSTS[5] == 30

    def test_phase_order_complete(self) -> None:
        assert PHASE_ORDER[0] == "init"
        assert PHASE_ORDER[-1] == "done"
        assert len(PHASE_ORDER) == 10

    def test_style_presets(self) -> None:
        assert "photorealistic" in STYLE_PRESET_OPTIONS
        assert "cinematic" in STYLE_PRESET_OPTIONS


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestTypes:
    def test_project_data_defaults(self) -> None:
        proj = ProjectData(id="test-id")
        assert proj.status == "pending"
        assert proj.style == "cinematic"
        assert proj.budget == 500
        assert proj.current_phase == "init"

    def test_project_data_to_dict(self) -> None:
        proj = ProjectData(id="abc", name="My Product", style="ugc")
        d = proj.to_dict()
        assert d["id"] == "abc"
        assert d["name"] == "My Product"

    def test_phase_result_defaults(self) -> None:
        pr = PhaseResult()
        assert pr.status == "pending"

    def test_cost_estimate(self) -> None:
        est = CostEstimate(style="cinematic", shot_count=5)
        assert est.style == "cinematic"


# ---------------------------------------------------------------------------
# Style presets tests
# ---------------------------------------------------------------------------


class TestStylePresets:
    def test_apply_none(self) -> None:
        assert apply_style_preset("a cat", "none") == "a cat"

    def test_apply_cinematic_adds_suffix(self) -> None:
        result = apply_style_preset("a cat", "cinematic")
        assert "anamorphic" in result

    def test_apply_photorealistic(self) -> None:
        result = apply_style_preset("portrait", "photorealistic")
        assert "Sony A7IV" in result

    def test_get_negative_prompt(self) -> None:
        neg = get_negative_prompt("cinematic")
        assert "ai generated" in neg

    def test_get_negative_prompt_none(self) -> None:
        assert get_negative_prompt("none") == ""


# ---------------------------------------------------------------------------
# Utils tests
# ---------------------------------------------------------------------------


class TestUtils:
    def test_generate_project_id_format(self) -> None:
        pid = generate_project_id()
        assert is_valid_project_id(pid)

    def test_is_valid_project_id(self) -> None:
        assert is_valid_project_id(generate_project_id())
        assert not is_valid_project_id("not_a_uuid")
        assert not is_valid_project_id("")
        # Slug format accepted
        assert is_valid_project_id("samsung-s26-campaign")
        # Path traversal rejected
        assert not is_valid_project_id("../etc/passwd")
        assert not is_valid_project_id("foo/bar")
        assert not is_valid_project_id("foo\\bar")
        # Drive-relative rejected (Windows)
        assert not is_valid_project_id("C:foo")
        assert not is_valid_project_id("D:bar")
        # Control chars rejected
        assert not is_valid_project_id("foo\x00bar")
        # Reserved device names rejected
        assert not is_valid_project_id("CON")
        assert not is_valid_project_id("com1")
        assert not is_valid_project_id("LPT1")

    def test_write_read_json(self, tmp_path: Path) -> None:
        p = tmp_path / "test.json"
        write_json(p, {"key": "value"})
        data = read_json(p)
        assert data["key"] == "value"

    def test_write_atomic(self, tmp_path: Path) -> None:
        p = tmp_path / "atomic.txt"
        write_atomic(p, "hello")
        assert p.read_text() == "hello"


# ---------------------------------------------------------------------------
# Memory tests
# ---------------------------------------------------------------------------


class TestMemory:
    def test_empty_initial_state(self, tmp_path: Path) -> None:
        mem = UserPreferences(tmp_path)
        assert not mem.exists()
        assert mem.get() == {}

    def test_like_and_dislike_hook(self, tmp_path: Path) -> None:
        mem = UserPreferences(tmp_path)
        mem.like_hook("hook1")
        assert "hook1" in mem.get()["liked_hooks"]
        mem.dislike_hook("hook1")
        assert "hook1" not in mem.get()["liked_hooks"]
        assert "hook1" in mem.get()["disliked_hooks"]

    def test_reset(self, tmp_path: Path) -> None:
        mem = UserPreferences(tmp_path)
        mem.like_hook("some hook")
        mem.reset()
        assert mem.get()["liked_hooks"] == []

    def test_persistence(self, tmp_path: Path) -> None:
        mem1 = UserPreferences(tmp_path)
        mem1.like_hook("persistent hook")
        # UserPreferences saves automatically on mutation
        mem2 = UserPreferences(tmp_path)
        assert "persistent hook" in mem2.get()["liked_hooks"]


# ---------------------------------------------------------------------------
# Project manager tests
# ---------------------------------------------------------------------------


class TestProjectManager:
    def test_create_and_read(self, tmp_path: Path) -> None:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(tmp_path)
        proj = ProjectData(id="test-001", name="Product X")
        asyncio_run(pm.create(proj))
        loaded = asyncio_run(pm.read("test-001"))
        assert loaded is not None
        assert loaded.name == "Product X"

    def test_list_empty(self, tmp_path: Path) -> None:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(tmp_path)
        ids = asyncio_run(pm.list_all())
        assert ids == []

    def test_delete(self, tmp_path: Path) -> None:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(tmp_path)
        proj = ProjectData(id="del-001", name="To Delete")
        asyncio_run(pm.create(proj))
        assert asyncio_run(pm.delete("del-001")) is True
        assert asyncio_run(pm.read("del-001")) is None


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Cost tracker tests
# ---------------------------------------------------------------------------


class TestCostTracker:
    def test_can_afford(self, tmp_path: Path) -> None:
        from brandly_cli.cost_tracker import CostTracker

        ct = CostTracker(tmp_path / "projects")
        # Create a fake cost state file
        proj_dir = tmp_path / "projects" / "proj-1"
        proj_dir.mkdir(parents=True)
        (proj_dir / "cost.json").write_text(
            json.dumps(
                {
                    "id": "proj-1",
                    "budget_credits": 500,
                    "credits_spent": 100,
                    "cost_log": [],
                }
            )
        )
        result = asyncio_run(ct.can_afford("proj-1", 50))
        assert result["allowed"] is True
        assert result["remaining"] == 400

    def test_budget_exceeded(self, tmp_path: Path) -> None:
        from brandly_cli.cost_tracker import CostTracker

        ct = CostTracker(tmp_path / "projects")
        proj_dir = tmp_path / "projects" / "proj-2"
        proj_dir.mkdir(parents=True)
        (proj_dir / "cost.json").write_text(
            json.dumps(
                {
                    "id": "proj-2",
                    "budget_credits": 100,
                    "credits_spent": 90,
                    "cost_log": [],
                }
            )
        )
        with pytest.raises(ValueError, match="Budget exceeded"):
            asyncio_run(ct.record_spend("proj-2", "asset", "image", 20))

    def test_record_and_summary(self, tmp_path: Path) -> None:
        from brandly_cli.cost_tracker import CostTracker

        ct = CostTracker(tmp_path / "projects")
        proj_dir = tmp_path / "projects" / "proj-3"
        proj_dir.mkdir(parents=True)
        (proj_dir / "cost.json").write_text(
            json.dumps(
                {
                    "id": "proj-3",
                    "budget_credits": 500,
                    "credits_spent": 0,
                    "cost_log": [],
                }
            )
        )
        asyncio_run(ct.record_spend("proj-3", "asset", "image", 50))
        summary = asyncio_run(ct.get_summary("proj-3"))
        assert summary["total"] == 50
        assert summary["remaining"] == 450

    def test_record_spend_auto_initializes_from_budget(self, tmp_path: Path) -> None:
        """When cost.json is missing and budget_credits is provided, it is created."""
        from brandly_cli.cost_tracker import CostTracker

        ct = CostTracker(tmp_path / "projects")
        # No cost.json exists for proj-new
        result = asyncio_run(
            ct.record_spend("proj-new", "asset", "image", 25, budget_credits=400)
        )
        assert result["total_spent"] == 25
        assert result["remaining"] == 375
        # Cost state file should now exist
        cost_file = tmp_path / "projects" / "proj-new" / "cost.json"
        assert cost_file.exists()
        state = json.loads(cost_file.read_text())
        assert state["budget_credits"] == 400

    def test_record_spend_missing_project_no_budget_raises(self, tmp_path: Path) -> None:
        """When cost.json is missing AND no budget provided, raise clearly."""
        from brandly_cli.cost_tracker import CostTracker

        ct = CostTracker(tmp_path / "projects")
        with pytest.raises(ValueError, match="not found"):
            asyncio_run(ct.record_spend("proj-ghost", "asset", "image", 10))
