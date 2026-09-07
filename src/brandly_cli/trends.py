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
