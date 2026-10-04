"""Tests for video_prompts prompt engineering module."""

from __future__ import annotations

from brandly_cli.video_prompts import (
    CAMERA_MOVES,
    LIGHTING_PRESETS,
    SHOT_TYPES,
    VIDEO_STYLE_TEMPLATES,
    ShotChain,
    apply_style_to_prompt,
    build_enhanced_video_prompt,
    build_keyframe_prompt,
    build_product_showcase_prompt,
    build_shot_fallback_prompt,
    build_single_shot_prompt,
    build_text_fallback_prompt,
    build_video_prompt,
    list_camera_moves,
    list_lighting_presets,
    list_shot_types,
    list_video_styles,
)


class TestListHelpers:
    def test_list_video_styles(self) -> None:
        styles = list_video_styles()
        assert isinstance(styles, list)
        assert "cinematic" in styles
        assert "commercial" in styles
        assert "ugc" in styles

    def test_list_camera_moves(self) -> None:
        moves = list_camera_moves()
        assert isinstance(moves, list)
        assert "push_in" in moves
        assert "static" in moves

    def test_list_lighting_presets(self) -> None:
        presets = list_lighting_presets()
        assert isinstance(presets, list)
        assert "golden_hour" in presets
        assert "studio" in presets

    def test_list_shot_types(self) -> None:
        types = list_shot_types()
        assert isinstance(types, list)
        assert "medium" in types
        assert "close_up" in types


class TestApplyStyleToPrompt:
    def test_cinematic_appends_suffix(self) -> None:
        result = apply_style_to_prompt("a cat walking", "cinematic")
        assert "anamorphic" in result

    def test_commercial_appends_suffix(self) -> None:
        result = apply_style_to_prompt("product on table", "commercial")
        assert "clean product focus" in result

    def test_ugc_appends_suffix(self) -> None:
        result = apply_style_to_prompt("selfie video", "ugc")
        assert "smartphone" in result

    def test_unknown_style_returns_prompt_unchanged(self) -> None:
        result = apply_style_to_prompt("hello world", "nonexistent_style")
        assert result == "hello world"

    def test_none_style_returns_prompt_unchanged(self) -> None:
        result = apply_style_to_prompt("hello", "")
        assert result == "hello"


class TestBuildVideoPrompt:
    def test_basic_multi_shot(self) -> None:
        result = build_video_prompt(
            subject="wireless earbuds",
            action="rotate on a marble surface",
            environment="minimalist desk",
            shots=3,
            style="commercial",
        )
        assert "[MASTER CONTEXT]" in result
        assert "SHOT 1" in result
        assert "SHOT 2" in result
        assert "SHOT 3" in result
        assert "wireless earbuds" in result
        assert "minimalist desk" in result

    def test_single_shot(self) -> None:
        result = build_video_prompt(
            subject="perfume bottle",
            action="glows under studio light",
            environment="dark background",
            shots=1,
            style="luxury",
        )
        assert "SHOT 1" in result
        assert "perfume bottle" in result

    def test_character_consistency_anchor(self) -> None:
        result = build_video_prompt(
            subject="woman in red dress",
            action="walks through garden",
            environment="sunlit park",
            shots=2,
            character_description="blonde woman, 30 years old, red floral dress",
            key_traits="blonde hair, red dress, tall",
        )
        assert "IDENTITY LOCK" in result
        assert "blonde woman" in result
        assert "red dress" in result

    def test_reference_image_anchor(self) -> None:
        result = build_video_prompt(
            subject="sneaker",
            action="sits on concrete",
            environment="urban street",
            shots=2,
            reference_image="https://example.com/ref.jpg",
        )
        assert "REFERENCE ANCHOR" in result
        assert "exact visual target" in result

    def test_camera_sequence_override(self) -> None:
        result = build_video_prompt(
            subject="robot",
            action="stands still",
            environment="factory floor",
            shots=2,
            camera_sequence=["dolly_in", "orbital"],
        )
        assert "dolly_in" in result
        assert "orbital" in result

    def test_style_applied(self) -> None:
        result = build_video_prompt(
            subject="watch",
            action="ticks on wrist",
            environment="luxury office",
            shots=2,
            style="cinematic",
        )
        result_lower = result.lower()
        assert "anamorphic" in result_lower or "film grain" in result_lower

    def test_invalid_style_falls_back_to_cinematic(self) -> None:
        result = build_video_prompt(
            subject="phone",
            action="displays screen",
            environment="desk",
            shots=1,
            style="nonexistent_style",
        )
        assert "[MASTER CONTEXT]" in result


