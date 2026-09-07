"""Tests for templates module — reusable project configurations."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from brandly_cli import templates


class TestListTemplates:
    """Tests for list_templates."""

    def test_returns_sorted_names(self) -> None:
        """Returns sorted list of template names."""
        result = asyncio.run(templates.list_templates())
        assert isinstance(result, list)
        assert result == sorted(result)

    def test_contains_known_templates(self) -> None:
        """Contains all registry templates."""
        result = asyncio.run(templates.list_templates())
        for name in templates.TEMPLATE_REGISTRY:
            assert name in result


class TestGetTemplate:
    """Tests for get_template."""

    def test_get_ig_reel(self) -> None:
        """IG Reel template has correct config."""
        result = asyncio.run(templates.get_template("ig-reel"))
        assert result["style"] == "ugc"
        assert result["duration"] == 30
        assert "tiktok" in result["platforms"]

    def test_get_yt_ad(self) -> None:
        """YouTube ad template has correct config."""
        result = asyncio.run(templates.get_template("yt-ad"))
        assert result["style"] == "commercial"
        assert result["budget"] == 500

    def test_get_unknown_raises(self) -> None:
        """Unknown template raises KeyError."""
        with pytest.raises(KeyError):
            asyncio.run(templates.get_template("nonexistent"))


class TestCreateFromTemplate:
    """Tests for create_from_template."""

    def test_create_with_overrides(self) -> None:
        """Overrides are merged into template config."""
        result = asyncio.run(
            templates.create_from_template("ig-reel", overrides={"duration": 60})
        )
        assert result["duration"] == 60
        assert result["style"] == "ugc"  # Still from template

    def test_create_without_overrides(self) -> None:
        """Works without overrides."""
        result = asyncio.run(templates.create_from_template("tiktok-product"))
        assert result["style"] == "ugc"
        assert result["duration"] == 15


class TestSaveAndLoad:
    """Tests for custom template persistence."""

    def test_save_and_load_template(self, tmp_path: Path) -> None:
        """Custom template can be saved and loaded."""
        config = {"style": "test", "shots": 3}
        asyncio.run(templates.save_template("test-template", config, root=tmp_path))

        result = asyncio.run(templates.get_custom_template("test-template", root=tmp_path))
        assert result["style"] == "test"
        assert result["shots"] == 3

    def test_list_custom_templates(self, tmp_path: Path) -> None:
        """Lists custom templates from disk."""
        asyncio.run(templates.save_template("custom1", {"a": 1}, root=tmp_path))
        asyncio.run(templates.save_template("custom2", {"b": 2}, root=tmp_path))

        result = asyncio.run(templates.list_custom_templates(root=tmp_path))
        assert "custom1" in result
        assert "custom2" in result

    def test_delete_template(self, tmp_path: Path) -> None:
        """Deletes custom template from disk."""
        asyncio.run(templates.save_template("to-delete", {"x": 1}, root=tmp_path))

        deleted = asyncio.run(templates.delete_template("to-delete", root=tmp_path))
        assert deleted is True

        # Should fail after deletion
        with pytest.raises(KeyError):
            asyncio.run(templates.get_custom_template("to-delete", root=tmp_path))

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Returns False when deleting non-existent template."""
        deleted = asyncio.run(templates.delete_template("nonexistent", root=tmp_path))
        assert deleted is False

    def test_empty_custom_templates(self, tmp_path: Path) -> None:
        """Returns empty list when no custom templates exist."""
        result = asyncio.run(templates.list_custom_templates(root=tmp_path))
        assert result == []


class TestTemplateFields:
    """Tests for template field completeness."""

    def test_all_templates_have_required_fields(self) -> None:
        """All templates have required configuration fields."""
        required = {"style", "shots", "duration", "platforms", "budget"}
        for name, config in templates.TEMPLATE_REGISTRY.items():
            assert required.issubset(set(config.keys())), \
                f"Template {name} missing: {required - set(config.keys())}"
