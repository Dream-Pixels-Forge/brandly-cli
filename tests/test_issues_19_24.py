r"""Tests for issue fixes #19, #20, #21, #23, #24 and the shot-by-shot
production pipeline (`brandly produce`) driven by the production plan.

Run under .venv\Scripts\python (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli.cli import cli
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.utils import (
    _read_production_plan_rows,
    generate_project_id,
    production_plan_path,
)
from brandly_cli.video_backend import VideoBackend, VideoBackendCapabilities, VideoTaskResult


class FakeBackend(VideoBackend):
    """Fake backend for testing - captures calls for verification."""
    def __init__(self, captured: dict[str, Any] | None = None, sleeps: list[float] | None = None):
        self.captured = captured or {}
        self.sleeps = sleeps or []

    def capabilities(self):
        return VideoBackendCapabilities(max_duration_seconds=12, reliable_duration_seconds=8, rate_limit_rpm=1)

    async def submit(self, **kwargs):
        self.captured.update(kwargs)
        return VideoTaskResult(video_id="fake-1", status="pending")

    async def poll(self, video_id, *, max_wait_seconds=300, interval_seconds=5, model_name=None, project_id=None, requested_duration=None):
        self.captured["video_id"] = video_id
        if model_name:
            self.captured["model_name"] = model_name
        if project_id:
            self.captured["project_id"] = project_id
        if requested_duration:
            self.captured["requested_duration"] = requested_duration
        return VideoTaskResult(video_id=video_id, status="completed", url="https://example.com/v.mp4")

    async def fetch(self, video_id):
        return b"bytes"


def _patch_agnes_backend(fake_backend: FakeBackend):
    """Context manager to patch AgnesVideoBackend to return our fake."""
    from unittest.mock import patch
    return patch("brandly_cli.cmd.production.AgnesVideoBackend", lambda: fake_backend)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _add_image(project_dir: Path, project_id: str, category: str, name: str) -> Path:
    d = project_dir / project_id / "images" / category
    d.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (16, 16), (10, 10, 10))
    p = d / name
    img.save(p, "PNG")
    return p


def _plan_rows(tmp_path: Path, project_id: str) -> dict[str, dict[str, str]]:
    return _read_production_plan_rows(production_plan_path(project_id, root=tmp_path))


FAKE_TASK = {
    "id": "task-1",
    "video_id": "vid-1",
    "status": "pending",
    "progress": 0,
    "mode": "text",
}


def _make_fake_client(captured: dict[str, Any]) -> Any:
    """AsyncClient factory that captures constructor kwargs and posted JSON."""

    class FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"id": "task-1", "status": "pending", "progress": 0}

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *a: Any) -> None:
            pass

        async def post(self, url: str, **kwargs: Any) -> FakeResp:
            captured["body"] = kwargs["json"]
            return FakeResp()

        async def get(self, url: str, **kwargs: Any) -> httpx.Response:
            return httpx.Response(404, request=httpx.Request("GET", url))

    return FakeClient


# ---------------------------------------------------------------------------
# Issue #21 - style preset follows --style (no hardcoded cinematic)
# ---------------------------------------------------------------------------


class TestStylePresetFollowsStyle:
    async def test_provider_passes_prompt_through(self) -> None:
        """Providers no longer touch the prompt layer — prompt goes out as-is."""
        from brandly_cli.agnes_client import create_video_task

        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.agnes_client.httpx.AsyncClient", _make_fake_client(captured)),
            patch.dict("os.environ", {"AGNES_API_KEY": "k"}),
        ):
            await create_video_task("monochrome ink wash on paper, no color")

        prompt = captured["body"]["prompt"]
        assert "monochrome ink wash" in prompt
        assert "anamorphic lens" not in prompt
        assert "Kodak Vision3" not in prompt

    async def test_explicit_preset_applied_by_caller(self) -> None:
        """Style application now happens in the caller (prompt layer)."""
        assert "anamorphic lens" in apply_style_preset("a cat on a sofa", "cinematic")

    async def test_preset_none_string_disables(self) -> None:
        assert apply_style_preset("plain prompt", "none") == "plain prompt"


# ---------------------------------------------------------------------------
# Issue #24 - error message is not empty; create timeout raised
# ---------------------------------------------------------------------------


def _ensure_plan(tmp_path: Path, project_id: str) -> None:
    """Write a minimal production plan so brandly video passes its gate."""
    plan_dir = tmp_path / ".brandly" / project_id / "docs" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "production_plan.md").write_text(
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


class TestVideoCreateErrorVisibility:
    def test_exception_type_and_message_printed(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)

        with patch(
            "brandly_cli.cmd.generation.create_video_task",
            AsyncMock(side_effect=RuntimeError("backend exploded")),
        ):
            result = runner.invoke(
                cli,
                ["video", pid, "-p", "a cat", "--no-wait", "--no-gate", "--no-auto-refs"],
            )

        assert result.exit_code == 1
        # Issue #24: the failure must not print an empty message.
        assert "RuntimeError" in result.output
        assert "backend exploded" in result.output

    def test_timeout_exception_type_printed(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)

        with patch(
            "brandly_cli.cmd.generation.create_video_task",
            AsyncMock(side_effect=httpx.ReadTimeout("")),
        ):
            result = runner.invoke(
                cli,
                ["video", pid, "-p", "a cat", "--no-wait", "--no-gate", "--no-auto-refs"],
            )

        assert result.exit_code == 1
        # Empty timeout messages used to vanish - the type name must show.
        assert "ReadTimeout" in result.output

    async def test_create_uses_longer_timeout(self) -> None:
        """Issue #24: create endpoint should not time out at 60s on big payloads."""
        from brandly_cli.agnes_client import create_video_task

        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.agnes_client.httpx.AsyncClient", _make_fake_client(captured)),
            patch.dict("os.environ", {"AGNES_API_KEY": "k"}),
        ):
            await create_video_task("x")

        assert captured["client_kwargs"]["timeout"] >= 120


