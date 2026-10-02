r"""Per-shot auto-reference scoping + exponential retry backoff.

Auto-refs bug: the ``produce`` runner path passed ``auto_refs_enabled=True``
to the ``video`` pipeline for EVERY shot, and ``video`` merged the whole
project images tree into each shot's reference payload - even when the shot
list already declared its own refs, and even when a plate has nothing to do
with the shot (payload bloat -> free-tier timeouts, style bleed).

Contract (follow-up to issues #20 / #38):
- A shot with explicit refs NEVER gets auto-injected refs (the shot list is
  the source of truth).
- A referenceless shot gets auto-refs scoped to what the shot is concerned
  with: character plates only when the shot has a character anchor (issue
  #38), location/prop plates only when the shot's prompt mentions the plate
  stem, unclassifiable plates kept (legacy behavior).

Exponential backoff (issues #191/#192): ``RunnerConfig.
retry_backoff_factor`` > 1 grows each retry wait exponentially (base *
factor**(attempt-1)); 1.0 preserves the flat backoff. The RETRY progress
lines record the actual wait per attempt.

Run under .venv\\Scripts\\python (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from brandly_cli import shot_runner
from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id

# ---------------------------------------------------------------------------
# Fixtures / helpers
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


def _write_project(project_dir: Path, project_id: str) -> None:
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(json.dumps({"id": project_id, "name": "Test"}))


def _write_shots_file(tmp_path: Path, data: Any, name: str = "shots.json") -> Path:
    f = tmp_path / name
    f.write_text(json.dumps(data))
    return f


def _add_plate(project_dir: Path, pid: str, category: str, name: str) -> None:
    from PIL import Image

    p = project_dir.parent / "pre-production" / pid / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (10, 10, 10)).save(p, "PNG")


# ---------------------------------------------------------------------------
# scope_auto_refs - the pure per-shot filter
# ---------------------------------------------------------------------------


class TestScopeAutoRefs:
    def test_character_plate_kept_when_anchor_present(self) -> None:
        plates = [r"C:\p\pre-production\x\images\character\char_rebel.jpg"]
        out = shot_runner.scope_auto_refs(
            plates, prompt="rebel walks the line", character="rebel, 62, gaunt"
        )
        assert out == plates

    def test_character_plate_dropped_without_anchor(self) -> None:
        plates = [r"C:\p\pre-production\x\images\character\char_rebel.jpg"]
        out = shot_runner.scope_auto_refs(plates, prompt="rebel walks the line")
        assert out == []

    def test_location_plate_kept_when_prompt_mentions_stem(self) -> None:
        plates = [r"C:\p\pre-production\x\images\location\loc_ink.jpg"]
        out = shot_runner.scope_auto_refs(
            plates, prompt="Ink world: rebel walks", character="rebel"
        )
        assert out == plates

    def test_location_plate_dropped_when_prompt_does_not_mention_it(self) -> None:
        plates = [r"C:\p\pre-production\x\images\location\loc_chapel.jpg"]
        out = shot_runner.scope_auto_refs(
            plates, prompt="Ink world: rebel walks", character="rebel"
        )
        assert out == []

    def test_prop_plate_scoped_like_location(self) -> None:
        plates = [r"C:\p\pre-production\x\images\prop\prop_phone.jpg"]
        assert shot_runner.scope_auto_refs(
            plates, prompt="he checks the phone", character="rebel"
        ) == plates
        assert shot_runner.scope_auto_refs(
            plates, prompt="he stares at the wall", character="rebel"
        ) == []

    def test_unclassifiable_plate_kept(self) -> None:
        """Plates at the images root carry no category - legacy behavior."""
        plates = [r"C:\p\pre-production\x\images\plate_a.jpg"]
        assert shot_runner.scope_auto_refs(plates, prompt="anything") == plates

    def test_match_is_case_insensitive_and_slash_agnostic(self) -> None:
        plates = ["/p/x/images/location/Loc_Ink.opt.jpg"]
        out = shot_runner.scope_auto_refs(
            plates, prompt="INK WORLD", character="rebel"
        )
        assert out == plates


# ---------------------------------------------------------------------------
# produce runner wiring - explicit refs never augmented, referenceless scoped
# ---------------------------------------------------------------------------


class TestProduceRunnerAutoRefWiring:
    def _capture_generate(self, captured: dict[str, Any]):
        def fake_generate(project_id: str, shot: dict[str, Any], **kw: Any) -> bool:
            captured["shot"] = shot
            captured.update(kw)
            return True

        return fake_generate

    def test_shot_with_refs_gets_no_auto_refs(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        shots = _write_shots_file(
            tmp_path,
            [{"id": "shot01", "prompt": "x", "duration": 5, "refs": ["char_a"]}],
        )
        captured: dict[str, Any] = {}
        with patch(
            "brandly_cli.cmd.generation._generate_shot",
            side_effect=self._capture_generate(captured),
        ), patch(
            "brandly_cli.cmd.production._generate_shot",
            side_effect=self._capture_generate(captured),
        ), patch("brandly_cli.shot_runner.time.sleep"):
            result = runner.invoke(
                cli, ["produce", pid, "--shots", str(shots), "--only", "shot01", "--interval", "0"]
            )
        assert result.exit_code == 0, result.output
        assert captured["auto_refs_enabled"] is False

    def test_referenceless_shot_gets_scoped_auto_refs(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots_file(
            tmp_path,
            [{"id": "shot01", "prompt": "x", "duration": 5, "character": "rebel"}],
        )
        captured: dict[str, Any] = {}
        with patch(
            "brandly_cli.cmd.generation._generate_shot",
            side_effect=self._capture_generate(captured),
        ), patch(
            "brandly_cli.cmd.production._generate_shot",
            side_effect=self._capture_generate(captured),
        ), patch("brandly_cli.shot_runner.time.sleep"):
            result = runner.invoke(
                cli, ["produce", pid, "--shots", str(shots), "--only", "shot01", "--interval", "0"]
            )
        assert result.exit_code == 0, result.output
        assert captured["auto_refs_enabled"] is True
        assert callable(captured.get("auto_ref_filter"))
        # The filter keeps only what the shot is concerned with.
        plates = [
            "/p/x/images/character/char_rebel.jpg",
            "/p/x/images/location/loc_chapel.jpg",
        ]
        out = captured["auto_ref_filter"](plates)
        assert out == [plates[0]]

    def test_no_auto_refs_flag_disables_everything(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots_file(
            tmp_path, [{"id": "shot01", "prompt": "x", "duration": 5}]
        )
        captured: dict[str, Any] = {}
        with patch(
            "brandly_cli.cmd.generation._generate_shot",
            side_effect=self._capture_generate(captured),
        ):
            result = runner.invoke(
                cli,
                ["produce", pid, "--shots", str(shots), "--no-auto-refs",
                 "--interval", "0"],
            )
        assert result.exit_code == 0, result.output
        assert captured["auto_refs_enabled"] is False


# ---------------------------------------------------------------------------
# Exponential retry backoff (issues #191/#192)
# ---------------------------------------------------------------------------


class TestExponentialBackoff:
    def _make_config(self, tmp_path: Path, retries: int, factor: float):
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)
        progress = shot_runner.ProgressLog(
            tmp_path / "docs" / "tmp" / "produce_progress.txt"
        )
        return shot_runner.RunnerConfig(
            shots=[shot_runner.Shot(
                id="shot01", act="", style="cinematic", folder="scenes",
                prompt="p", duration=5,
            )],
            generate_one=lambda shot: (False, 1, "503 video_queue_full"),
            scenes_dir=scenes,
            progress=progress,
            interval=30.0,
            retries=retries,
            retry_backoff_factor=factor,
        )

    def test_factor_one_preserves_flat_backoff(self, tmp_path: Path) -> None:
        sleeps: list[float] = []
        with patch.object(shot_runner.time, "sleep", side_effect=sleeps.append):
            assert shot_runner.run_shots(self._make_config(tmp_path, 2, 1.0)) == 1
        assert sleeps == [30.0, 30.0]

    def test_factor_two_doubles_each_retry(self, tmp_path: Path) -> None:
        sleeps: list[float] = []
        with patch.object(shot_runner.time, "sleep", side_effect=sleeps.append):
            assert shot_runner.run_shots(self._make_config(tmp_path, 3, 2.0)) == 1
        assert sleeps == [30.0, 60.0, 120.0]

    def test_retry_lines_record_actual_wait(self, tmp_path: Path) -> None:
        config = self._make_config(tmp_path, 2, 2.0)
        with patch.object(shot_runner.time, "sleep"):
            shot_runner.run_shots(config)
        text = config.progress.path.read_text()
        assert "backoff=30s" in text
        assert "backoff=60s" in text

        plates = [r"C:\p\pre-production\x\images\location\loc_ink.jpg"]
        out = shot_runner.scope_auto_refs(
            plates, prompt="Ink world: rebel walks", character="rebel"
        )
        assert out == plates

    def test_location_plate_dropped_when_prompt_does_not_mention_it(self) -> None:
        plates = [r"C:\p\pre-production\x\images\location\loc_chapel.jpg"]
        out = shot_runner.scope_auto_refs(
            plates, prompt="Ink world: rebel walks", character="rebel"
        )
        assert out == []