class TestBuildSingleShotPrompt:
    def test_basic_single_shot(self) -> None:
        result = build_single_shot_prompt(
            subject="diamond ring",
            action="sparkles under light",
            environment="black velvet",
            camera="push_in",
            duration=5,
        )
        assert "diamond ring" in result
        assert "sparkles under light" in result
        assert "push.in" in result.replace(" ", "") or "dolly" in result.lower()
        assert "5s" in result

    def test_character_in_single_shot(self) -> None:
        result = build_single_shot_prompt(
            subject="man in suit",
            action="walks confidently",
            environment="city street",
            character_description="tall man, dark suit, confident posture",
        )
        assert "tall man" in result
        assert "dark suit" in result

    def test_reference_image_in_single_shot(self) -> None:
        result = build_single_shot_prompt(
            subject="product",
            action="sits on surface",
            environment="studio",
            reference_image="https://example.com/ref.jpg",
        )
        assert "REFERENCE ANCHOR" in result

    def test_default_style_is_cinematic(self) -> None:
        result = build_single_shot_prompt(
            subject="car",
            action="drives fast",
            environment="highway",
        )
        assert "cinematic" in result.lower() or "film" in result.lower()


class TestBuildEnhancedVideoPrompt:
    def test_base_enhancement(self) -> None:
        result = build_enhanced_video_prompt(
            prompt="sleek headphones rotating",
            style="cinematic",
        )
        assert "anamorphic" in result
        assert "[SCENE CONTEXT]" in result

    def test_with_character(self) -> None:
        result = build_enhanced_video_prompt(
            prompt="woman holding phone",
            style="commercial",
            character="blonde woman in white dress",
        )
        assert "blonde woman in white dress" in result
        assert "IDENTITY LOCK" in result

    def test_with_reference_images(self) -> None:
        refs = ["https://img1.com/a.png", "https://img2.com/b.png"]
        result = build_enhanced_video_prompt(
            prompt="product showcase",
            style="luxury",
            reference_images=refs,
        )
        assert "2 reference image" in result
        assert "REFERENCE ANCHOR" in result

    def test_none_character_and_images(self) -> None:
        result = build_enhanced_video_prompt(
            prompt="simple product",
            style="ugc",
        )
        assert "simple product" in result
        assert "[SCENE CONTEXT]" in result

    def test_reference_notes_with_exclusions(self) -> None:
        result = build_enhanced_video_prompt(
            prompt="Amélie does her makeup",
            style="cinematic",
            reference_images=["char_amelie.png", "prop_phone.png"],
            reference_notes=[
                {
                    "ref": "@char_amelie",
                    "defines": "her face, hair and clothing",
                    "exclude": "the black blazer, the grey studio background, the handbag",
                },
                {
                    "ref": "@prop_amelie_phone",
                    "defines": "her phone",
                    "exclude": "the back of the phone, its camera bump, any logo",
                },
            ],
        )
        assert "[REFERENCE NOTES]" in result
        assert "@char_amelie defines her face, hair and clothing" in result
        assert "Do not use: the black blazer, the grey studio background, the handbag." in result
        assert "@prop_amelie_phone defines her phone" in result
        assert "Do not use: the back of the phone, its camera bump, any logo." in result

    def test_reference_notes_absent_by_default(self) -> None:
        result = build_enhanced_video_prompt(
            prompt="product showcase",
            style="luxury",
            reference_images=["a.png"],
        )
        assert "[REFERENCE NOTES]" not in result
        assert "Do not use:" not in result

    def test_unknown_style_falls_back_to_cinematic(self) -> None:
        result = build_enhanced_video_prompt(
            prompt="test",
            style="nonexistent_style",
        )
        assert "test" in result


class TestBuildKeyframePrompt:
    def test_basic_keyframe(self) -> None:
        result = build_keyframe_prompt(
            first_frame_subject="raw ingredients",
            last_frame_subject="finished cake",
            transformation="baking process",
            style="commercial",
            duration=10,
        )
        assert "raw ingredients" in result
        assert "finished cake" in result
        assert "baking process" in result
        assert "10s" in result


class TestBuildProductShowcasePrompt:
    def test_basic_showcase(self) -> None:
        result = build_product_showcase_prompt(
            product_name="Premium Coffee Maker",
            product_description="stainless steel, matte black finish",
            setting="modern kitchen counter",
            shots=4,
        )
        assert "Premium Coffee Maker" in result
        assert "brand colors" in result


