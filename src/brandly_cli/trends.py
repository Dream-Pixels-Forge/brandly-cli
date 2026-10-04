"""Trending format research database for video production."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

TREND_DATABASE: dict[str, list[dict[str, Any]]] = {
    "tech": [
        {
            "name": "Unboxing",
            "description": "Product reveal",
            "hook": "Wait for it...",
            "duration": 15,
            "virality": 0.85,
        },
        {
            "name": "ASMR",
            "description": "Satisfying sounds",
            "hook": "Sound-focused",
            "duration": 30,
            "virality": 0.72,
        },
        {
            "name": "Comparison",
            "description": "This vs That",
            "hook": "Which is better?",
            "duration": 45,
            "virality": 0.78,
        },
    ],
    "fashion": [
        {
            "name": "Get Ready With Me",
            "description": "GRWM style",
            "hook": "Morning routine",
            "duration": 60,
            "virality": 0.82,
        },
        {
            "name": "Styling Hacks",
            "description": "Tips & tricks",
            "hook": "You've been doing it wrong",
            "duration": 30,
            "virality": 0.75,
        },
    ],
    "food": [
        {
            "name": "Recipe Reveal",
            "description": "Cooking process",
            "hook": "Secret ingredient",
            "duration": 45,
            "virality": 0.80,
        },
        {
            "name": "Taste Test",
            "description": "Reaction video",
            "hook": "First bite reaction",
            "duration": 20,
            "virality": 0.70,
        },
    ],
    "beauty": [
        {
            "name": "Before/After",
            "description": "Transformation",
            "hook": "You won't believe...",
            "duration": 30,
            "virality": 0.88,
        },
        {
            "name": "Tutorial",
            "description": "Step-by-step guide",
            "hook": "Easy hack",
            "duration": 60,
            "virality": 0.72,
        },
    ],
    "fitness": [
        {
            "name": "Workout Routine",
            "description": "Exercise demo",
            "hook": "30-day challenge",
            "duration": 45,
            "virality": 0.75,
        },
        {
            "name": "Transformation",
            "description": "Progress reveal",
            "hook": "From this to this",
            "duration": 30,
            "virality": 0.82,
        },
    ],
}

PLATFORM_NOTES: dict[str, dict[str, str]] = {
    "tiktok": {
        "tech": "Fast cuts, sound-on preferred, 15-30s optimal",
        "fashion": "GRWM and styling dominate, vertical format",
        "food": "Quick recipes and taste reactions perform best",
        "beauty": "Before/after transformations highly shareable",
        "fitness": "Short workout clips, challenge formats trend well",
    },
    "youtube": {
        "tech": "Longer unboxings and comparisons (3-10 min)",
        "fashion": "Full lookbooks and styling tutorials",
        "food": "Detailed recipe walkthroughs",
        "beauty": "In-depth tutorials and reviews",
        "fitness": "Full workout routines and progress journeys",
    },
    "instagram": {
        "tech": "Reels under 60s, carousels for comparisons",
        "fashion": "Aesthetic GRWM and outfit transitions",
        "food": "Quick recipes and food aesthetics",
        "beauty": "Transformation reels and quick tutorials",
        "fitness": "Workout snippets and progress photos",
    },
    "twitter": {
        "tech": "Quick reveals and hot takes, under 30s",
        "fashion": "Style moments and viral outfit checks",
        "food": "Food trends and quick taste reactions",
        "beauty": "Glow-up reveals and viral hacks",
        "fitness": "Transformation snapshots and motivation clips",
    },
}


async def research_trends(
    product_category: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Research trending video formats for a product category.

    Args:
        product_category: The category to research (e.g. 'tech', 'fashion').
        platforms: Optional list of platforms to filter notes for.
                   If None, all platform notes are included.

    Returns:
        Dict with category, trending_formats, recommended_format,
        platform_notes, and timestamp.
    """
    category = product_category.lower().strip()
    formats = TREND_DATABASE.get(category, [])

    # Sort by virality descending to find the recommended format
    sorted_formats = sorted(formats, key=lambda f: f["virality"], reverse=True)
    recommended = sorted_formats[0]["name"] if sorted_formats else ""

    # Filter platform notes if platforms specified (None = all, [] = none)
    all_platforms = list(PLATFORM_NOTES.keys())
    if platforms is None:
        filtered_platforms = all_platforms
    elif platforms:
        filtered_platforms = [p for p in all_platforms if p in platforms]
    else:
        filtered_platforms = []

    notes: dict[str, str] = {}
    for p in filtered_platforms:
        notes[p] = PLATFORM_NOTES[p].get(
            category, "No platform-specific notes available"
        )

    return {
        "category": category,
        "trending_formats": sorted_formats,
        "recommended_format": recommended,
        "platform_notes": notes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def list_categories() -> list[str]:
    """List all available trend categories.

    Returns:
        Sorted list of category names from the trend database.
    """
    return sorted(TREND_DATABASE.keys())


# ---------------------------------------------------------------------------
# Hashtag bank (issue: social copy + hashtags) - deterministic, seeded from
# project metadata. Everything is curated data; nothing is invented per call.
# ---------------------------------------------------------------------------

#: Per-category tag bank: a "core" set plus per-platform tags.
HASHTAG_BANK: dict[str, dict[str, Any]] = {
    "tech": {
        "core": ["Tech", "Gadgets", "Unboxing", "TechReview"],
        "platforms": {
            "tiktok": ["TikTokMadeMeBuyIt"],
            "instagram": ["Reels"],
            "youtube": ["TechYouTube"],
            "twitter": ["Tech"],
        },
    },
    "fashion": {
        "core": ["Fashion", "OOTD", "Style", "GRWM"],
        "platforms": {
            "tiktok": ["FashionTikTok"],
            "instagram": ["Reels", "StyleReels"],
            "youtube": ["Lookbook"],
            "twitter": ["Style"],
        },
    },
    "food": {
        "core": ["Food", "Foodie", "Recipe", "Cooking"],
        "platforms": {
            "tiktok": ["FoodTok"],
            "instagram": ["FoodGram"],
            "youtube": ["Cooking"],
            "twitter": ["Food"],
        },
    },
    "beauty": {
        "core": ["Beauty", "GlowUp", "Skincare", "Makeup"],
        "platforms": {
            "tiktok": ["BeautyTok"],
            "instagram": ["Reels"],
            "youtube": ["Beauty"],
            "twitter": ["GlowUp"],
        },
    },
    "fitness": {
        "core": ["Fitness", "Workout", "Gym", "Transformation"],
        "platforms": {
            "tiktok": ["FitnessTok"],
            "instagram": ["Fit"],
            "youtube": ["Workout"],
            "twitter": ["Fitness"],
        },
    },
}

#: Generic, platform-appropriate video tags (e.g. YouTube -> #Shorts #Trending).
PLATFORM_DEFAULT_HASHTAGS: dict[str, list[str]] = {
    "youtube": ["Shorts", "Trending"],
    "instagram": ["Reels", "Explore"],
    "tiktok": ["FYP", "ForYou"],
    "twitter": ["Video", "Trending"],
}

#: Style presets -> short tags.
STYLE_HASHTAGS: dict[str, list[str]] = {
    "cinematic": ["Cinematic", "4K"],
    "ugc": ["RealVibes"],
    "commercial": ["Ad"],
    "luxury": ["Luxury"],
}

#: Words never promoted to a tag when deriving subject-derived hashtags.
_HASHTAG_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at",
    "with", "my", "your", "our", "is", "are", "vs",
}


