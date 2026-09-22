"""Regression tests for issues #31-#43 (GOAL-ISSUES-31-43.md)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from brandly_cli import layout, quality_gate, shot_runner
from brandly_cli.cli import cli
from brandly_cli.project_manager import ProjectManager, sync_production_state
from brandly_cli.types import ProjectData
from brandly_cli.utils import (
    _read_production_plan_rows,
    production_plan_path,
    write_generation_plan,
)
from brandly_cli.video_prompts import (
    build_enhanced_video_prompt,
    build_single_shot_prompt,
    detect_scene_direction,
    expand_structured_prompt,
)


def _write_character_plate(dirs: Path, name: str) -> None:
    p = dirs / "character" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG")


# ---------------------------------------------------------------------------
# #42 — CONSTRAINTS (technical) vs NEGATIVE (visual) never overlap
# ---------------------------------------------------------------------------


def test_constraints_and_negative_are_separate() -> None:
    prompt = build_single_shot_prompt("Marcus at desk", "types", "dark apartment")
    assert prompt.count("[CONSTRAINTS]") == 1
    assert prompt.count("[NEGATIVE]") == 1
    # The old duplicated "Avoid:" + "Negative prompt:" lines are gone.
    assert "Negative prompt:" not in prompt
    # CONSTRAINTS carries technical limits only; visual exclusions live in NEGATIVE.
    constraints_body = prompt.split("[CONSTRAINTS]")[1].split("[NEGATIVE]")[0]
    negative_body = prompt.split("[NEGATIVE]")[1]
    assert "Avoid:" not in constraints_body
    assert "Avoid:" in negative_body


def test_enhanced_prompt_no_overlap() -> None:
    prompt = build_enhanced_video_prompt(
        "Marcus types",
        "cinematic",
        character="Marcus",
        model="agnes-video-2.5-flash",
        duration=5,
        aspect="2.39:1",
    )
    assert prompt.count("[CONSTRAINTS]") == 1
    assert prompt.count("[NEGATIVE]") == 1
    assert "Frame aspect ratio: 2.39:1" in prompt
    assert "Shot duration: exactly 5s" in prompt
    # IDENTITY LOCK only when a character is present (#38).
    assert "[IDENTITY LOCK]" in prompt
    without_char = build_enhanced_video_prompt("Marcus types", "cinematic")
    assert "[IDENTITY LOCK]" not in without_char


# ---------------------------------------------------------------------------
# #32 — scene-aware boilerplate
# ---------------------------------------------------------------------------


def test_scene_aware_boilerplate_overrides() -> None:
    prompt = build_enhanced_video_prompt(
        "Marcus in dark apartment, monitor glow",
        "cinematic",
        character="Marcus",
        shot_lighting="cool blue monitor glow, no golden hour",
        shot_grade="desaturated teal",
        shot_style="Blade Runner 2049",
    )
    assert "cool blue monitor glow, no golden hour" in prompt
    assert "desaturated teal" in prompt
    assert "Blade Runner 2049" in prompt


def test_no_boilerplate_skips_presets() -> None:
    prompt = build_enhanced_video_prompt(
        "night scene, full direction inline", "cinematic", no_boilerplate=True
    )
    assert "[LIGHTING]" not in prompt
    assert "[COLOR GRADE]" not in prompt
    assert "[VISUAL STYLE]" not in prompt
    # Technical constraints + visual negatives still present.
    assert "[CONSTRAINTS]" in prompt
    assert "[NEGATIVE]" in prompt


def test_detect_scene_direction() -> None:
    detected = detect_scene_direction(
        "scene text\n[LIGHTING] warm amber practicals\n[COLOR GRADE] teal-orange\n"
        "no_boilerplate: true"
    )
    assert detected["shot_lighting"] == "warm amber practicals"
    assert detected["shot_grade"] == "teal-orange"
    assert detected["no_boilerplate"] is True
    assert detect_scene_direction("plain prompt") == {}


# ---------------------------------------------------------------------------
# #31 — structured 8-layer prompt dicts
# ---------------------------------------------------------------------------


def test_expand_structured_prompt() -> None:
    prompt = expand_structured_prompt(
        {
            "subject": "Marcus Tyler typing",
            "emotion": "isolation",
            "optics": "35mm wide, deep focus",
            "motion": "slow push in",
            "lighting": "warm amber monitor glow",
            "style": "cyberpunk thriller, 35mm grain",
            "audio": "keystrokes, rain",
            "continuity": "after exterior establishing shot",
        },
        character="Marcus Tyler",
        duration=6,
        aspect="2.39:1",
    )
    for layer in ("[SUBJECT]", "[EMOTION]", "[OPTICS]", "[MOTION]",
                  "[LIGHTING]", "[STYLE]", "[AUDIO]", "[CONTINUITY]"):
        assert layer in prompt, layer
    assert "Marcus Tyler" in prompt
    assert "Shot duration: exactly 6s" in prompt
    assert "Frame aspect ratio: 2.39:1" in prompt


def test_expand_structured_prompt_rejects_unknown_keys() -> None:
    try:
        expand_structured_prompt({"subject": "x", "keywords": "cat, hat"})
    except ValueError as e:
        assert "keywords" in str(e)
    else:
        raise AssertionError("unknown key must raise ValueError")
    # Strings pass through untouched.
    assert expand_structured_prompt("plain text") == "plain text"


def test_flatten_shots_expands_dict_prompts(tmp_path: Path) -> None:
    shots = shot_runner.flatten_shots(
        [
            {
                "id": "s01_01",
                "prompt": {"subject": "Marcus", "emotion": "tension"},
                "duration": 6,
            }
        ],
        tmp_path / "images",
    )
    assert len(shots) == 1
    assert "[SUBJECT]" in shots[0].prompt
    assert "Marcus" in shots[0].prompt


def test_flatten_shots_character_presence(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    _write_character_plate(images_dir, "char_marcus.png")
    _write_character_plate(images_dir, "char_lee.png")
    shots = shot_runner.flatten_shots(
        {
            "character": "Marcus Tyler, black jacket; Lee Chang, grey hoodie",
            "acts": {
                "act1": {
                    "shots": [
                        {
                            "id": "s01_01",
                            "prompt": "Marcus alone at desk",
                            "refs": ["char_marcus"],
                            "characters": ["Marcus Tyler"],
                        },
                        {"id": "s01_02", "prompt": "Lee at desk", "refs": ["char_lee"]},
                    ]
                }
            },
        },
        images_dir,
    )
    # Presence-declared shot locks only the present character (#38);
    # the fallback shot locks the global roster.
    assert shots[0].character == "Marcus Tyler"
    assert shots[1].character == "Marcus Tyler, black jacket; Lee Chang, grey hoodie"


# ---------------------------------------------------------------------------
# #39 — retry/backoff logging
# ---------------------------------------------------------------------------


def test_progress_log_retry_markers(tmp_path: Path) -> None:
    log = shot_runner.ProgressLog(tmp_path / "produce_progress.txt")
    log.record("s10_04", "RETRY", 1, " timeout", retry=1, backoff=60.0)
    log.record("s10_04", "OK", 0, "", retry=1)
    assert log.completed_ids(["s10_04"]) == {"s10_04"}
    lines = log.path.read_text().splitlines()
    assert lines[0].split()[2] == "RETRY"
    assert "retry=1" in lines[0] and "backoff=60s" in lines[0]
    assert lines[1].split()[2] == "OK" and "retry=1" in lines[1]


def test_run_shots_retries_then_succeeds(tmp_path: Path) -> None:
    calls = {"n": 0}

    def generate_one(shot):
        calls["n"] += 1
        if calls["n"] <= 2:
            return False, 1, "generation timeout"
        (tmp_path / "scenes" / shot.clip_name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "scenes" / shot.clip_name).write_bytes(b"\x00")
        return True, 0, ""

    shots = shot_runner.flatten_shots(
        [{"id": "s01_01", "prompt": "x", "duration": 5}], tmp_path / "images"
    )
    log = shot_runner.ProgressLog(tmp_path / "produce_progress.txt")
    config = shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=tmp_path / "scenes",
        progress=log,
        interval=0.0,
        retries=3,
        retry_backoff=0.0,
    )
    assert shot_runner.run_shots(config) == 0
    lines = log.path.read_text().splitlines()
    assert any(x.split()[2] == "RETRY" and "generation timeout" in x for x in lines)
    assert any(x.split()[2] == "OK" and "retry=2" in x for x in lines)
    assert log.completed_ids([s.id for s in shots]) == {"s01_01"}


def test_run_shots_exhausted_retries_fail(tmp_path: Path) -> None:
    def generate_one(shot):
        return False, 1, "model error"

    shots = shot_runner.flatten_shots([{"id": "s01_01", "prompt": "x"}], tmp_path / "images")
    log = shot_runner.ProgressLog(tmp_path / "produce_progress.txt")
    config = shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=tmp_path / "scenes",
        progress=log,
        interval=0.0,
        retries=1,
        retry_backoff=0.0,
    )
    assert shot_runner.run_shots(config) == 1
    lines = log.path.read_text().splitlines()
    assert lines[0].split()[2] == "RETRY"
    assert lines[1].split()[2] == "FAIL" and "retry=1" in lines[1]
    assert log.completed_ids([s.id for s in shots]) == set()


# ---------------------------------------------------------------------------
# #35 — duration validation + splitting
# ---------------------------------------------------------------------------


def test_split_long_shots(tmp_path: Path) -> None:
    shots = shot_runner.flatten_shots(
        [
            {"id": "a", "prompt": "short", "duration": 5},
            {"id": "b", "prompt": "long", "duration": 12},
        ],
        tmp_path / "images",
    )
    split = shot_runner.split_long_shots(shots)
    ids = [s.id for s in split]
    assert ids == ["a", "b-p1", "b-p2"]
    b1 = next(s for s in split if s.id == "b-p1")
    assert b1.duration == 6
    assert "part 1 of 2" in b1.prompt
    # Originals unchanged.
    assert [s.id for s in shots] == ["a", "b"]


# ---------------------------------------------------------------------------
# #34 — gate threshold + lenient policy
# ---------------------------------------------------------------------------


def test_gate_threshold_floor() -> None:
    result = quality_gate.GateResult()
    verdict = {"quality_score": 85, "slop": 2, "distortion": 1, "verdict": "pass"}
    quality_gate._apply_ai_verdict(
        result, verdict, expect_matt_background=False, has_reference=False, threshold=90
    )
    assert result.status == quality_gate.FAIL
    assert any("below the required threshold 90" in i for i in result.issues)
    assert "score floor 90" in result.policy_line()


def test_gate_no_threshold_by_default() -> None:
    result = quality_gate.GateResult()
    verdict = {"quality_score": 85, "slop": 2, "distortion": 1, "verdict": "pass"}
    quality_gate._apply_ai_verdict(
        result, verdict, expect_matt_background=False, has_reference=False
    )
    assert result.status == quality_gate.PASS


def test_gate_lenient_raises_cutoffs() -> None:
    result = quality_gate.GateResult()
    # distortion 7/10 normally fails; the lenient cutoff is 8/10 → warning,
    # and the model's "fail" verdict is demoted to warn.
    verdict = {"quality_score": 80, "slop": 2, "distortion": 7, "verdict": "fail"}
    quality_gate._apply_ai_verdict(
        result,
        verdict,
        expect_matt_background=False,
        has_reference=False,
        lenient=True,
    )
    assert result.status == quality_gate.WARN
    assert not any("Severe distortion" in i for i in result.issues)


def test_gate_policy_line(tmp_path: Path) -> None:
    result = quality_gate.GateResult(threshold=90, score=88)
    line = result.policy_line()
    assert "score floor 90" in line and "88 below" in line


# ---------------------------------------------------------------------------
# #37 — plan filenames carry the shot id; table gets a Shot ID column
# ---------------------------------------------------------------------------


def test_generation_plan_shot_id(tmp_path: Path) -> None:
    layout.ensure_project_dirs(tmp_path / ".brandly" / "proj")
    plan, _ = write_generation_plan(
        "proj",
        "video",
        root=tmp_path,
        prompt="p",
        model="m",
        style="cinematic",
        shot_id="s01_01",
        scene=1,
        act="act1",
    )
    assert plan.name.startswith("plan_video_s01_01_")
    content = plan.read_text(encoding="utf-8")
    assert "**Shot ID:** s01_01" in content
    assert "**Scene:** 1" in content
    assert "**Act:** act1" in content
    # The production plan table now has a Shot ID column.
    table = production_plan_path("proj", root=tmp_path).read_text(encoding="utf-8")
    assert "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |" in table


def test_old_seven_column_tables_still_parse(tmp_path: Path) -> None:
    path = production_plan_path("legacy", root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Production Plan\n\n"
        "| Plan | Asset | Model | Source | Status | Created | Updated |\n"
        "|------|-------|-------|--------|--------|---------|---------|\n"
        "| plan_video_x.md | video | m | src | PENDING | t | t |\n",
        encoding="utf-8",
    )
    rows = _read_production_plan_rows(path)
    assert rows["plan_video_x.md"]["status"] == "PENDING"
    assert rows["plan_video_x.md"]["shot_id"] == ""


# ---------------------------------------------------------------------------
# #36 — project.json stays live during production
# ---------------------------------------------------------------------------


def test_sync_production_state(tmp_path: Path) -> None:
    import asyncio

    pm = ProjectManager(tmp_path)
    asyncio.run(
        pm.create(ProjectData(id="live", status="pending", shot_count=10, budget=10000))
    )
    (tmp_path / ".brandly" / "live" / "cost.json").write_text(
        json.dumps({"budget_credits": 2000}), encoding="utf-8"
    )
    synced = sync_production_state(
        tmp_path, "live", status="in_progress", current_phase="video", shot_count=65
    )
    assert synced is not None
    data = json.loads(
        (tmp_path / ".brandly" / "live" / "project.json").read_text(encoding="utf-8")
    )
    assert data["status"] == "in_progress"
    assert data["current_phase"] == "video"
    assert data["shot_count"] == 65
    # Budget reconciled with cost.json (issue #36.4: 10000 vs 2000 contradiction).
    assert data["budget"] == 2000
    # Phase-transition timestamps (issue #36.5).
    assert "video" in data["phases"]
    assert data["phases"]["video"]["started_at"]
    # Terminal completion stamps completed_at.
    sync_production_state(
        tmp_path, "live", status="complete", current_phase="video", shot_count=65
    )
    data = json.loads(
        (tmp_path / ".brandly" / "live" / "project.json").read_text(encoding="utf-8")
    )
    assert data["phases"]["video"]["completed_at"]
    assert data["status"] == "complete"


# ---------------------------------------------------------------------------
# #40 — aspect-ratio crop step
# ---------------------------------------------------------------------------


def test_apply_aspect_ratio_bad_input(tmp_path: Path) -> None:
    clip = tmp_path / "c.mp4"
    clip.write_bytes(b"x")
    # Missing file / unparseable target never raise.
    assert shot_runner.apply_aspect_ratio(tmp_path / "missing.mp4", "2.39:1") is False
    assert shot_runner.apply_aspect_ratio(clip, "not-a-ratio") is False


def test_apply_aspect_ratio_no_ffmpeg(tmp_path: Path) -> None:
    clip = tmp_path / "c.mp4"
    clip.write_bytes(b"fake")
    with patch("shutil.which", return_value=None):
        assert shot_runner.apply_aspect_ratio(clip, "2.39:1") is False
    # Clip untouched.
    assert clip.read_bytes() == b"fake"


# ---------------------------------------------------------------------------
# #43 — v2 layout + migrate
# ---------------------------------------------------------------------------


def test_migrate_moves_to_v2_layout(tmp_path: Path) -> None:
    from brandly_cli import migrate as migrate_mod

    proj_dir = tmp_path / ".brandly" / "war"
    for rel in (
        "images/character/marcus.jpg",
        "images/prop/desk.jpg",
        "videos/scenes/Scene-01-Shot-1-1.mp4",
        "audio/soundtrack/theme.mp3",
    ):
        p = proj_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"asset")

    # Dry run: nothing moves, no v2 dirs created.
    dry = migrate_mod.apply_migration(tmp_path, "war", apply=False)
    assert len(dry.moves) >= 3
    assert not (tmp_path / "pre-production").exists()

    applied = migrate_mod.apply_migration(tmp_path, "war", apply=True)
    assert applied.ok, [str(s) for s in applied.skipped]
    assert (tmp_path / "pre-production" / "war" / "character" / "marcus.jpg").is_file()
    assert (tmp_path / "production" / "war" / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4").is_file()
    assert (tmp_path / "production" / "war" / "audio" / "soundtrack" / "theme.mp3").is_file()
    # Stamped + layout-aware resolution.
    assert layout.is_v2_layout(tmp_path, "war") is True
    assert layout.resolve_media_root(tmp_path, "war", "images") == (
        tmp_path / "pre-production" / "war"
    )
    assert layout.resolve_media_root(tmp_path, "war", "videos") == (
        tmp_path / "production" / "war" / "videos"
    )


def test_legacy_layout_unchanged_for_unmigrated_project(tmp_path: Path) -> None:
    layout.ensure_project_dirs(tmp_path / ".brandly" / "old")
    assert layout.is_v2_layout(tmp_path, "old") is False
    assert layout.resolve_media_root(tmp_path, "old", "images") == (
        tmp_path / ".brandly" / "old" / "images"
    )


# ---------------------------------------------------------------------------
# #33/#41 — new commands registered + new flags
# ---------------------------------------------------------------------------


def test_new_commands_registered() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert "storyboard" in result.output
    assert "migrate" in result.output


def test_storyboard_help() -> None:
    result = CliRunner().invoke(cli, ["storyboard", "--help"])
    assert result.exit_code == 0
    assert "--shots" in result.output
    assert "--only" in result.output


def test_migrate_help() -> None:
    result = CliRunner().invoke(cli, ["migrate", "--help"])
    assert result.exit_code == 0
    assert "--apply" in result.output


def test_produce_has_new_flags() -> None:
    result = CliRunner().invoke(cli, ["produce", "--help"])
    assert result.exit_code == 0
    for flag in ("--retries", "--split-long-shots", "--aspect-ratio", "--no-plan"):
        assert flag in result.output, flag


def test_gate_has_threshold_flags() -> None:
    result = CliRunner().invoke(cli, ["gate", "--help"])
    assert result.exit_code == 0
    assert "--threshold" in result.output
    assert "--lenient" in result.output


def test_reference_has_format_flag() -> None:
    result = CliRunner().invoke(cli, ["reference", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
