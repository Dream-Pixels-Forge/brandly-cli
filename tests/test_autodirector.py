"""Tests for the surviving autodirector utilities (script parsing, prompts).

G2 PR D (audit F3/F4): the fabricated ``auto_direct`` pipeline stub was
DELETED — the real pipeline is ``brandly run --execute``
(``Director.run_pipeline`` in ``cmd/production.py``).  The regression test
below pins the removal so the stub cannot come back.
"""

from __future__ import annotations

from brandly_cli import autodirector


class TestAutoDirectRemoval:
    """The auto_direct stub is gone (G2 PR D)."""

    def test_auto_direct_is_not_defined(self) -> None:
        assert not hasattr(autodirector, "auto_direct")


class TestScriptParsing:
    """Tests for script parsing."""

    def test_parse_empty_script(self) -> None:
        """Empty script returns empty list."""
        scenes = autodirector.parse_script("")
        assert scenes == []

    def test_parse_simple_script(self) -> None:
        """Simple script with one paragraph."""
        script = "This is a test script."
        scenes = autodirector.parse_script(script)
        assert len(scenes) == 1
        assert scenes[0]["text"] == "This is a test script."

    def test_parse_multi_paragraph(self) -> None:
        """Script with multiple paragraphs."""
        script = "Scene 1\n\nScene 2\n\nScene 3"
        scenes = autodirector.parse_script(script)
        assert len(scenes) == 3

    def test_parse_with_titles(self) -> None:
        """Script with titled scenes."""
        script = "Title 1: Description 1\n\nTitle 2: Description 2"
        scenes = autodirector.parse_script(script)
        assert scenes[0]["title"] == "Title 1"
        assert scenes[1]["title"] == "Title 2"

    def test_parse_preserves_content(self) -> None:
        """Full content is preserved in scene."""
        script = "First paragraph\n\nSecond paragraph"
        scenes = autodirector.parse_script(script)
        assert len(scenes) == 2
        assert "First paragraph" in scenes[0]["full"]
        assert "Second paragraph" in scenes[1]["full"]


class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_generate_single_prompt(self) -> None:
        """Generate prompts for a scene."""
        scene = {"text": "Product demo", "title": "Demo"}
        prompts = autodirector.generate_scene_prompt(scene, "cinematic", 3)
        assert len(prompts) == 3
        assert all("cinematic" in p for p in prompts)

    def test_generate_prompts_includes_shot_numbers(self) -> None:
        """Prompts include shot numbers."""
        scene = {"text": "Test", "title": ""}
        prompts = autodirector.generate_scene_prompt(scene, "commercial", 2)
        assert "Shot 1" in prompts[0]
        assert "Shot 2" in prompts[1]