def _subject_tags(subject: str, max_tags: int = 3) -> list[str]:
    """Derive a few CamelCase tags from the user's own subject/title words.

    Only significant words (length >= 3, not a stopword) are used - this is a
    transformation of user-supplied data, not fabricated marketing copy.
    """
    import re

    out: list[str] = []
    for word in re.findall(r"[A-Za-z0-9]+", subject or ""):
        if word.lower() in _HASHTAG_STOPWORDS or len(word) < 3:
            continue
        out.append(word.capitalize())
        if len(out) >= max_tags:
            break
    return out


def build_hashtags(
    category: str | None,
    *,
    subject: str | None = None,
    style: str | None = None,
    platform: str | None = None,
    limit: int = 8,
) -> list[str]:
    """Build a deterministic, order-stable hashtag list from project metadata.

    Order (strongest first): category core tags, style tags, subject-derived
    tags, then platform tags (category-specific first, then the generic
    platform video tags). Result is deduplicated case-insensitively, capped at
    ``limit``, and each entry is prefixed with ``#``. An unknown category
    contributes no category tags (no fabrication); with no metadata at all the
    result is an empty list.
    """
    chosen: list[str] = []
    cat = (category or "").lower().strip()
    bank = HASHTAG_BANK.get(cat)
    if bank is not None:
        chosen.extend(bank.get("core", []))
    style_key = (style or "").lower().strip()
    if style_key in STYLE_HASHTAGS:
        chosen.extend(STYLE_HASHTAGS[style_key])
    if subject:
        chosen.extend(_subject_tags(subject))
    plat = (platform or "").lower().strip()
    if plat:
        if bank is not None:
            chosen.extend(bank.get("platforms", {}).get(plat, []))
        chosen.extend(PLATFORM_DEFAULT_HASHTAGS.get(plat, []))

    seen: set[str] = set()
    out: list[str] = []
    for tag in chosen:
        cleaned = str(tag).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(f"#{cleaned}")
        if len(out) >= max(1, limit):
            break
    return out