# ---------------------------------------------------------------------------
# Issue #19 - brandly jobs degrades gracefully on 404
# ---------------------------------------------------------------------------


class TestJobsGraceful404:
    async def test_list_jobs_404_returns_empty_without_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from brandly_cli.agnes_client import list_jobs

        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.agnes_client.httpx.AsyncClient", _make_fake_client(captured)),
            patch.dict("os.environ", {"AGNES_API_KEY": "k"}),
        ):
            jobs = await list_jobs()

        assert jobs == []
        out = capsys.readouterr().out
        # Degrade gracefully: no alarming error spam for an unsupported endpoint.
        assert "Could not fetch jobs" not in out


# ---------------------------------------------------------------------------
# Issue #20 - scope auto-injected reference images
# ---------------------------------------------------------------------------


class TestScopedAutoRefs:
    def _invoke(
        self,
        runner: CliRunner,
        pid: str,
        *extra: str,
        capture: dict[str, Any],
    ) -> Any:
        async def fake_create(*args: Any, **kwargs: Any) -> dict[str, Any]:
            capture["reference_images"] = kwargs.get("reference_images")
            return dict(FAKE_TASK)

        with patch("brandly_cli.cmd.generation.create_video_task", side_effect=fake_create):
            return runner.invoke(
                cli,
                [
                    "video",
                    pid,
                    "-p",
                    "a cat",
                    "--no-wait",
                    "--no-gate",
                    "--allow-referenceless",
                    *extra,
                ],
            )

    def test_default_includes_all_auto_refs(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_image(project_dir, pid, "prop", "a.png")
        _add_image(project_dir, pid, "location", "b.png")
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(runner, pid, capture=capture)
        assert result.exit_code == 0, result.output
        refs = capture["reference_images"] or []
        assert any("a.png" in r for r in refs)
        assert any("b.png" in r for r in refs)

    def test_no_auto_refs_flag_excludes_them(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_image(project_dir, pid, "prop", "a.png")
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(runner, pid, "--no-auto-refs", capture=capture)
        assert result.exit_code == 0, result.output
        refs = capture["reference_images"] or []
        assert not any("a.png" in r for r in refs)

    def test_auto_ref_category_filters(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_image(project_dir, pid, "prop", "a.png")
        _add_image(project_dir, pid, "location", "b.png")
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(
            runner, pid, "--auto-ref-category", "location", capture=capture
        )
        assert result.exit_code == 0, result.output
        refs = capture["reference_images"] or []
        assert any("b.png" in r for r in refs)
        assert not any("a.png" in r for r in refs)


class TestReferenceNoteFlag:
    """``--reference-note``: per-reference defines/exclude lines surface in
    the enhanced prompt as a [REFERENCE NOTES] section (clip-chain brief
    grammar: "@ref defines X. Do not use: Y.")."""

    def _invoke(
        self,
        runner: CliRunner,
        pid: str,
        *extra: str,
        capture: dict[str, Any],
    ) -> Any:
        async def fake_create(*args: Any, **kwargs: Any) -> dict[str, Any]:
            capture["prompt"] = args[0]
            return dict(FAKE_TASK)

        with patch("brandly_cli.cmd.generation.create_video_task", side_effect=fake_create):
            return runner.invoke(
                cli,
                [
                    "video",
                    pid,
                    "-p",
                    "a cat",
                    "--no-wait",
                    "--no-gate",
                    "--allow-referenceless",
                    *extra,
                ],
            )

    def test_note_with_defines_and_exclude(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(
            runner,
            pid,
            "--reference-note",
            "@char_amelie:her face, hair and clothing:the black blazer, the grey studio background",
            capture=capture,
        )
        assert result.exit_code == 0, result.output
        prompt = capture["prompt"]
        assert "[REFERENCE NOTES]" in prompt
        assert "@char_amelie defines her face, hair and clothing." in prompt
        assert "Do not use: the black blazer, the grey studio background." in prompt

    def test_multiple_notes_emit_in_order(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(
            runner,
            pid,
            "--reference-note",
            "@char_amelie:her face, hair and clothing:the black blazer",
            "--reference-note",
            "@prop_amelie_phone:her phone:the back of the phone, any logo",
            capture=capture,
        )
        assert result.exit_code == 0, result.output
        prompt = capture["prompt"]
        assert prompt.index("@char_amelie") < prompt.index("@prop_amelie_phone")

    def test_note_ref_only_emits_bare_line(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(
            runner, pid, "--reference-note", "@loc_bathroom", capture=capture
        )
        assert result.exit_code == 0, result.output
        prompt = capture["prompt"]
        assert "[REFERENCE NOTES]" in prompt
        assert "@loc_bathroom" in prompt
        assert "defines" not in prompt.split("[REFERENCE NOTES]")[1]
        assert "Do not use" not in prompt

    def test_flag_absent_leaves_prompt_unchanged(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)
        capture: dict[str, Any] = {}
        result = self._invoke(runner, pid, capture=capture)
        assert result.exit_code == 0, result.output
        assert "[REFERENCE NOTES]" not in capture["prompt"]


# ---------------------------------------------------------------------------
# Issue #23 - import an existing plate as primary_reference
# ---------------------------------------------------------------------------


def _import_args(pid: str, plate: Path) -> list[str]:
    return [
        "reference",
        pid,
        "--subject-type",
        "object",
        "--subject",
        "Test product",
        "--image",
        str(plate),
        "--no-generate",
    ]


class TestReferenceImport:
    def test_import_existing_image_no_generate(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        plate = _add_image(project_dir, pid, "general", "client_plate.png")

        with patch(
            "brandly_cli.cmd.generation.generate_image",
            AsyncMock(side_effect=AssertionError("must not generate")),
        ):
            result = runner.invoke(cli, _import_args(pid, plate), input="y\n")

        assert result.exit_code == 0, result.output
        # primary_reference must be registered in project.json
        data = json.loads((project_dir / pid / "project.json").read_text())
        ref = data["primary_reference"]
        assert ref["image_path"]
        plateref = Path(ref["image_path"])
        assert plateref.exists()
        # Issue #41: --format defaults to jpg — the plate is standardized to
        # .jpg and the duplicate .png twin is removed.
        assert plateref.name.endswith("client_plate.jpg"), plateref.name
        png_twin = plateref.with_suffix(".png")
        assert not png_twin.exists()

    def test_import_registers_plan_row(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        plate = _add_image(project_dir, pid, "general", "client_plate2.png")

        with patch(
            "brandly_cli.cmd.generation.generate_image",
            AsyncMock(side_effect=AssertionError("must not generate")),
        ):
            result = runner.invoke(cli, _import_args(pid, plate), input="y\n")

        assert result.exit_code == 0, result.output
        rows = _plan_rows(tmp_path, pid)
        assert rows, "expected a production plan row for the imported reference"

    def test_import_missing_image_fails(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        result = runner.invoke(cli, _import_args(pid, tmp_path / "ghost.png"))
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# brandly produce - shot-by-shot generation pulled from the production plan
# ---------------------------------------------------------------------------
# brandly batch — rate-limit compliance (1 request/min) + style preset parity
# ---------------------------------------------------------------------------


class TestBatchRateLimit:
    def test_batch_waits_one_minute_between_variants(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake = FakeBackend()

        with (
            _patch_agnes_backend(fake),
            patch("brandly_cli.cmd.production.time.sleep", side_effect=lambda x: fake.sleeps.append(x) or None),
        ):
            result = runner.invoke(
                cli,
                [
                    "batch",
                    pid,
                    "a product on a table",
                    "-n",
                    "3",
                ],
            )

        assert result.exit_code == 0, result.output
        assert fake.captured["prompt"]  # prompt was captured
        # 1 request/min: exactly one 60s wait between consecutive variants.
        assert fake.sleeps == [60.0, 60.0]

    def test_batch_applies_cinematic_preset_for_cinematic_style(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake = FakeBackend()

        with (
            _patch_agnes_backend(fake),
            patch("brandly_cli.cmd.production.time.sleep"),
        ):
            result = runner.invoke(
                cli,
                ["batch", pid, "a cat", "-n", "1"],
            )

        assert result.exit_code == 0, result.output
        # Parity with the old behaviour: cinematic style (the default) keeps
        # the cinematic preset — now applied in the caller, so the prompt
        # itself carries the cinematic cues and the provider kwarg is gone.
        assert "anamorphic lens" in fake.captured["prompt"]
        assert "style_preset" not in fake.captured

    def test_batch_no_preset_for_non_photographic_style(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake = FakeBackend()

        with (
            _patch_agnes_backend(fake),
            patch("brandly_cli.cmd.production.time.sleep"),
        ):
            result = runner.invoke(
                cli,
                ["batch", pid, "ink wash", "-n", "1", "--style", "explainer_video"],
            )

        assert result.exit_code == 0, result.output
        assert "anamorphic lens" not in fake.captured["prompt"]
        assert "style_preset" not in fake.captured

    def test_batch_wait_forwards_model_name_to_poll(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        """Issue #152: reference-mode tasks must be polled WITH model_name.

        Agnes docs: a video_id query without model_name is valid only for
        mode "text"; keyframe/reference polls must include model_name —
        otherwise retrieval is invalid (surfaces as 404/400/503 in --wait).
        """
        pid = generate_project_id()
        _write_project(project_dir, pid)

        fake = FakeBackend()

        with (
            _patch_agnes_backend(fake),
            patch("brandly_cli.cmd.production.time.sleep"),
        ):
            result = runner.invoke(
                cli, ["batch", pid, "a cat", "-n", "1", "--wait"]
            )

        assert result.exit_code == 0, result.output
        assert fake.captured["video_id"] == "fake-1"
        assert fake.captured.get("model_name") == "agnes-video-2.5-flash"

# (no batch; 1 request per minute Agnes rate limit)
# ---------------------------------------------------------------------------


def _write_shots(tmp_path: Path, shots: list[dict[str, Any]]) -> Path:
    f = tmp_path / "shots.json"
    f.write_text(json.dumps(shots))
    return f


class TestProduceShotByShot:
    def test_prepare_all_shots_then_generate_one_by_one(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots(
            tmp_path,
            [
                {"name": "shot-1", "prompt": "establishing shot", "duration": 5},
                {"name": "shot-2", "prompt": "close-up shot", "duration": 6},
            ],
        )

        calls: list[str] = []
        sleeps: list[float] = []

        def fake_generate(project_id: str, shot: dict[str, Any], **kw: Any) -> bool:
            calls.append(shot["name"])
            return True

        with (
            patch("brandly_cli.cmd.production._generate_shot", side_effect=fake_generate),
            patch("brandly_cli.cmd.production.time.sleep", side_effect=sleeps.append),
        ):
            result = runner.invoke(cli, ["produce", pid, "--shots", str(shots)])

        assert result.exit_code == 0, result.output
        # Both shots were generated, in order, one at a time.
        assert calls == ["shot-1", "shot-2"]
        # Rate limit: one sleep between consecutive shots (1 request/min).
        assert len(sleeps) == 1
        assert sleeps[0] == 60.0
        # Production plan is the source of truth: a row per shot exists.
        rows = _plan_rows(tmp_path, pid)
        shot_rows = [k for k, v in rows.items() if v["asset"].startswith("video-shot")]
        assert len(shot_rows) == 2

    def test_stops_on_failure_and_keeps_remaining_pending(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots(
            tmp_path,
            [
                {"name": "ok-shot", "prompt": "fine", "duration": 5},
                {"name": "bad-shot", "prompt": "fails", "duration": 5},
                {"name": "never-shot", "prompt": "never", "duration": 5},
            ],
        )

        calls: list[str] = []

        def fake_generate(project_id: str, shot: dict[str, Any], **kw: Any) -> bool:
            calls.append(shot["name"])
            return shot["name"] != "bad-shot"

        with (
            patch("brandly_cli.cmd.production._generate_shot", side_effect=fake_generate),
            patch("brandly_cli.cmd.production.time.sleep"),
        ):
            result = runner.invoke(cli, ["produce", pid, "--shots", str(shots)])

        assert result.exit_code != 0
        assert calls == ["ok-shot", "bad-shot"]  # never-shot was NOT attempted
        rows = _plan_rows(tmp_path, pid)
        shot_rows = [v for v in rows.values() if v["asset"].startswith("video-shot")]
        assert any("COMPLETED" in r["status"] for r in shot_rows)
        assert any("PENDING" in r["status"] for r in shot_rows)

    def test_missing_shots_file_fails(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        result = runner.invoke(cli, ["produce", pid, "--shots", str(tmp_path / "no.json")])
        assert result.exit_code != 0

    def test_empty_shot_list_fails(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots(tmp_path, [])
        result = runner.invoke(cli, ["produce", pid, "--shots", str(shots)])
        assert result.exit_code != 0
