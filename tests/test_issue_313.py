"""Issue #313: the reference cap must not drop every character identity sheet.

``_ref_priority`` (#295) ranked ``Scene-*`` storyboard keyframes (0) ABOVE
``char_/wardrobe_`` identity plates (1). During a single-protagonist run the
5-image cap kept the keyframes and dropped ALL FOUR wardrobe variants of the
protagonist — character consistency then rode on keyframes, which depict her
but are not designed as identity anchors.

Ruling (identity anchors first):
    ``char_/wardrobe_`` identity plates (0) → ``Scene-*`` keyframes (1) →
    ``loc_/prop_`` plates (2) → unknown (9). Junk still ranks last (#295).
"""

from __future__ import annotations

from brandly_cli.shot_runner import _ref_priority, cap_reference_selection


class TestIdentityAnchorsRankFirst:
    def test_char_plate_outranks_keyframe(self) -> None:
        assert (
            _ref_priority("/p/character/char_elara_act1_cast.jpg")
            < _ref_priority("/p/storyboard/Scene-02-Shot-2-1-shots.jpg")
        ), "a character identity sheet must outrank a storyboard keyframe (#313)"

    def test_wardrobe_plate_outranks_keyframe(self) -> None:
        assert (
            _ref_priority("/p/wardrobe/wardrobe_coat_red.jpg")
            < _ref_priority("/p/storyboard/Scene-01-Shot-1-3-shots.jpg")
        )

    def test_keyframe_outranks_loc_prop(self) -> None:
        assert (
            _ref_priority("/p/storyboard/Scene-01-Shot-1-1-shots.jpg")
            < _ref_priority("/p/prop/prop_earbuds.jpg")
        )

    def test_unknown_still_ranks_last(self) -> None:
        # #295 contract preserved: junk never outranks a canonical name.
        assert _ref_priority("/p/_debug_scratch.png") > _ref_priority("/p/char_x.jpg")
        assert _ref_priority("/p/_debug_scratch.png") > _ref_priority("/p/Scene-01-Shot-1-1.jpg")
        assert _ref_priority("/p/_debug_scratch.png") > _ref_priority("/p/prop_x.jpg")


class TestCapKeepsIdentityAnchors:
    def test_protagonist_sheets_survive_keyframe_flood(self) -> None:
        """The #313 repro: 24 keyframes + 4 wardrobe variants, cap 5."""
        refs = [
            f"/p/pre-production/x/storyboard/Scene-0{i // 8 + 1}-Shot-1-{i}-shots.jpg"
            for i in range(1, 25)
        ] + [
            "/p/pre-production/x/character/char_elara_act_1_cast-hero.jpg",
            "/p/pre-production/x/character/char_elara_act_2_run.jpg",
            "/p/pre-production/x/character/char_elara_act_2_studio.jpg",
            "/p/pre-production/x/character/char_elara_act_3.jpg",
        ]
        kept, dropped = cap_reference_selection(refs, 5)
        char_kept = [k for k in kept if "char_" in k]
        assert len(char_kept) >= 1, (
            "at least one character identity sheet must survive the cap (#313)"
        )
        assert all("char_" in k or "Scene-" in k for k in kept)
        assert any("Scene-" in d for d in dropped), (
            "keyframes should yield slots to identity anchors"
        )

    def test_full_protagonist_set_survives_small_keyframe_set(self) -> None:
        refs = [
            "/p/storyboard/Scene-01-Shot-1-1-shots.jpg",
            "/p/storyboard/Scene-01-Shot-1-2-shots.jpg",
            "/p/character/char_elara_act_1_cast-hero.jpg",
            "/p/character/char_elara_act_2_run.jpg",
            "/p/character/char_elara_act_2_studio.jpg",
            "/p/character/char_elara_act_3.jpg",
        ]
        kept, _dropped = cap_reference_selection(refs, 5)
        char_kept = [k for k in kept if "char_" in k]
        assert len(char_kept) == 4, (
            f"all four wardrobe variants must survive when they fit: {kept}"
        )
