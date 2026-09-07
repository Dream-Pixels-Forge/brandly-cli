"""Tests for `brandly_cli.trends` module."""

from __future__ import annotations

from brandly_cli.trends import (
    TREND_DATABASE,
    list_categories,
    research_trends,
)

# ---------------------------------------------------------------------------
# research_trends — tech category
# ---------------------------------------------------------------------------


class TestResearchTrendsTech:
    async def test_tech_category_returns_formats(self) -> None:
        result = await research_trends("tech")
        assert result["category"] == "tech"
        assert isinstance(result["trending_formats"], list)
        assert len(result["trending_formats"]) == 3

    async def test_tech_formats_have_required_fields(self) -> None:
        result = await research_trends("tech")
        for fmt in result["trending_formats"]:
            assert "name" in fmt
            assert "description" in fmt
            assert "hook" in fmt
            assert "duration" in fmt
            assert "virality" in fmt


# ---------------------------------------------------------------------------
# research_trends — unknown category
# ---------------------------------------------------------------------------


class TestResearchTrendsUnknown:
    async def test_unknown_category_returns_empty_list(self) -> None:
        result = await research_trends("nonexistent")
        assert result["category"] == "nonexistent"
        assert result["trending_formats"] == []
        assert result["recommended_format"] == ""

    async def test_unknown_category_still_has_metadata(self) -> None:
        result = await research_trends("nonexistent")
        assert "platform_notes" in result
        assert "timestamp" in result


# ---------------------------------------------------------------------------
# research_trends — platform filtering
# ---------------------------------------------------------------------------


class TestResearchTrendsPlatforms:
    async def test_platform_filtering_limits_notes(self) -> None:
        result = await research_trends("tech", platforms=["tiktok"])
        assert set(result["platform_notes"].keys()) == {"tiktok"}

    async def test_platform_filtering_multiple(self) -> None:
        result = await research_trends("fashion", platforms=["youtube", "instagram"])
        assert set(result["platform_notes"].keys()) == {"youtube", "instagram"}

    async def test_no_platform_returns_all(self) -> None:
        result = await research_trends("tech")
        expected = {"tiktok", "youtube", "instagram", "twitter"}
        assert set(result["platform_notes"].keys()) == expected

    async def test_empty_platform_list(self) -> None:
        result = await research_trends("tech", platforms=[])
        assert result["platform_notes"] == {}


# ---------------------------------------------------------------------------
# list_categories
# ---------------------------------------------------------------------------


class TestListCategories:
    def test_returns_list_of_strings(self) -> None:
        cats = list_categories()
        assert isinstance(cats, list)
        assert all(isinstance(c, str) for c in cats)

    def test_all_db_categories_present(self) -> None:
        cats = list_categories()
        assert set(cats) == set(TREND_DATABASE.keys())

    def test_sorted(self) -> None:
        cats = list_categories()
        assert cats == sorted(cats)

    def test_no_duplicate_categories(self) -> None:
        cats = list_categories()
        assert len(cats) == len(set(cats))


# ---------------------------------------------------------------------------
# Recommended format has highest virality
# ---------------------------------------------------------------------------


class TestRecommendedFormat:
    async def test_tech_recommended_is_highest_virality(self) -> None:
        result = await research_trends("tech")
        assert result["recommended_format"] == "Unboxing"

    async def test_fashion_recommended_is_highest_virality(self) -> None:
        result = await research_trends("fashion")
        assert result["recommended_format"] == "Get Ready With Me"

    async def test_beauty_recommended_is_highest_virality(self) -> None:
        result = await research_trends("beauty")
        assert result["recommended_format"] == "Before/After"

    async def test_recommended_format_exists_in_formats(self) -> None:
        result = await research_trends("tech")
        names = [f["name"] for f in result["trending_formats"]]
        assert result["recommended_format"] in names

    async def test_unknown_category_no_recommendation(self) -> None:
        result = await research_trends("unknown_cat_xyz")
        assert result["recommended_format"] == ""

    async def test_formats_sorted_by_virality_descending(self) -> None:
        result = await research_trends("tech")
        virality_scores = [f["virality"] for f in result["trending_formats"]]
        assert virality_scores == sorted(virality_scores, reverse=True)
