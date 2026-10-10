"""Contract tests — GOAL-OPEN-ISSUES-270-283.md (issues #270–#283).

RED-first proofs, one section per increment. The I1 section pins:

* #270 — the produce runner syncs a VALID phase (``asset``, never the
  invalid ``"video"``) and a poisoned ``current_phase`` fails honestly
  (structured error + repair hint) instead of a raw ``ValueError`` at the
  three ``.index()`` sites (``run_pipeline``/``run``/``approve``)
* #271 — the pipeline-path helpers (``cli._load_project_reference``) and the
  agent-tool handlers (``agent_tools.py``) go through
  ``async_compat.run_async`` (no bare ``asyncio.run(`` reachable from a
  running loop); a reference read from inside a running loop returns the
  metadata, never a silently-swallowed ``None``
* same-chain — ``brandly video``'s metadata lookup searches the REAL plate
  path (``resolve_media_root(...,"images") / category``) with the REAL
  prefix (``layout.image_name_prefix``), not the dead
  ``images/<category>`` depth + ``reference_<subject_type>_`` prefix
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from click.testing import CliRunner

_SRC = Path(__file__).resolve().parent.parent / "src" / "brandly_cli"


# ---------------------------------------------------------------------------
# Source-contract helpers
# ---------------------------------------------------------------------------


def _read(rel: str) -> str:
    return (_SRC / rel).read_text(encoding="utf-8")


def _function_body(source: str, func_name: str) -> str:
    """Return the source slice of a top-level ``def <func_name>`` body."""
    match = re.search(rf"^def {re.escape(func_name)}\(.*?:", source, re.MULTILINE | re.DOTALL)
    assert match, f"function {func_name} not found"
    start = match.start()
    next_def = re.search(r"^(def |@click\.command|class |async def )", source[match.end():], re.MULTILINE)
    end = match.end() + (next_def.start() if next_def else len(source) - match.end())
    return source[start:end]


def _make_project(root: Path, pid: str = "brewmaster-one", **extra: object) -> None:
    """Create a project fixture on disk (project.json + v2 skeleton)."""
    from brandly_cli.project_manager import ProjectManager
    from brandly_cli.types import ProjectData

    fields: dict[str, object] = {
        "id": pid,
        "name": "Brewmaster",
        "description": "A 30-second product presentation",
        "style": "cinematic",
        "shot_count": 5,
    }
    fields.update(extra)
    asyncio.run(ProjectManager(root).create(ProjectData(**fields)))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# I1 — #271: pipeline-path async surface
# ---------------------------------------------------------------------------


class TestPipelineAsyncSurface:
    def test_no_bare_asyncio_run_in_cli(self) -> None:
        """cli.py must not call bare asyncio.run — the pipeline path runs
        inside a running loop and the bare call silently degrades (#271)."""
        src = _read("cli.py")
        bare = [
            ln for ln in src.splitlines()
            if "asyncio.run(" in ln and "run_async(" not in ln
        ]
        assert not bare, f"bare asyncio.run( sites in cli.py: {bare}"

    def test_no_bare_asyncio_run_in_agent_tools(self) -> None:
        """agent_tools.py handlers run inside agent_tool_loop's running loop —
        a bare asyncio.run there makes EVERY built-in tool call fail with
        ``{"error": ...}`` (#271)."""
        src = _read("agent_tools.py")
        bare = [
            ln for ln in src.splitlines()
            if "asyncio.run(" in ln and "run_async(" not in ln
        ]
        assert not bare, f"bare asyncio.run( sites in agent_tools.py: {bare}"

    def test_web_async_helpers_go_through_run_async(self) -> None:
        """web/state.py + web/utils/ffprobe.py are broken by construction if
        called from a running loop — the dual-context helper is the standard."""
        state_src = _read("web/state.py")
        assert "asyncio.run(" not in state_src.replace("run_async(", ""), (
            "web/state.py must go through run_async (no bare asyncio.run)"
        )
        ffprobe_src = _read("web/utils/ffprobe.py")
        assert "asyncio.run(" not in ffprobe_src.replace("run_async(", ""), (
            "web/utils/ffprobe.py must go through run_async (no bare asyncio.run)"
        )

    def test_reference_read_inside_running_loop_returns_metadata(
        self, tmp_path: Path
    ) -> None:
        """_load_project_reference called from INSIDE a running event loop
        must return the project's primary_reference — pre-fix the bare
        asyncio.run raised, was swallowed, and the GOLD plate was silently
        dropped (#271)."""
        from brandly_cli.cli import _load_project_reference

        _make_project(
            tmp_path,
            pid="ref-loop-proj",
            primary_reference={
                "subject_type": "character",
                "image_path": "/tmp/char_theo.jpg",
            },
        )

        async def _in_loop() -> dict[str, object] | None:
            # The bug: calling the sync helper while a loop is running.
            return _load_project_reference("ref-loop-proj", tmp_path)

        result = asyncio.run(_in_loop())
        assert result is not None, (
            "reference metadata silently dropped inside a running loop (#271)"
        )
        assert result.get("subject_type") == "character"

    def test_agent_tool_handler_inside_running_loop_returns_data(
        self, tmp_path: Path
    ) -> None:
        """A built-in tool handler invoked from agent_tool_loop's running
        loop must return real data — pre-fix every call failed with
        ``{"error": ...}`` (#271)."""
        from brandly_cli.agent_tools import _list_projects

        _make_project(tmp_path, pid="tools-loop-proj")

        async def _in_loop() -> dict[str, object]:
            # The bug: the handler runs inside the agent loop's running loop.
            return _list_projects(root=str(tmp_path))

        result = asyncio.run(_in_loop())
        assert "error" not in result, f"tool failed inside the loop: {result}"
        assert result.get("count", 0) >= 1


# ---------------------------------------------------------------------------
# I1 — #270: the produce runner syncs a valid phase
# ---------------------------------------------------------------------------


class TestSyncProjectPhase:
    def test_sync_project_writes_valid_phase(self) -> None:
        """The produce runner's _sync_project writes a phase that IS in
        PHASE_ORDER — ``"video"`` is not a phase and bricks every
        subsequent phase command (#270)."""
        from brandly_cli.constants import PHASE_ORDER

        src = _read("cmd/generation.py")
        # The sync_production_state call inside the produce runner.
        call = re.search(
            r"sync_production_state\((.*?)\)", src, re.DOTALL
        )
        assert call, "sync_production_state call not found in generation.py"
        args = call.group(1)
        match = re.search(r'current_phase\s*=\s*"([a-z_]+)"', args)
        assert match, "current_phase= not found in the sync call"
        assert match.group(1) in PHASE_ORDER, (
            f"current_phase='{match.group(1)}' is not a pipeline phase (#270)"
        )


# ---------------------------------------------------------------------------
# I1 — #270: poisoned current_phase fails honestly
# ---------------------------------------------------------------------------


class TestPoisonedPhaseFailsHonest:
    def test_run_command_fails_honest_on_poisoned_phase(
        self, tmp_path: Path
    ) -> None:
        """`brandly run <id>` on a project with current_phase='video' exits 1
        with a structured repair hint — never a raw ValueError traceback."""
        from brandly_cli.project_manager import ProjectManager

        _make_project(tmp_path, pid="poisoned-run")
        asyncio.run(
            ProjectManager(tmp_path).update(
                "poisoned-run", {"current_phase": "video"}
            )
        )
        from brandly_cli.cli import cli

        result = CliRunner().invoke(
            cli, ["--root", str(tmp_path), "run", "poisoned-run"]
        )
        assert result.exit_code == 1, f"expected exit 1, got {result.exit_code}"
        assert "Traceback" not in result.output, (
            f"raw traceback leaked (#270): {result.output}"
        )
        assert "not a pipeline phase" in result.output
        assert "repair" in result.output.lower()

    def test_approve_fails_honest_on_poisoned_phase(self, tmp_path: Path) -> None:
        """`brandly approve <id> <phase>` on a poisoned project exits 1 with
        a structured repair hint — never a raw ValueError (#270)."""
        from brandly_cli.project_manager import ProjectManager

        _make_project(tmp_path, pid="poisoned-approve")
        asyncio.run(
            ProjectManager(tmp_path).update(
                "poisoned-approve", {"current_phase": "video"}
            )
        )
        from brandly_cli.cli import cli

        result = CliRunner().invoke(
            cli, ["--root", str(tmp_path), "approve", "poisoned-approve", "asset"]
        )
        assert result.exit_code == 1, f"expected exit 1, got {result.exit_code}"
        assert "Traceback" not in result.output, (
            f"raw traceback leaked (#270): {result.output}"
        )
        assert "not a pipeline phase" in result.output

    def test_run_pipeline_fails_honest_on_poisoned_phase(
        self, tmp_path: Path
    ) -> None:
        """Director.run_pipeline on a poisoned project returns a structured
        error dict (never raises ValueError) — the --execute path is
        guardable downstream (#270)."""
        from brandly_cli.cmd.production import Director, DirectorConfig
        from brandly_cli.project_manager import ProjectManager

        _make_project(tmp_path, pid="poisoned-pipeline")
        asyncio.run(
            ProjectManager(tmp_path).update(
                "poisoned-pipeline", {"current_phase": "video"}
            )
        )
        director = Director(DirectorConfig(tmp_path))

        async def _in_loop() -> dict[str, object]:
            return await director.run_pipeline("poisoned-pipeline")

        result = asyncio.run(_in_loop())
        assert "error" in result, f"expected a structured error, got {result}"
        assert "not a pipeline phase" in str(result["error"])


# ---------------------------------------------------------------------------
# I1 — same-chain: brandly video's metadata lookup uses the real plate path
# ---------------------------------------------------------------------------


class TestVideoMetadataLookupContract:
    def test_video_lookup_uses_real_plate_path(self) -> None:
        """The video command's metadata lookup resolves the v2 plate path
        (``resolve_media_root(...,'images') / category``) with the real
        prefix — the dead ``images/<category>`` depth and the
        ``reference_<subject_type>_`` prefix match nothing on disk."""
        src = _read("cmd/generation.py")
        # Find the video command's expected_dir construction (with its
        # images_root line for the resolve context).
        match = re.search(
            r"images_root = ([^\n]+)\n(?:[^\n]*\n)*?\s*expected_dir\s*=\s*([^\n]+)", src
        )
        assert match, "video metadata lookup (images_root + expected_dir) not found"
        root_expr, expr = match.group(1), match.group(2)
        assert "resolve_media_root" in root_expr
        assert '/ "images" /' not in expr, (
            f"video metadata lookup uses the dead images/ depth: {expr}"
        )
        # The prefix must come from the layout (IMAGE_NAME_PREFIXES), not the
        # stale reference_<subject_type>_ literal.
        prefix_match = re.search(
            r'expected_prefix\s*=\s*([^\n]+)', src
        )
        assert prefix_match, "expected_prefix not found in generation.py"
        assert 'f"reference_{subject_type}_"' not in prefix_match.group(1), (
            "video metadata lookup uses the dead reference_ prefix"
        )
