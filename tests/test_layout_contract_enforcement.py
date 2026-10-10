"""Layout-contract enforcement — GOAL: the pipeline honors the layout taxonomy.

The drift set (#297-#302, found in the live `coffee-mug-duo` demo run):

* #298 — the screenplay belongs in ``docs/screenplay/`` (the layout declares
  ``screenplay/ — screenplays + beat sheets``), never ``docs/plan/``
* #299 — trends/concept/the scene manifest belong in ``docs/general/``
  (research + creative + manifest documents); ``docs/plan/`` is for
  pre-generation plans (production_plan.md)
* #304 — run transcripts belong in ``docs/tmp/`` (transient working docs)

Readers accept the LEGACY ``docs/plan/`` locations (back-compat with
pre-existing projects); writers always write the contract-correct path.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

_SRC = Path(__file__).resolve().parent.parent / "src" / "brandly_cli"


def _read(rel: str) -> str:
    return (_SRC / rel).read_text(encoding="utf-8")


def _make_project(root: Path, pid: str = "layout-proj", **extra: object) -> None:
    from brandly_cli.project_manager import ProjectManager
    from brandly_cli.types import ProjectData

    fields: dict[str, object] = {"id": pid, "name": "L", "style": "cinematic", "shot_count": 5}
    fields.update(extra)
    asyncio.run(ProjectManager(root).create(ProjectData(**fields)))  # type: ignore[arg-type]


def _seed(root: Path, pid: str, phase: str) -> None:
    from brandly_cli.cmd.production import PHASE_ORDER
    from brandly_cli.project_manager import ProjectManager

    prior = {p: {"status": "completed"} for p in PHASE_ORDER[: PHASE_ORDER.index(phase)]}
    asyncio.run(ProjectManager(root).update(pid, {"current_phase": phase, "phases": prior}))


def _director(root: Path, agent_runner=None):  # type: ignore[no-untyped-def]
    from brandly_cli.cmd.production import Director, DirectorConfig

    return Director(DirectorConfig(root, agent_runner=agent_runner))


class TestLayoutTaxonomy:
    def test_general_category_declared(self) -> None:
        """docs/general/ exists in the taxonomy — research + creative + the
        scene manifest (#299)."""
        from brandly_cli.layout import DOC_CATEGORIES

        assert "general" in DOC_CATEGORIES

    def test_trends_writer_targets_general(self, tmp_path: Path) -> None:
        """The trends phase writes docs/general/trends.md (#299)."""
        from brandly_cli.trends import TREND_DATABASE

        _make_project(tmp_path, pid="trends-gen", product_category=next(iter(TREND_DATABASE)))
        _seed(tmp_path, "trends-gen", "trends")
        result = asyncio.run(_director(tmp_path).run_phase("trends-gen", "trends"))
        assert "error" not in result, result
        new = tmp_path / ".brandly" / "trends-gen" / "docs" / "general" / "trends.md"
        assert new.exists() and new.read_text(encoding="utf-8").strip(), (
            "the trends writer must target docs/general/ (#299)"
        )

    def test_concept_writer_targets_general(self, tmp_path: Path) -> None:
        """The concept phase writes docs/general/concept.md (#299)."""
        _make_project(tmp_path, pid="concept-gen", description="a test brief")
        _seed(tmp_path, "concept-gen", "concept")
        result = asyncio.run(
            _director(tmp_path, agent_runner=lambda p: "# Concept\n\nA moody brewery.\n").run_phase(
                "concept-gen", "concept"
            )
        )
        assert "error" not in result, result
        new = tmp_path / ".brandly" / "concept-gen" / "docs" / "general" / "concept.md"
        assert new.exists() and new.read_text(encoding="utf-8").strip(), (
            "the concept writer must target docs/general/ (#299)"
        )

    def test_screenplay_writer_targets_screenplay_category(self, tmp_path: Path) -> None:
        """The screenplay phase writes docs/screenplay/screenplay.md (#298) —
        the layout declares screenplay/ for screenplays + beat sheets."""
        _make_project(tmp_path, pid="screenplay-cat", description="a test brief")
        _seed(tmp_path, "screenplay-cat", "screenplay")
        result = asyncio.run(
            _director(
                tmp_path, agent_runner=lambda p: "# Screenplay\n\nINT. BREWERY - DAWN\n"
            ).run_phase("screenplay-cat", "screenplay")
        )
        assert "error" not in result, result
        new = tmp_path / ".brandly" / "screenplay-cat" / "docs" / "screenplay" / "screenplay.md"
        assert new.exists() and new.read_text(encoding="utf-8").strip(), (
            "the screenplay writer must target docs/screenplay/ (#298)"
        )
        old = tmp_path / ".brandly" / "screenplay-cat" / "docs" / "plan" / "screenplay.md"
        assert not old.exists(), "the screenplay must NOT land in docs/plan/ (#298)"

    def test_scenes_manifest_targets_general(self, tmp_path: Path) -> None:
        """scenes.json lives at docs/general/scenes.json (#299)."""
        from brandly_cli import scenes

        _make_project(tmp_path, pid="scenes-gen")
        shots = [
            {"id": f"shot-{i}", "prompt": "x", "duration": 5, "scene": 1, "shot": i}
            for i in range(1, 4)
        ]
        scenes.write_scenes("scenes-gen", shots, root=tmp_path)
        new = tmp_path / ".brandly" / "scenes-gen" / "docs" / "general" / "scenes.json"
        assert new.exists(), "the scene manifest must live at docs/general/ (#299)"

    def test_readers_accept_legacy_plan_location(self, tmp_path: Path) -> None:
        """Back-compat: a pre-existing project with concept.md in docs/plan/
        still passes the approve gate (readers accept the legacy location)."""
        from brandly_cli.cli import _check_phase_artifacts

        _make_project(tmp_path, pid="legacy-proj")
        legacy = tmp_path / ".brandly" / "legacy-proj" / "docs" / "plan" / "concept.md"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("# Concept\n\nlegacy\n")
        missing = _check_phase_artifacts("legacy-proj", "concept", tmp_path)
        assert missing == [], "the legacy docs/plan/ concept must still be accepted"

    def test_approve_gate_accepts_new_locations(self, tmp_path: Path) -> None:
        """The approve gate reads the contract-correct locations."""
        from brandly_cli.cli import _check_phase_artifacts

        _make_project(tmp_path, pid="gate-new")
        general = tmp_path / ".brandly" / "gate-new" / "docs" / "general" / "concept.md"
        general.parent.mkdir(parents=True, exist_ok=True)
        general.write_text("# Concept\n\nnew home\n")
        assert _check_phase_artifacts("gate-new", "concept", tmp_path) == []


class TestSourceContractNoHardcodedPlanPaths:
    def test_writers_use_layout_docs_dir(self) -> None:
        """Source contract: production.py must not hardcode ``docs / "plan"``
        for categorized documents — categorized paths go through
        ``layout.docs_dir`` / ``layout.resolve_project_dir`` + the category
        constant (#298 #299). The only permitted literal is inside
        layout.py itself (the taxonomy owner)."""
        src = _read("cmd/production.py")
        offenders = [
            ln.strip()
            for ln in src.splitlines()
            if '/ "plan"' in ln
        ]
        assert not offenders, (
            f"hardcoded docs/plan paths in production.py (#298 #299): {offenders}"
        )

    def test_scenes_module_uses_general(self) -> None:
        """scenes.py resolves the manifest via the general category."""
        src = _read("scenes.py")
        assert '"general"' in src, (
            "scenes.py must resolve scenes.json via the general category (#299)"
        )


# ---------------------------------------------------------------------------
# E2 - #304: run --execute persists its transcript to docs/tmp/
# ---------------------------------------------------------------------------


class TestRunTranscript:
    def test_run_execute_writes_docs_tmp_run_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`brandly run --execute` persists a structured run transcript to
        docs/tmp/run_<ts>.log (#304) — the layout's transient-docs home."""

        import brandly_cli.cmd.production as production_mod
        from brandly_cli.cli import cli

        pid = "runlog-proj"
        _make_project(tmp_path, pid=pid)
        calls: list[str] = []

        async def fake(self: object, phase: str, proj: object) -> dict[str, object]:
            calls.append(phase)
            return {"phase": phase, "ok": True}

        monkeypatch.setattr(production_mod.Director, "_run_phase_real", fake)
        result = CliRunner().invoke(
            cli, ["--root", str(tmp_path), "run", pid, "--execute", "--yes", "--until", "init"]
        )
        assert result.exit_code == 0, result.output
        logs = list((tmp_path / ".brandly" / pid / "docs" / "tmp").glob("run_*.log"))
        assert logs, "no run transcript written to docs/tmp/ (#304)"
        text = logs[0].read_text(encoding="utf-8")
        assert "init" in text, f"the transcript must record the phases: {text!r}"


# ---------------------------------------------------------------------------
# E3a - #292: the storyboard pass has a progress log + per-shot output
# ---------------------------------------------------------------------------


class TestStoryboardPassProgress:
    def test_storyboard_pass_uses_progress_log_and_prints(self) -> None:
        """Source contract: _run_storyboard_pass consults the ProgressLog
        (approved keyframes skip regeneration) and prints per-shot lines
        (#292)."""
        src = _read("cmd/production.py")
        start = src.index("def _run_storyboard_pass")
        body = src[start : src.index("async def _run_phase_real", start)]
        assert "ProgressLog" in body, (
            "the storyboard pass must consult the ProgressLog (#292)"
        )
        assert "completed_ids" in body, (
            "approved keyframes must skip regeneration on re-run (#292)"
        )
        assert body.count("Keyframe for") >= 1, (
            "the pass must print per-shot lines (#292 — silent success)"
        )

    def test_asset_phase_passes_retries(self) -> None:
        """Source contract: the pipeline-path produce runner gets retries >= 1
        so a transient provider error engages the runner's backoff (#293)."""
        src = _read("cmd/production.py")
        start = src.index("if phase == \"asset\":")
        body = src[start : src.index("if phase == \"audio\":", start)]
        match = re.search(r"retries\s*=\s*(\d+)", body)
        assert match, "the asset phase must pass an explicit retries count"
        assert int(match.group(1)) >= 1, (
            "the pipeline path must not hardcode retries=0 (#293)"
        )


# ---------------------------------------------------------------------------
# E4 - #294: provider saturation is classified in the phase error
# ---------------------------------------------------------------------------


class TestProviderSaturationClassification:
    def test_asset_error_classifies_provider_saturation(self) -> None:
        """Source contract: the asset phase's failure path recognizes the
        provider-saturation signature (503 video_queue_full / ReadTimeout on
        task creation) and says so — the operator learns to wait, not fix
        (#294)."""
        src = _read("cmd/production.py")
        start = src.index("if phase == \"asset\":")
        body = src[start : src.index("if phase == \"audio\":", start)]
        assert "video_queue_full" in body or "provider_saturated" in body, (
            "the asset failure path must classify provider saturation (#294)"
        )
        assert "wait" in body.lower(), (
            "the saturation message must tell the operator to wait (#294)"
        )


# ---------------------------------------------------------------------------
# E5 - #295: the reference cap ranks canonical names above unknown files
# ---------------------------------------------------------------------------


class TestReferenceCapPriority:
    def test_canonical_names_win_the_cap(self) -> None:
        """A junk/unknown-named image never displaces a canonical keyframe or
        plate at the reference cap (#295)."""
        from brandly_cli.shot_runner import cap_reference_selection

        refs = [
            "/p/_debug_scratch.png",                      # junk — must drop first
            "/p/pre-production/x/storyboard/Scene-01-Shot-1-1-shots.jpg",
            "/p/pre-production/x/storyboard/Scene-01-Shot-1-2-shots.jpg",
            "/p/pre-production/x/character/char_theo.jpg",
            "/p/pre-production/x/wardrobe/wardrobe_coat.jpg",
            "/p/pre-production/x/storyboard/Scene-01-Shot-1-3-shots.jpg",
        ]
        kept, dropped = cap_reference_selection(refs, limit=4)
        assert any("_debug_scratch.png" in d for d in dropped), (
            f"the junk file must be dropped before canonical refs: {dropped}"
        )
        assert all("Scene-" in k or "char_" in k or "wardrobe_" in k for k in kept), (
            f"only canonical refs should survive the cap: {kept}"
        )

    def test_unknown_names_rank_last(self) -> None:
        from brandly_cli.shot_runner import _ref_priority

        assert _ref_priority("/p/x/Scene-01-Shot-1-1.jpg") < _ref_priority("/p/x/random.png")
        assert _ref_priority("/p/x/char_theo.jpg") < _ref_priority("/p/x/random.png")
        assert _ref_priority("/p/x/wardrobe_coat.jpg") < _ref_priority("/p/x/random.png")


# ---------------------------------------------------------------------------
# E6 - #297/#301/#300: the bible + casting phases and the 4x4 graphite grid
# ---------------------------------------------------------------------------


BIBLE_FIXTURE = """# Production Bible — Coffee Mug Duo

## Section 4: Characters

- **Maya**: 28, dark braids, olive skin, warm smile; charcoal wool coat over a red dress; consistency: same face and silhouette in every frame.
- **Theo**: 31, short curly hair, dark skin, navy chore jacket; consistency: same face and build in every frame.
"""


class TestBiblePhase:
    def test_bible_in_phase_order(self) -> None:
        """The bible phase sits between concept and casting (#297)."""
        from brandly_cli.constants import PHASE_ORDER

        assert "bible" in PHASE_ORDER
        idx = PHASE_ORDER.index("bible")
        assert PHASE_ORDER[idx - 1] == "concept"
        assert PHASE_ORDER[idx + 1] == "casting"

    def test_bible_phase_writes_doc(self, tmp_path: Path) -> None:
        """The bible phase derives the production bible (Section 4: Characters
        mandatory) and writes docs/bible/production_bible.md (#297)."""
        _make_project(tmp_path, pid="bible-proj", description="two people showing a coffee mug")
        _seed(tmp_path, "bible-proj", "bible")
        result = asyncio.run(
            _director(tmp_path, agent_runner=lambda p: BIBLE_FIXTURE).run_phase("bible-proj", "bible")
        )
        assert "error" not in result, result
        doc = tmp_path / ".brandly" / "bible-proj" / "docs" / "bible" / "production_bible.md"
        assert doc.exists() and "Characters" in doc.read_text(encoding="utf-8"), (
            "the bible phase must write the production bible with Section 4 (#297)"
        )

    def test_bible_phase_fails_honest_without_characters(self, tmp_path: Path) -> None:
        """A runner output without the Characters section fails honest (G11) —
        the casting flow cannot run without Section 4 (#297)."""
        _make_project(tmp_path, pid="bible-nosec", description="a test brief")
        _seed(tmp_path, "bible-nosec", "bible")
        result = asyncio.run(
            _director(tmp_path, agent_runner=lambda p: "# Bible\n\nNothing relevant.\n").run_phase(
                "bible-nosec", "bible"
            )
        )
        assert "error" in result and "Characters" in str(result["error"])


class TestCastingPhase:
    def test_casting_in_phase_order(self) -> None:
        """The casting phase sits between bible and screenplay (#301)."""
        from brandly_cli.constants import PHASE_ORDER

        assert "casting" in PHASE_ORDER
        idx = PHASE_ORDER.index("casting")
        assert PHASE_ORDER[idx - 1] == "bible"
        assert PHASE_ORDER[idx + 1] == "screenplay"

    def test_casting_phase_produces_the_cast_set(self, tmp_path: Path) -> None:
        """The casting phase reads Section 4 and generates the cast set per
        character into pre-production/<id>/character/ with the char_<name>_
        cast-* convention (#301)."""
        from unittest.mock import AsyncMock, patch

        import brandly_cli.cmd.production as production_mod
        from brandly_cli import quality_gate as qg

        _make_project(tmp_path, pid="cast-proj", description="a test brief")
        bible = tmp_path / ".brandly" / "cast-proj" / "docs" / "bible" / "production_bible.md"
        bible.parent.mkdir(parents=True, exist_ok=True)
        bible.write_text(BIBLE_FIXTURE, encoding="utf-8")
        _seed(tmp_path, "cast-proj", "casting")
        director = _director(tmp_path)

        gen_mock = AsyncMock(return_value={"url": "https://example.invalid/c.jpg"})
        gate_mock = AsyncMock(return_value=qg.GateResult(status="pass", score=92, kind="image"))

        def fake_download(url: str, dest: Path) -> Path:  # noqa: ARG001
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"fake-jpg")
            return dest

        async def _call():
            with (
                patch.object(production_mod, "generate_image", gen_mock),
                patch.object(production_mod, "download_file", AsyncMock(side_effect=fake_download)),
                patch.object(qg, "verify_element", gate_mock),
            ):
                return await director.run_phase("cast-proj", "casting")

        result = asyncio.run(_call())
        assert "error" not in result, result
        char_dir = tmp_path / "pre-production" / "cast-proj" / "character"
        cast_files = sorted(p.name for p in char_dir.glob("char_maya_cast-*.jpg"))
        assert len(cast_files) >= 3, (
            f"Maya's cast set (hero/portrait/fullbody) must land with the "
            f"char_<name>_cast-* convention: {cast_files}"
        )
        assert any("theo" in n for n in (p.name for p in char_dir.glob("*.jpg"))), (
            f"both bible characters must be cast: {sorted(p.name for p in char_dir.glob('*.jpg'))}"
        )
        # The GOLD sheet is gate-checked before it counts (#275's flow).
        assert gate_mock.await_count >= 2, "each cast sheet must pass the quality gate"


class TestStoryboardGrid:
    def test_storyboard_pass_builds_one_4col_grid(self, tmp_path: Path) -> None:
        """The storyboard pass tiles the approved panels into ONE contact
        sheet (4 columns, graphite style) — the MANDATORY grid-style-lock
        deliverable (#300)."""
        from unittest.mock import AsyncMock, patch

        import brandly_cli.cmd.production as production_mod
        from brandly_cli import quality_gate as qg
        from brandly_cli.cmd.production import Director, DirectorConfig
        from brandly_cli.project_manager import ProjectManager
        from brandly_cli.types import ProjectData

        pid = "grid-proj"
        asyncio.run(
            ProjectManager(tmp_path).create(
                ProjectData(id=pid, name="G", style="cinematic", shot_count=4, storyboards=True)
            )
        )
        shots = {
            "acts": {
                "1": {
                    "name": "one",
                    "scene": 1,
                    "shots": [
                        {"id": f"shot-{i}", "prompt": f"beat {i}", "duration": 5}
                        for i in range(1, 5)
                    ],
                }
            }
        }
        shots_path = tmp_path / ".brandly" / pid / "shots.json"
        shots_path.parent.mkdir(parents=True, exist_ok=True)
        shots_path.write_text(json.dumps(shots))

        import io as _io

        from PIL import Image as _Image

        png_buf = _io.BytesIO()
        _Image.new("RGB", (16, 9), (240, 240, 240)).save(png_buf, "PNG")
        png_bytes = png_buf.getvalue()

        def fake_download(url: str, dest: Path) -> Path:  # noqa: ARG001
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(png_bytes)
            return dest

        director = Director(DirectorConfig(tmp_path))
        gen_mock = AsyncMock(return_value={"url": "https://example.invalid/k.jpg"})
        gate_mock = AsyncMock(return_value=qg.GateResult(status="pass", score=90, kind="image"))

        proj = asyncio.run(ProjectManager(tmp_path).read(pid))

        async def _call():
            with (
                patch.object(production_mod, "_run_produce_runner", return_value=None),
                patch.object(production_mod, "generate_image", gen_mock),
                patch.object(
                    production_mod, "download_file", AsyncMock(side_effect=fake_download)
                ),
                patch.object(qg, "verify_element", gate_mock),
            ):
                return await director._run_phase_real("asset", proj)

        result = asyncio.run(_call())
        assert "error" not in result, result
        sb_dir = tmp_path / "pre-production" / pid / "storyboard"
        grids = list(sb_dir.glob("storyboard_grid_*.png"))
        assert len(grids) == 1, f"exactly ONE grid file must be written (#300): {grids}"
        # The panels carry the graphite style preamble (source contract).
        prompts = [c.args[0] for c in gen_mock.await_args_list]
        assert all("graphite pencil" in p for p in prompts), (
            "every storyboard panel prompt must carry the spec graphite preamble (#300)"
        )


# ---------------------------------------------------------------------------
# E7 - the AGENTS.md template teaches the conventions (prevention layer)
# ---------------------------------------------------------------------------


class TestAgentsTemplateTeachesTheContract:
    def test_agents_md_covers_the_layout_and_flow(self) -> None:
        """The generated AGENTS.md must teach agents the layout contract, the
        production flow, the run-log convention, and the no-junk rule — the
        prevention layer for the drift set (#297-#302, #304, #295)."""
        from brandly_cli.agent_surface import render_agents_md

        md = render_agents_md()
        for marker in (
            "docs/plan/",
            "docs/bible/",
            "docs/screenplay/",
            "docs/general/",
            "docs/tmp/",
            "run_<ts>.log",
            "trends → concept → bible → casting → screenplay",
            "graphite",
            "grid-style-lock.md",
            "NEVER drop",
        ):
            assert marker in md, f"the AGENTS.md template must teach: {marker}"
