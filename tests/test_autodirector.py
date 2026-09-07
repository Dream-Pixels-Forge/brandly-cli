"""Tests for autodirector module — script-to-video pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path

from brandly_cli import autodirector


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


class TestAutoDirect:
    """Tests for auto_direct function."""

    def test_autodirect_empty_script(self) -> None:
        """Empty script returns error."""
        result = asyncio.run(autodirector.auto_direct("test-1", ""))
        assert "error" in result

    def test_autodirect_valid_script(self, tmp_path: Path) -> None:
        """Valid script returns parsed scenes."""
        script = "Scene 1: Product reveal\n\nScene 2: Benefits\n\nScene 3: Call to action"
        result = asyncio.run(autodirector.auto_direct("test-1", script))
        assert "error" not in result
        assert result["scenes"] == 3
        assert result["style"] == "cinematic"

    def test_autodirect_custom_style(self, tmp_path: Path) -> None:
        """Custom style is passed through."""
        result = asyncio.run(
            autodirector.auto_direct("test-1", "Test script", style="ugc")
        )
        assert result["style"] == "ugc"


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
