"""Issue #121: brandly assemble - ordered final assembly from the
deterministic Scene-XX-Shot-X-Y clip names.

The runner already names clips deterministically; assembling a film meant
hand-listing 35 paths into stitch. assemble derives order from the shot
list + naming, concatenates each scene (hard cuts within a scene), then
stitches the scene segments together with the between-scenes transition,
color grade and the G4 ratio policy. Fails closed on missing shots with
their --only re-run commands.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from brandly_cli import shot_runner
from brandly_cli.assemble import plan_assembly
from brandly_cli.cli import cli

PROJECT = "asm-proj"


def _shots_payload() -> dict:
    return {
        "acts": {
            "scene1": {
                "scene": 1,
                "shots": [
                    {"id": "scene1-shot01", "prompt": "a", "duration": 4},
                    {"id": "scene1-shot02", "prompt": "b", "duration": 4},
                ],
            },
            "scene2": {
                "scene": 2,
                "shots": [{"id": "scene2-shot01", "prompt": "c", "duration": 4}],
            },
        }
    }


def _setup(root: Path) -> tuple[Path, Path]:
    proj = root / ".brandly" / PROJECT
    (proj / "docs" / "tmp").mkdir(parents=True)
    scenes = root / "production" / PROJECT / "videos" / "scenes"
    scenes.mkdir(parents=True)
    shots_path = root / "shots.json"
    shots_path.write_text(json.dumps(_shots_payload()), encoding="utf-8")
    return shots_path, scenes


def _clip(scenes: Path, name: str) -> Path:
    p = scenes / name
    p.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    return p


def _flat(shots_path: Path, images_dir: Path) -> list:
    data = shot_runner.load_shots_file(shots_path)
    return shot_runner.flatten_shots(data, images_dir)


def test_plan_assembly_groups_scenes_in_order(tmp_path: Path) -> None:
    shots_path, scenes = _setup(tmp_path)
    _clip(scenes, "Scene-01-Shot-1-1-scene1.mp4")
    _clip(scenes, "Scene-01-Shot-1-2-scene1.mp4")
    _clip(scenes, "Scene-02-Shot-2-1-scene2.mp4")
    shots = _flat(shots_path, tmp_path / "pre-production" / PROJECT)
    plan = plan_assembly(shots, scenes)
    assert plan.missing == []
    assert [s.name for s in plan.scene_clips[0]] == [
        "Scene-01-Shot-1-1-scene1.mp4",
        "Scene-01-Shot-1-2-scene1.mp4",
    ]
    assert [s.name for s in plan.scene_clips[1]] == ["Scene-02-Shot-2-1-scene2.mp4"]


def test_plan_assembly_reports_missing_shots(tmp_path: Path) -> None:
    shots_path, scenes = _setup(tmp_path)
    _clip(scenes, "Scene-01-Shot-1-1-scene1.mp4")  # shot 1-2 and scene 2 missing
    shots = _flat(shots_path, tmp_path / "pre-production" / PROJECT)
    plan = plan_assembly(shots, scenes)
    assert sorted(plan.missing) == ["scene1-shot02", "scene2-shot01"]


def _mock_edits(monkeypatch, calls: dict) -> None:  # type: ignore[no-untyped-def]
    async def fake_concat(inputs, output, **kwargs):  # type: ignore[no-untyped-def]
        calls.setdefault("concat", []).append(([str(Path(i).name) for i in inputs], str(output)))
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"seg")
        return {"output_path": str(out)}

    async def fake_stitch(clips, output, **kwargs):  # type: ignore[no-untyped-def]
        calls.setdefault("stitch", []).append(
            ([str(Path(c).name) for c in clips], str(output), kwargs)
        )
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"final")
        return {"output_path": str(out), "duration_seconds": 12.0}

    monkeypatch.setattr("brandly_cli.edit.concatenate_videos", fake_concat)
    monkeypatch.setattr("brandly_cli.stitch.stitch_videos", fake_stitch)


def test_assemble_cli_orchestrates_concat_then_stitch(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    shots_path, scenes = _setup(tmp_path)
    _clip(scenes, "Scene-01-Shot-1-1-scene1.mp4")
    _clip(scenes, "Scene-01-Shot-1-2-scene1.mp4")
    _clip(scenes, "Scene-02-Shot-2-1-scene2.mp4")
    calls: dict = {}
    _mock_edits(monkeypatch, calls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "assemble", PROJECT,
            "--shots", str(shots_path),
            "--ratio", "2.39:1",
            "--color-grade", "cinematic",
        ],
        env={"ROOT": str(tmp_path)},
    )
    assert result.exit_code == 0, result.output
    # one concat for the two-clip scene; none for the single-clip scene
    assert len(calls.get("concat", [])) == 1
    assert calls["concat"][0][0] == ["Scene-01-Shot-1-1-scene1.mp4", "Scene-01-Shot-1-2-scene1.mp4"]
    # final stitch got both segments + the ratio + grade
    assert len(calls.get("stitch", [])) == 1
    clip_names, out_path, kwargs = calls["stitch"][0]
    assert len(clip_names) == 2
    assert kwargs.get("ratio") == "2.39:1"
    assert kwargs.get("color_grade") == "cinematic"
    assert str(out_path).endswith("final.mp4")


def test_assemble_cli_fails_closed_on_missing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    shots_path, scenes = _setup(tmp_path)
    _clip(scenes, "Scene-01-Shot-1-1-scene1.mp4")  # two shots missing
    calls: dict = {}
    _mock_edits(monkeypatch, calls)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["assemble", PROJECT, "--shots", str(shots_path)],
        env={"ROOT": str(tmp_path)},
    )
    assert result.exit_code == 1
    assert "--only scene1-shot02" in result.output
    assert "--only scene2-shot01" in result.output
    assert calls.get("stitch") is None
