"""P1 contract tests — GOAL-ALL-OPEN-ISSUES.md phase P1.

RED-first proofs for the in-flight fixes on branch
``fix/f2-reference-injection-245-252``:

* #251 — ``brandly status`` accepts ``--root`` (parity with ``list``/``run``)
* #250 — reference gate auto-approves when the AI verdict is ``pass`` with a
  score at or above the threshold; below threshold (and no-AI) still prompts
* #246/#249 — ``cmd/production.py`` and the pipeline-path helpers go through
  ``async_compat.run_async`` (no bare ``asyncio.run(`` on pipeline paths)
* #248 — per-beat shot prompt variation: ``build_single_shot_prompt`` accepts
  ``beat_role`` and varies action/setting per beat role; the script-phase
  caller passes ``beat_role=beat``; global style stays shared
* #245/#252 — ``_load_project_reference`` reads the ``primary_reference``
  extra from ``project.json`` (fix commit ``4e3172d`` on this branch)
"""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from brandly_cli.gates import human_review_gate

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
    next_def = re.search(r"^(def |@click\.command|class )", source[match.end():], re.MULTILINE)
    end = match.end() + (next_def.start() if next_def else len(source) - match.end())
    return source[start:end]


# ---------------------------------------------------------------------------
# #251 — `brandly status` accepts --root
# ---------------------------------------------------------------------------


