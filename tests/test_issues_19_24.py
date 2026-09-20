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
from brandly_cli.utils import (
    _read_production_plan_rows,
    generate_project_id,
    production_plan_path,
)

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
    async def test_no_preset_when_style_preset_none(self) -> None:
        from brandly_cli.agnes_client import create_video_task

        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.agnes_client.httpx.AsyncClient", _make_fake_client(captured)),
            patch.dict("os.environ", {"AGNES_API_KEY": "k"}),
        ):
            await create_video_task(
                "monochrome ink wash on paper, no color", style_preset=None
            )

        prompt = captured["body"]["prompt"]
        assert "monochrome ink wash" in prompt
        assert "anamorphic lens" not in prompt
        assert "Kodak Vision3" not in prompt

    async def test_explicit_preset_applied(self) -> None:
        from brandly_cli.agnes_client import create_video_task

        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.agnes_client.httpx.AsyncClient", _make_fake_client(captured)),
            patch.dict("os.environ", {"AGNES_API_KEY": "k"}),
        ):
            await create_video_task("a cat on a sofa", style_preset="cinematic")

        assert "anamorphic lens" in captured["body"]["prompt"]

    async def test_preset_none_string_disables(self) -> None:
        from brandly_cli.agnes_client import create_video_task

        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.agnes_client.httpx.AsyncClient", _make_fake_client(captured)),
            patch.dict("os.environ", {"AGNES_API_KEY": "k"}),
        ):
            await create_video_task("plain prompt", style_preset="none")

        assert "anamorphic lens" not in captured["body"]["prompt"]


# ---------------------------------------------------------------------------
# Issue #24 - error message is not empty; create timeout raised
# ---------------------------------------------------------------------------


class TestVideoCreateErrorVisibility:
    def test_exception_type_and_message_printed(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        with patch(
            "brandly_cli.cli.create_video_task",
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

        with patch(
            "brandly_cli.cli.create_video_task",
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
            await create_video_task("x", style_preset=None)

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

        with patch("brandly_cli.cli.create_video_task", side_effect=fake_create):
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
        capture: dict[str, Any] = {}
        result = self._invoke(
            runner, pid, "--auto-ref-category", "location", capture=capture
        )
        assert result.exit_code == 0, result.output
        refs = capture["reference_images"] or []
        assert any("b.png" in r for r in refs)
        assert not any("a.png" in r for r in refs)


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
            "brandly_cli.cli.generate_image",
            AsyncMock(side_effect=AssertionError("must not generate")),
        ):
            result = runner.invoke(cli, _import_args(pid, plate), input="y\n")

        assert result.exit_code == 0, result.output
        # primary_reference must be registered in project.json
        data = json.loads((project_dir / pid / "project.json").read_text())
        ref = data["primary_reference"]
        assert ref["image_path"]
        assert Path(ref["image_path"]).exists()
        assert Path(ref["image_path"]).name.endswith("client_plate.png")

    def test_import_registers_plan_row(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        plate = _add_image(project_dir, pid, "general", "client_plate2.png")

        with patch(
            "brandly_cli.cli.generate_image",
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

        calls: list[str] = []
        sleeps: list[float] = []

        async def fake_create(prompt: str, **kwargs: Any) -> dict[str, Any]:
            calls.append(prompt)
            return dict(FAKE_TASK)

        with (
            patch("brandly_cli.cli.create_video_task", side_effect=fake_create),
            patch("brandly_cli.cli.time.sleep", side_effect=sleeps.append),
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
        assert len(calls) == 3
        # 1 request/min: exactly one 60s wait between consecutive variants.
        assert sleeps == [60.0, 60.0]

    def test_batch_passes_cinematic_preset_for_cinematic_style(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        captured: dict[str, Any] = {}

        async def fake_create(prompt: str, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return dict(FAKE_TASK)

        with (
            patch("brandly_cli.cli.create_video_task", side_effect=fake_create),
            patch("brandly_cli.cli.time.sleep"),
        ):
            result = runner.invoke(
                cli,
                ["batch", pid, "a cat", "-n", "1"],
            )

        assert result.exit_code == 0, result.output
        # Parity with the old hardcoded behaviour: cinematic style keeps the
        # cinematic preset; other styles must not receive it.
        assert captured.get("style_preset") == "cinematic"

    def test_batch_no_preset_for_non_photographic_style(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)

        captured: dict[str, Any] = {}

        async def fake_create(prompt: str, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return dict(FAKE_TASK)

        with (
            patch("brandly_cli.cli.create_video_task", side_effect=fake_create),
            patch("brandly_cli.cli.time.sleep"),
        ):
            result = runner.invoke(
                cli,
                ["batch", pid, "ink wash", "-n", "1", "--style", "explainer_video"],
            )

        assert result.exit_code == 0, result.output
        assert captured.get("style_preset") is None

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
            patch("brandly_cli.cli._generate_shot", side_effect=fake_generate),
            patch("brandly_cli.cli.time.sleep", side_effect=sleeps.append),
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
            patch("brandly_cli.cli._generate_shot", side_effect=fake_generate),
            patch("brandly_cli.cli.time.sleep"),
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
