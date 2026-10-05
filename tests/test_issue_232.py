"""Contract test: G9 — the vision gate is wired to video clips (issue #232).

RED test. The produce/validate path passed ``use_ai=False`` unconditionally, so
generated **video** was never vision-judged while stills were. The capability
already shipped in issue #171 (``_extra_video_frames``, ``judge_frames`` 1-8,
N frames in one judge call, exposed as ``--use-ai --judge-frames`` on the gate
CLI) — this suite pins the *wiring*, not a rebuild.

Policy is ``off | scene-first | all``:

* ``off``         — today's behaviour exactly (deterministic pre-checks only)
* ``scene-first`` — the **first clip of each scene** gets the vision judge
  (highest identity signal per credit); the rest stay deterministic
* ``all``         — every clip is judged

A FAIL on an AI-judged clip must fail **that scene only** and never leak into
the next one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from brandly_cli import scenes

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION = REPO_ROOT / "src" / "brandly_cli" / "cmd" / "production.py"


def _write_clips(root: Path) -> None:
    videos = root / "production" / "vidgate" / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    for n in (1, 2):
        for i in (1, 2):
            (videos / f"Scene-{n:02d}-Shot-{n}-{i}.mp4").write_bytes(
                b"\x00\x00\x00\x18ftypmp42" + b"0" * 32
            )


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    manifest: dict[str, Any] = {
        "project_id": "vidgate",
        "scenes": [
            {
                "id": f"scene-{n:02d}",
                "shots": [
                    {
                        "id": f"scene-{n:02d}-shot-{i}",
                        "clip": f"Scene-{n:02d}-Shot-{n}-{i}.mp4",
                        "folder": "scenes",
                    }
                    for i in (1, 2)
                ],
            }
            for n in (1, 2)
        ],
    }
    # scenes.json lives at .brandly/<id>/docs/plan/scenes.json (scenes.scenes_path)
    scenes_path = root / ".brandly" / "vidgate" / "docs" / "plan" / "scenes.json"
    scenes_path.parent.mkdir(parents=True, exist_ok=True)
    scenes_path.write_text(json.dumps(manifest), encoding="utf-8")
    _write_clips(root)
    return root


class TestGateAiPolicy:
    def test_policy_values_exist(self) -> None:
        assert set(scenes.GATE_AI_POLICIES) == {"off", "scene-first", "all"}
        assert scenes.DEFAULT_GATE_AI_POLICY == "scene-first"

    def test_off_is_todays_behaviour(self, project: Path) -> None:
        """`off` must never invoke the AI runner — not even once."""
        calls: list[Path] = []

        def ai_runner(p: Path) -> str:
            calls.append(p)
            return "pass"

        report = scenes.evaluate_all(
            "vidgate", root=project, gate_runner=lambda p: "pass", ai_runner=ai_runner
        )
        assert calls == [], "policy 'off' must not call the AI judge"
        assert report["verdict"] == "pass"

    def test_scene_first_judges_exactly_one_clip_per_scene(self, project: Path) -> None:
        calls: list[Path] = []

        def ai_runner(p: Path) -> str:
            calls.append(p)
            return "pass"

        report = scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=ai_runner,
            gate_ai="scene-first",
        )
        assert len(calls) == 2, f"expected 1 judged clip per scene, got {len(calls)}"
        assert len(set(calls)) == 2
        assert report["verdict"] == "pass"

    def test_all_judges_every_clip(self, project: Path) -> None:
        calls: list[Path] = []

        def ai_runner(p: Path) -> str:
            calls.append(p)
            return "pass"

        scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=ai_runner,
            gate_ai="all",
        )
        assert len(calls) == 4, f"expected all 4 clips judged, got {len(calls)}"

    def test_scene_first_uses_first_clip_of_each_scene(self, project: Path) -> None:
        judged: list[str] = []

        def ai_runner(p: Path) -> str:
            judged.append(p.name)
            return "pass"

        scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=ai_runner,
            gate_ai="scene-first",
        )
        assert judged == ["Scene-01-Shot-1-1.mp4", "Scene-02-Shot-2-1.mp4"]


class TestSceneIsolation:
    def test_ai_fail_blocks_only_its_own_scene(self, project: Path) -> None:
        """A drift verdict on scene 1 must fail scene 1 and leave scene 2 passing."""
        report = scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=lambda p: "fail" if p.name.startswith("Scene-01") else "pass",
            gate_ai="scene-first",
        )
        by_id = {s["id"]: s for s in report["scenes"]}
        assert by_id["scene-01"]["verdict"] == "fail"
        assert by_id["scene-02"]["verdict"] == "pass"
        assert report["verdict"] == "fail", "project verdict is the worst scene"

    def test_ai_warn_does_not_promote_to_fail(self, project: Path) -> None:
        report = scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=lambda p: "warn",
            gate_ai="scene-first",
        )
        by_id = {s["id"]: s for s in report["scenes"]}
        assert by_id["scene-01"]["verdict"] == "warn"
        assert report["verdict"] == "warn"

    def test_ai_crash_fails_that_scene_not_the_cli(self, project: Path) -> None:
        """A judge crash on scene 1 must fail scene 1 and leave scene 2 passing."""

        def boom(p: Path) -> str:
            if p.name.startswith("Scene-01"):
                raise RuntimeError("judge exploded")
            return "pass"

        report = scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=boom,
            gate_ai="scene-first",
        )
        by_id = {s["id"]: s for s in report["scenes"]}
        assert by_id["scene-01"]["verdict"] == "fail"
        assert by_id["scene-02"]["verdict"] == "pass"


class TestAiVerdictIsRecorded:
    def test_report_records_how_many_were_ai_judged(self, project: Path) -> None:
        """G10 needs this signal, so it must be in the per-scene report now."""
        report = scenes.evaluate_all(
            "vidgate",
            root=project,
            gate_runner=lambda p: "pass",
            ai_runner=lambda p: "pass",
            gate_ai="scene-first",
        )
        for scene_report in report["scenes"]:
            assert scene_report["quality"]["ai_checked"] == 1, (
                "each scene must record that one clip was AI-judged"
            )
            assert scene_report["quality"]["skipped"] is False

    def test_ai_checked_is_zero_when_policy_off(self, project: Path) -> None:
        report = scenes.evaluate_all(
            "vidgate", root=project, gate_runner=lambda p: "pass"
        )
        for scene_report in report["scenes"]:
            assert scene_report["quality"]["ai_checked"] == 0


class TestProduceWiring:
    def test_production_exposes_a_gate_ai_option(self) -> None:
        body = PRODUCTION.read_text(encoding="utf-8")
        assert '"--gate-ai"' in body, "produce/validate must expose --gate-ai"
        assert "GATE_AI_POLICIES" in body

    def test_production_builds_an_ai_runner_with_judge_frames(self) -> None:
        """The judge must ask for multiple frames — that is the whole point of
        judging a *clip* rather than its poster frame."""
        body = PRODUCTION.read_text(encoding="utf-8")
        assert "use_ai=True" in body, "the AI runner must actually enable the judge"
        assert "judge_frames=" in body, "AI runner must pass judge_frames (issue #171)"

    def test_validate_phase_clip_gate_is_policy_driven(self) -> None:
        """The validate-phase clip gate must not hard-code use_ai=False.

        The *keyframe* gate (images, a different code path) legitimately stays
        deterministic, so this pins the clip gate's own ``ai_gate_runner``
        instead of banning the flag repo-wide.
        """
        body = PRODUCTION.read_text(encoding="utf-8")
        assert "def ai_gate_runner(clip: Path) -> str:" in body, (
            "validate phase must define a vision-judge runner"
        )
        assert "gate_ai=gate_ai" in body, (
            "evaluate_all must receive the caller's gate_ai policy"
        )
        # No hard-coded use_ai=False may remain inside the vision runner.
        start = body.index("def ai_gate_runner(clip: Path) -> str:")
        end = body.index("# evaluate_all is sync", start)
        assert "use_ai=False" not in body[start:end], (
            "the vision runner must not disable the judge"
        )
        assert "use_ai=True" in body[start:end]

