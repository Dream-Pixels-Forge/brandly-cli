"""Contract test: G10 - Scene scorecard + bounded rework.

RED test for the scene scorecard + bounded rework increment.

The validate phase should emit a scene scorecard with:
- identity consistency
- drift
- duration fidelity
- slop

Below threshold => scene marked NEEDS_REWORK, director re-runs ONLY that scene via --only
Bounded: <=2 rework attempts per scene, then stop and report
Data honesty: missing dimension = unverified, never passing
"""

from __future__ import annotations

import json
from pathlib import Path

from brandly_cli import scenes

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION = REPO_ROOT / "src" / "brandly_cli" / "cmd" / "production.py"


def _make_scene_manifest(project_id: str, tmp_path: Path, scenes_data: list) -> None:
    manifest = {"project_id": project_id, "scenes": scenes_data}
    scenes_path = Path(tmp_path) / ".brandly" / project_id / "docs" / "plan" / "scenes.json"
    scenes_path.parent.mkdir(parents=True, exist_ok=True)
    scenes_path.write_text(json.dumps(manifest), encoding="utf-8")


def _write_clips(root: Path, project_id: str, scene_id: str, shots: list) -> None:
    videos_root = Path(root) / "production" / project_id / "videos" / "scenes"
    videos_root.mkdir(parents=True, exist_ok=True)
    for shot in shots:
        clip_path = Path(root) / "production" / project_id / "videos" / "scenes" / shot
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        clip_path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 32)


class TestSceneScorecard:
    def test_scorecard_exists(self, tmp_path: Path):
        project_id = "scorecard_test"
        _make_scene_manifest(project_id, tmp_path, [
            {"id": "scene-01", "shots": [{"id": "scene-01-shot-1", "clip": "Scene-01-Shot-1-1.mp4", "folder": "scenes"}]},
        ])
        _write_clips(tmp_path, project_id, "scene-01", ["Scene-01-Shot-1-1.mp4"])
        result = scenes.evaluate_all(project_id, root=tmp_path, gate_runner=lambda p: "pass", ai_runner=lambda p: "pass")
        assert "scenes" in result
        assert len(result["scenes"]) == 1
        scene = result["scenes"][0]
        assert "quality" in scene
        assert "scorecard" in scene["quality"]

    def test_unverified_when_no_ai(self, tmp_path: Path):
        project_id = "unverified_test"
        _make_scene_manifest(project_id, tmp_path, [
            {"id": "scene-01", "shots": [{"id": "scene-01-shot-1", "clip": "Scene-01-Shot-1-1.mp4", "folder": "scenes"}]},
        ])
        _write_clips(tmp_path, project_id, "scene-01", ["Scene-01-Shot-1-1.mp4"])
        result = scenes.evaluate_all(project_id, root=tmp_path, gate_runner=lambda p: "pass")
        scene = result["scenes"][0]
        scorecard = scene["quality"]["scorecard"]
        assert scorecard.get("unverified") is True


class TestBoundedReworkLoop:
    def test_max_attempts_constant(self):
        assert hasattr(scenes, "MAX_REWORK_ATTEMPTS")
        assert scenes.MAX_REWORK_ATTEMPTS == 2

    def test_threshold_constant(self):
        assert hasattr(scenes, "SCENE_REWORK_THRESHOLD")
        assert 0 < scenes.SCENE_REWORK_THRESHOLD <= 1.0


class TestDirectorIntegration:
    def test_director_has_only_flag(self):
        body = open("src/brandly_cli/cmd/production.py", encoding="utf-8").read()
        assert '"--only"' in body