class TestStatusRootOption:
    def test_status_accepts_root_option(self, tmp_path: Path) -> None:
        """`brandly status <id> --root <tmp>` resolves the project (issue #251)."""
        import asyncio

        from brandly_cli.project_manager import ProjectManager
        from brandly_cli.types import ProjectData

        asyncio.run(ProjectManager(tmp_path).create(ProjectData(id="status-root-proj", name="T")))
        from brandly_cli.cli import cli

        result = CliRunner().invoke(cli, ["status", "status-root-proj", "--root", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "status-root-proj" in result.output

    def test_status_root_source_contract(self) -> None:
        """The status command declares a --root option like its siblings."""
        src = _read("cmd/production.py")
        assert "@click.option" in src
        # The status command's decorator block (just above `def status`) has --root.
        decorator = src[: src.index("def status(")]
        assert '--root' in decorator[decorator.rindex("@click.command"):], (
            "status command must declare --root (issue #251)"
        )


# ---------------------------------------------------------------------------
# #250 — reference gate auto-approve on AI pass
# ---------------------------------------------------------------------------


class TestGateAutoApprove:
    def test_auto_approves_on_ai_pass_at_threshold(self, monkeypatch) -> None:
        """AI verdict 'pass' + score >= threshold -> approved, no prompt."""
        called = []
        monkeypatch.setattr(
            "brandly_cli.gates.click.confirm",
            lambda *a, **k: called.append(1) or True,
        )
        approved, note = human_review_gate(
            "reference", "the object reference", ai_verdict="pass", ai_score=92
        )
        assert approved is True
        assert note == ""
        assert called == [], "gate must not prompt when the AI verdict is pass >= threshold"

    def test_auto_approves_at_exact_threshold(self, monkeypatch) -> None:
        """Score == threshold auto-approves (>= semantics)."""
        monkeypatch.setattr(
            "brandly_cli.gates.click.confirm", lambda *a, **k: pytest_fail()
        )
        approved, _ = human_review_gate(
            "reference", "label", ai_verdict="pass", ai_score=90, ai_threshold=90
        )
        assert approved is True

    def test_below_threshold_still_prompts(self, monkeypatch) -> None:
        """AI pass but score < threshold -> the human prompt still runs."""
        called = []
        monkeypatch.setattr(
            "brandly_cli.gates.click.confirm",
            lambda *a, **k: called.append(1) or True,
        )
        approved, _ = human_review_gate(
            "reference", "the object reference", ai_verdict="pass", ai_score=50
        )
        assert called, "below threshold the gate must prompt (fail-honest)"
        assert approved is True  # mocked confirm returns True

    def test_no_ai_verdict_still_prompts(self, monkeypatch) -> None:
        """No AI verdict -> current fail-honest behavior (prompt) is preserved."""
        called = []
        monkeypatch.setattr(
            "brandly_cli.gates.click.confirm",
            lambda *a, **k: called.append(1) or True,
        )
        human_review_gate("reference", "the object reference")
        assert called, "no-AI path must keep prompting (G11 fail-honest)"

    def test_reference_command_wires_ai_verdict(self) -> None:
        """The reference command passes gate_result status/score into the gate (#250)."""
        src = _read("cmd/generation.py")
        ref_body = _function_body(src, "reference")
        assert "ai_verdict=" in ref_body, (
            "reference command must wire the AI verdict into human_review_gate (#250)"
        )
        assert "ai_score=" in ref_body


# ---------------------------------------------------------------------------
# #246/#249 — async correctness via run_async
# ---------------------------------------------------------------------------


class TestAsyncCorrectness:
    def test_production_has_no_bare_asyncio_run(self) -> None:
        """No ``asyncio.run(`` in cmd/production.py — every call goes through
        ``async_compat.run_async`` so the pipeline path never crashes inside a
        running event loop (#246) and no coroutine is dropped (#249)."""
        src = _read("cmd/production.py")
        offenders = [
            (i + 1, line.strip())
            for i, line in enumerate(src.splitlines())
            if "asyncio.run(" in line
        ]
        assert not offenders, f"bare asyncio.run sites in production.py: {offenders}"

    def test_production_imports_run_async(self) -> None:
        """production.py imports the shared run_async helper."""
        src = _read("cmd/production.py")
        assert "from brandly_cli.async_compat import run_async" in src

    def test_maybe_llm_enhance_no_asyncio_run(self) -> None:
        """_maybe_llm_enhance runs on the pipeline path (video command calls it
        from produce) — it must use run_async, not bare asyncio.run (#246)."""
        src = _read("cmd/generation.py")
        body = _function_body(src, "_maybe_llm_enhance")
        assert "asyncio.run(" not in body, (
            "_maybe_llm_enhance must not use bare asyncio.run — it runs inside "
            "the pipeline's event loop and silently degrades today"
        )

    def test_video_command_body_no_asyncio_run(self) -> None:
        """The video command body (the produce path) has no bare asyncio.run."""
        src = _read("cmd/generation.py")
        body = _function_body(src, "video")
        assert "asyncio.run(" not in body


# ---------------------------------------------------------------------------
# #248 — per-beat shot prompt variation
# ---------------------------------------------------------------------------


class TestBeatPromptVariation:
    def test_build_single_shot_prompt_accepts_beat_role(self) -> None:
        """build_single_shot_prompt takes beat_role (#248 implementation)."""
        from brandly_cli.video_prompts import build_single_shot_prompt

        result = build_single_shot_prompt(
            subject="Ignite Espresso",
            action="demonstrates key features",
            environment="clean studio setting",
            style="cinematic",
            beat_role="setup",
        )
        assert isinstance(result, str) and result

    def test_beat_roles_vary_action_and_setting(self) -> None:
        """Different beat roles produce different action/setting segments."""
        from brandly_cli.video_prompts import build_single_shot_prompt

        prompts = {}
        for role in ("setup", "turn", "consequence", "resolve"):
            prompts[role] = build_single_shot_prompt(
                subject="Ignite Espresso",
                action="demonstrates key features",
                environment="clean studio setting",
                style="cinematic",
                beat_role=role,
            )
        # At least 3 distinct prompt bodies across the 4 beat roles
        distinct = len(set(prompts.values()))
        assert distinct >= 3, f"expected >=3 distinct per-beat prompts, got {distinct}"

    def test_beat_variation_keeps_global_style_shared(self) -> None:
        """Global style block (color grade / negatives) stays consistent across
        beats — brandly-consistency convention (never fork the style namespace)."""
        from brandly_cli.video_prompts import build_single_shot_prompt

        p_setup = build_single_shot_prompt(
            subject="X", action="a", environment="e", style="cinematic", beat_role="setup"
        )
        p_resolve = build_single_shot_prompt(
            subject="X", action="a", environment="e", style="cinematic", beat_role="resolve"
        )
        # Same style preset segments appear in both (shared global style).
        for fragment in ("teal", "Kodak"):
            in_setup = fragment.lower() in p_setup.lower()
            in_resolve = fragment.lower() in p_resolve.lower()
            assert in_setup == in_resolve, (
                f"global style fragment '{fragment}' present in one beat but not the other"
            )

    def test_script_caller_passes_beat_role(self) -> None:
        """The script phase's build_single_shot_prompt call passes beat_role=beat
        — without the wiring the #248 implementation is dead code."""
        src = _read("cmd/production.py")
        assert "beat_role=beat" in src, (
            "script phase must pass beat_role=beat to build_single_shot_prompt (#248)"
        )


# ---------------------------------------------------------------------------
# #245/#252 — reference metadata discovery
# ---------------------------------------------------------------------------


class TestReferenceMetadataDiscovery:
    def test_load_project_reference_reads_extra(self, tmp_path: Path) -> None:
        """_load_project_reference returns the primary_reference dict written
        as a project.json extra (extra='allow') — the #245/#252 fix."""
        import asyncio

        from brandly_cli.cli import _load_project_reference
        from brandly_cli.project_manager import ProjectManager
        from brandly_cli.types import ProjectData

        metadata = {
            "subject_type": "prop",
            "skill": "prop",
            "subject": "pocket espresso maker",
            "image_path": str(tmp_path / "pre-production" / "ref-proj" / "prop" / "plate.jpg"),
            "source_url": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "model": "test",
            "style_preset": "cinematic",
        }
        pm = ProjectManager(tmp_path)
        asyncio.run(pm.create(ProjectData(id="ref-proj", name="R")))
        asyncio.run(pm.update("ref-proj", {"primary_reference": metadata}))

        loaded = _load_project_reference("ref-proj", tmp_path)
        assert loaded is not None, "primary_reference extra must be readable (#245/#252)"
        assert loaded.get("subject_type") == "prop"
        assert loaded.get("subject") == "pocket espresso maker"

    def test_load_project_reference_none_when_absent(self, tmp_path: Path) -> None:
        """No reference metadata -> None (callers warn, never crash)."""
        import asyncio

        from brandly_cli.cli import _load_project_reference
        from brandly_cli.project_manager import ProjectManager
        from brandly_cli.types import ProjectData

        asyncio.run(ProjectManager(tmp_path).create(ProjectData(id="ref-none", name="N")))
        assert _load_project_reference("ref-none", tmp_path) is None


def pytest_fail() -> None:  # pragma: no cover - helper
    raise AssertionError("click.confirm must not be called in the auto-approve path")