class TestConstants:
    def test_shot_types_complete(self) -> None:
        assert len(SHOT_TYPES) > 5
        assert "medium" in SHOT_TYPES
        assert "establishing" in SHOT_TYPES

    def test_camera_moves_complete(self) -> None:
        assert len(CAMERA_MOVES) > 5
        assert "push_in" in CAMERA_MOVES
        assert "static" in CAMERA_MOVES

    def test_lighting_presets_complete(self) -> None:
        assert len(LIGHTING_PRESETS) > 5
        assert "golden_hour" in LIGHTING_PRESETS
        assert "studio" in LIGHTING_PRESETS

    def test_video_style_templates_complete(self) -> None:
        assert len(VIDEO_STYLE_TEMPLATES) > 5
        assert "cinematic" in VIDEO_STYLE_TEMPLATES
        assert "commercial" in VIDEO_STYLE_TEMPLATES


class TestBuildVideoPromptFormatMode:
    """Brandly clip-chain grammar: unbroken takes, joins in post, no cut tokens."""

    def test_format_mode_line_declares_unbroken_takes(self) -> None:
        result = build_video_prompt(
            "Amélie", "does her makeup", "marble bathroom",
            shots=5, duration_per_shot=3,
        )
        assert "Mode: 5 unbroken takes, 15s total" in result
        assert "a join never happens inside a generation" in result

    def test_no_cut_tokens_emitted(self) -> None:
        result = build_video_prompt(
            "Amélie", "does her makeup", "marble bathroom",
            shots=3, duration_per_shot=4,
        )
        assert "CUT TO" not in result
        assert "---" not in result


class TestShotChainClipChain:
    """ShotChain speaks brandly language: handoffs, continuity suffix, no cuts words."""

    def _chain(self) -> ShotChain:
        chain = ShotChain(
            "Amélie at the bathroom counter",
            "marble bathroom, warm sun at frame right",
            carry_over=["Amélie's face", "gold hoops", "white silk blouse"],
        )
        chain.add_shot(
            "medium",
            "works a brush along her cheekbone",
            camera_move="locked_off",
            duration=3,
            ends_on="the last word of her line",
        )
        chain.add_shot(
            "close_up",
            "adjusts the lip brush, then withdraws",
            camera_move="locked_off",
            duration=2,
            ends_on="the colleague's voice stopping",
            handoff="match the finished sentence — Clip 1 ends on the last word, "
                    "Clip 2 opens on the phone already live",
        )
        return chain

    def test_carry_over_emitted_once(self) -> None:
        prompt = self._chain().build_prompt()
        assert "Carry over across all 2 clips:" in prompt
        assert "Amélie's face, gold hoops, white silk blouse" in prompt

    def test_ends_on_lines(self) -> None:
        prompt = self._chain().build_prompt()
        assert "Ends on the last word of her line." in prompt
        assert "Ends on the colleague's voice stopping." in prompt

    def test_handoff_line_uses_brandly_grammar(self) -> None:
        prompt = self._chain().build_prompt()
        assert "Clip 1→2 handoff: match the finished sentence" in prompt
        assert "CUT TO" not in prompt
        assert "---" not in prompt

    def test_clip_prompt_is_self_contained(self) -> None:
        clip2 = self._chain().clip_prompt(1)
        for fragment in (
            "[CLIP 2]",
            "adjusts the lip brush",
            "Ends on the colleague's voice stopping.",
            "[CONTINUITY] Same Amélie's face, gold hoops, white silk blouse. "
            "Continuity from Clip 1.",
            "[CONSTRAINTS]",
            "[NEGATIVE]",
        ):
            assert fragment in clip2, fragment
        assert "CUT TO" not in clip2

    def test_first_clip_has_no_continuity_suffix(self) -> None:
        clip1 = self._chain().clip_prompt(0)
        assert "[CLIP 1]" in clip1
        assert "[CONTINUITY]" not in clip1
        assert "CUT TO" not in clip1

    def test_legacy_call_still_builds(self) -> None:
        chain = ShotChain("subject", "environment")
        chain.add_shot("medium", "walks", transition="dissolve")
        prompt = chain.build_prompt()
        assert "[SHOT 1]" in prompt
        assert "DISSOLVE TO" not in prompt
        assert chain.get_shot(0)["transition"] == "dissolve"


