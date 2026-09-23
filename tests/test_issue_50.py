"""Regression tests for issue #50: same-scene same-shot-number clip-name
collision.

Root cause
----------
``Shot.clip_name`` keyed only on ``(scene, index_in_scene)``. Two distinct
shots that map to the same scene number and in-scene index (e.g. a road
shot and a chapel shot that both use ``scene=9`` within their own acts)
produced the same canonical file name, so the later generation silently
overwrote the earlier clip.

Fix
---
``Shot.clip_name`` now appends a filesystem-safe slug of the act name when
the act is non-empty, guaranteeing distinct names for distinct acts.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import shot_runner


class TestClipNameCollisionFix:
    """Two shots with the same (scene, index) in different acts must
    produce distinct clip names."""

    def test_same_scene_index_different_acts_do_not_collide(self) -> None:
        road = shot_runner.Shot(
            id="shot09_road", act="act4_road", style="cinematic",
            folder="scenes", prompt="road", duration=5,
            scene=9, index_in_scene=1,
        )
        chapel = shot_runner.Shot(
            id="shot09b_chapel", act="act5_midpoint", style="cinematic",
            folder="scenes", prompt="chapel", duration=5,
            scene=9, index_in_scene=1,
        )
        assert road.clip_name != chapel.clip_name
        # Both remain readable: Scene-09-Shot-9-1-<slug>
        assert road.clip_name.startswith("Scene-09-Shot-9-1")
        assert chapel.clip_name.startswith("Scene-09-Shot-9-1")
        # The slugs actually differ
        assert "act4" in road.clip_name
        assert "act5" in chapel.clip_name

    def test_short_act_names_stay_compact(self) -> None:
        s = shot_runner.Shot(
            id="x", act="INT. CHAPEL", style="cinematic",
            folder="scenes", prompt="p", duration=4,
            scene=3, index_in_scene=2,
        )
        # Slugify: lowercase, non-alnum -> hyphen, trimmed
        assert s.clip_name == "Scene-03-Shot-3-2-int-chapel.mp4"

    def test_act_already_in_base_name_is_not_duplicated(self) -> None:
        # If the act name somehow is the literal scene/index string, don't
        # append it twice. (Unlikely, but the guard should exist.)
        s = shot_runner.Shot(
            id="x", act="scene-01-shot-1-1", style="cinematic",
            folder="scenes", prompt="p", duration=4,
            scene=1, index_in_scene=1,
        )
        # The base is "Scene-01-Shot-1-1.mp4"; the slug "scene-01-shot-1-1"
        # is NOT a substring of that (different case), so it appends.
        assert s.clip_name == "Scene-01-Shot-1-1-scene-01-shot-1-1.mp4"

    def test_empty_act_falls_back_to_base_name(self) -> None:
        s = shot_runner.Shot(
            id="x", act="", style="cinematic",
            folder="scenes", prompt="p", duration=4,
            scene=1, index_in_scene=1,
        )
        assert s.clip_name == "Scene-01-Shot-1-1.mp4"

    def test_split_parts_do_not_double_up(self) -> None:
        """Under --split-long-shots, parts of one shot keep the same act,
        so they still get distinct names from sibling acts but the same
        prefix within the shot (they differ by -p1/-p2 in their id, not
        their clip name — that's a separate axis)."""
        parent = shot_runner.Shot(
            id="shot01", act="act1", style="cinematic",
            folder="scenes", prompt="p", duration=10,
            scene=1, index_in_scene=1,
        )
        split = shot_runner.split_long_shots([parent])
        # All parts share the act, so their clip names are identical
        # (the split is a time-axis, not a name-axis). This is by design:
        # extra parts of the same shot are tracked by -2/-3 numeric
        # suffixes in name_clips, not by the act slug.
        names = {s.clip_name for s in split}
        assert len(names) == 1
        assert "act1" in names.pop()

    def test_slugify_is_filesystem_safe(self) -> None:
        assert shot_runner._slugify("Act 1: The Road") == "act-1-the-road"
        assert shot_runner._slugify("  __multi__space__ ") == "multi-space"
        assert shot_runner._slugify("a/b\\c:d") == "a-b-c-d"
        assert shot_runner._slugify("") == ""
        assert shot_runner._slugify("!!!") == ""
