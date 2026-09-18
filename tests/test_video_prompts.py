"""Tests for video_prompts prompt engineering module."""

from __future__ import annotations

from brandly_cli.video_prompts import (
    CAMERA_MOVES,
    LIGHTING_PRESETS,
    SHOT_TYPES,
    VIDEO_STYLE_TEMPLATES,
    apply_style_to_prompt,
    build_enhanced_video_prompt,
    build_keyframe_prompt,
    build_product_showcase_prompt,
    build_single_shot_prompt,
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