# ---------------------------------------------------------------------------
# i2v -> t2v fallback prompt (issue: text-to-video fallback with a
# consistency-preserving structured prompt)
# ---------------------------------------------------------------------------


class TestBuildTextFallbackPrompt:
    """The pinned t2v fallback format:

    ``[character(s)], [environment], [direction], [camera], [lighting],
    [motion], [audio], [sfx], [positive constraint]`` — comma-joined, empty
    segments omitted.
    """

    def test_full_template_in_order(self) -> None:
        result = build_text_fallback_prompt(
            character="natural afro, ink-wash woman, 30s, red floral dress",
            environment="an ink-wash village at dusk",
            direction="she walks along the canal",
            camera="wide 24mm, slow push-in",
            lighting="golden hour, volumetric haze",
            motion="gentle forward dolly",
            audio="ambient water, soft footsteps",
            sfx="drums on a distant drum",
            positive_constraint="lock costume, lock hair, no extra figures",
        )
        expected = ", ".join(
            [
                "natural afro, ink-wash woman, 30s, red floral dress",
                "an ink-wash village at dusk",
                "she walks along the canal",
                "wide 24mm, slow push-in",
                "golden hour, volumetric haze",
                "gentle forward dolly",
                "ambient water, soft footsteps",
                "drums on a distant drum",
                "lock costume, lock hair, no extra figures",
            ]
        )
        assert result == expected

    def test_subset_preserves_order_and_omits_empty(self) -> None:
        result = build_text_fallback_prompt(
            character="blonde woman, 30s, red dress",
            environment="sunlit park",
            camera="medium 50mm",
            # lighting / motion / audio / sfx / positive_constraint omitted
        )
        assert result == "blonde woman, 30s, red dress, sunlit park, medium 50mm"

    def test_multiple_characters_lead_the_line(self) -> None:
        result = build_text_fallback_prompt(
            character="amélie",
            characters=["the janitor", "amélie", "a red bus"],
            environment="a rainy Parisian street",
        )
        # amélie deduped, order: primary character first, then the rest
        assert result == "amélie, the janitor, a red bus, a rainy Parisian street"

    def test_all_empty_returns_empty_string(self) -> None:
        assert build_text_fallback_prompt() == ""

    def test_no_double_or_edge_commas(self) -> None:
        result = build_text_fallback_prompt(
            character="a cat",
            # environment omitted
            lighting="studio",
            # motion / audio omitted
            sfx="purr",
        )
        assert result == "a cat, studio, purr"
        assert ", ," not in result
        assert not result.startswith(",")
        assert not result.endswith(",")


class TestBuildShotFallbackPrompt:
    """``build_shot_fallback_prompt`` maps a flattened ``Shot`` onto the same
    format, using the shot's ``character`` / ``environment`` and its structured
    layers (or the raw prompt as the direction when no structure exists)."""

    def test_structured_layers_win_over_raw_prompt(self) -> None:
        from brandly_cli import shot_runner

        shot = shot_runner.Shot(
            id="s1",
            act="",
            style="cinematic",
            folder="scenes",
            prompt="[OPTICS] wide\n[MOON] x",  # raw i2v direction, should be ignored
            duration=5,
            character="a natural-afro woman",
            environment="an ink-wash village",
            structured={
                "optics": "wide 24mm",
                "lighting": "golden hour",
                "motion": "slow push-in",
                "audio": "rain",
                "locks": "no extra figures",
            },
        )
        result = build_shot_fallback_prompt(shot)
        assert result == (
            "a natural-afro woman, an ink-wash village, wide 24mm, "
            "golden hour, slow push-in, rain, no extra figures"
        )

    def test_plain_prompt_becomes_direction(self) -> None:
        from brandly_cli import shot_runner

        shot = shot_runner.Shot(
            id="s2",
            act="",
            style="cinematic",
            folder="scenes",
            prompt="she walks along the canal",
            duration=5,
            character="a woman",
            environment="a misty harbor",
        )
        result = build_shot_fallback_prompt(shot)
        assert result == "a woman, a misty harbor, she walks along the canal"

    def test_only_character_is_honest_minimal(self) -> None:
        from brandly_cli import shot_runner

        shot = shot_runner.Shot(
            id="s3",
            act="",
            style="cinematic",
            folder="scenes",
            prompt="",  # no direction, no structure, no environment
            duration=5,
            character="a lone lighthouse keeper",
        )
        assert build_shot_fallback_prompt(shot) == "a lone lighthouse keeper"
