"""Issue #310: produce retry flags must not be silently ignored.

``--retries/--backoff-factor/--continue-on-fail/--park-after`` only exist in
the progress-file runner, but ``produce`` routes a FLAT shot list (without
``--only/--max/--no-auto-refs/--character/--allow-referenceless``) through
the plan-based loop, which fail-stops on the first failed shot - the flags
were accepted, displayed in help, and silently dropped.

Ruling: any non-default retry-family flag routes the run through the
progress-file runner, which honors all four.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from brandly_cli.cli import cli

PROJECT = "retry-proj"


def _setup_flat(root: Path) -> Path:
    proj = root / ".brandly" / PROJECT
    (proj / "docs" / "plan").mkdir(parents=True, exist_ok=True)
    (proj / "docs" / "tmp").mkdir(parents=True, exist_ok=True)
    shots = [
        {"id": "shot-1", "prompt": "A test shot", "duration": 5},
        {"id": "shot-2", "prompt": "Another shot", "duration": 5},
    ]
    path = root / "shots.json"
    path.write_text(json.dumps(shots), encoding="utf-8")
    return path


def _invoke(root: Path, *args: str, **kwargs):  # type: ignore[no-untyped-def]
    runner = CliRunner()
    return runner.invoke(cli, ["--root", str(root), *args], **kwargs)


RUNNER = "brandly_cli.cmd.production._run_produce_runner"
GEN = "brandly_cli.cmd.production._generate_shot"


class TestRetryFlagsRouteToProgressRunner:
    def test_retries_routes_flat_list_to_runner(self, tmp_path: Path) -> None:
        shots = _setup_flat(tmp_path)
        calls = []

        def fake_runner(*args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)

        with patch(RUNNER, side_effect=fake_runner), patch(GEN, return_value=True):
            result = _invoke(
                tmp_path,
                "produce", PROJECT, "--shots", str(shots), "--interval", "0",
                "--retries", "3",
            )
        assert result.exit_code == 0, result.output
        assert calls, (
            "--retries must route the flat list through the progress-file "
            "runner (the plan-based loop cannot retry)"
        )
        assert calls[0].get("retries") == 3

    def test_continue_on_fail_routes(self, tmp_path: Path) -> None:
        shots = _setup_flat(tmp_path)
        calls = []

        def fake_runner(*args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)

        with patch(RUNNER, side_effect=fake_runner), patch(GEN, return_value=True):
            result = _invoke(
                tmp_path,
                "produce", PROJECT, "--shots", str(shots), "--interval", "0",
                "--continue-on-fail",
            )
        assert result.exit_code == 0, result.output
        assert calls, "--continue-on-fail must route through the runner"
        assert calls[0].get("continue_on_fail") is True

    def test_backoff_factor_routes(self, tmp_path: Path) -> None:
        shots = _setup_flat(tmp_path)
        calls = []

        def fake_runner(*args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)

        with patch(RUNNER, side_effect=fake_runner), patch(GEN, return_value=True):
            result = _invoke(
                tmp_path,
                "produce", PROJECT, "--shots", str(shots),
                "--interval", "0", "--retries", "2", "--backoff-factor", "2.0",
            )
        assert result.exit_code == 0, result.output
        assert calls
        assert calls[0].get("backoff_factor") == 2.0

    def test_default_flags_keep_plan_based_loop(self, tmp_path: Path) -> None:
        """No retry flags + flat list: the plan-based loop stays the default."""
        shots = _setup_flat(tmp_path)
        calls = []

        def fake_runner(*args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)

        with (
            patch(RUNNER, side_effect=fake_runner),
            patch(GEN, return_value=True) as gen,
        ):
            result = _invoke(
                tmp_path, "produce", PROJECT, "--shots", str(shots),
                "--interval", "0",
            )
        assert result.exit_code == 0, result.output
        assert not calls, "without retry flags the plan-based loop must stay"
        assert gen.called, "the plan-based loop must have run"
