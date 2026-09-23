"""Reference-sheet prompt building for ``brandly reference``.

Subject types map to brandly's built-in sheet skills and template their
GOLD-grade primary reference prompts. Moved out of cli.py (structural
split, no behavioral change).
"""

from __future__ import annotations

# Subject types that map to brandly's built-in sheet skills.
REFERENCE_SUBJECTS: dict[str, str] = {
    "object": "brandly-object-sheet",
    "character": "brandly-character-sheet",
    "location": "brandly-location-sheet",
    "vehicle": "brandly-vehicle-sheet",
    "animal": "brandly-animal-sheet",
    "plant": "brandly-plant-sheet",
    "mecha": "brandly-mecha-sheet",
}

# Per-subject prompt templates. These produce GOLD-grade primary reference
# images that downstream `brandly video` calls will auto-detect.
#
# Layout convention:
#   - object / character / vehicle / animal / plant / mecha:
#       MULTI-VIEW GRID — all views in one 16:9 image, split by columns/rows
#   - location:
#       FULL-FRAME — single wide establishing shot (16:9)
#
# Aspect ratio (16:9) is the project default; users can override with --ratio.
REFERENCE_PROMPT_TEMPLATES: dict[str, str] = {
    "object": (
        "Subject and Character\n"
        "{subject}. A single product, shown alone, with consistent material, "
        "color and form across every view. The product identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production product reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with subtle "
        "thin grey divider lines. Left two-thirds: a 3-column multi-view grid "
        "(front three-quarter, pure side profile, rear three-quarter). Right "
        "third: a single large hero front view. All views show the same "
        "product at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus across the whole board, "
        "high-resolution photorealistic texture with sharp definition of "
        "materials and surface detail, neutral color temperature with no "
        "color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "environment context, no dramatic shadows, no oversaturated colors."
    ),
    "character": (
        "Subject and Character\n"
        "{subject}. The character identity is strictly consistent across all "
        "views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production character reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. The layout features a 2 by 2 grid in "
        "the left two-thirds of the frame, consisting of 2 equal square "
        "panels: top left is an extreme close-up of the face from eyes to "
        "chin; top right is a front-facing head and shoulders portrait; the "
        "right third of the board contains two tall vertical panels spanning "
        "the full height of the image with correct proportions, showing a "
        "full-body front-facing standing view and a full-body back standing "
        "view.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels "
        "to ensure professional clarity. Shot with an 85mm lens, f/8 for "
        "deep focus across the entire board, high-resolution photorealistic "
        "texture, sharp definition of fabric weaves and skin pores, neutral "
        "color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no distorted facial "
        "features, no inconsistent character design, no dramatic shadows, "
        "no oversaturated colors."
    ),
    "location": (
        "Subject and Character\n"
        "{subject}. A single environment shown with consistent lighting, "
        "time of day and reference points across the frame.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape establishing frame filling the entire "
        "canvas, no grid, no split panels, no insets. No people. Clear "
        "architectural or environmental reference points with consistent "
        "lighting and time of day across the whole frame.\n\n"
        "Lighting and Technical\n"
        "Uniform, professional lighting matched to the stated time of day; "
        "deep focus across the frame; high-resolution photorealistic "
        "texture; neutral, accurate color grading.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no UI elements, no "
        "people, no dramatic color cast."
    ),
    "vehicle": (
        "Subject and Character\n"
        "{subject}. A single vehicle shown with consistent form, paint and "
        "detail across every view. The vehicle identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production vehicle reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (front three-quarter, pure side profile, rear "
        "three-quarter). Right third: a single large hero front three-"
        "quarter view. All views show the same vehicle at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus, high-resolution "
        "photorealistic texture with sharp definition of paint, glass and "
        "surface detail, neutral color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "environment context, no dramatic shadows, no oversaturated colors."
    ),
    "animal": (
        "Subject and Character\n"
        "{subject}. A single animal shown with consistent anatomy, coat and "
        "proportion across every view. The animal identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production animal reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (full-body side profile, head close-up with eye "
        "detail, three-quarter body). Right third: a single large hero "
        "full-body view. All views show the same animal at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus, high-resolution "
        "photorealistic texture with sharp definition of coat and features, "
        "neutral color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "habitat or environment context, no distorted anatomy, no dramatic "
        "shadows, no oversaturated colors."
    ),
    "plant": (
        "Subject and Character\n"
        "{subject}. A single plant shown with consistent foliage, structure "
        "and color across every view. The plant identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production botanical reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (full-plant overview, leaf detail close-up, "
        "stem/trunk detail). Right third: a single large hero full-plant "
        "view. All views show the same plant at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even diffused studio lighting, uniform across all panels. "
        "Shot with a 100mm macro-to-mid lens, f/11 for deep focus, "
        "high-resolution photorealistic texture with sharp definition of "
        "leaf texture and color, neutral color temperature with no color "
        "spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no soil "
        "or environment context, no distorted foliage, no dramatic shadows, "
        "no oversaturated colors."
    ),
    "mecha": (
        "Subject and Character\n"
        "{subject}. A single mecha shown with consistent proportions, "
        "panel lines, materials and detailing across every view. The mecha "
        "identity is strictly consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production mecha reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (front three-quarter, pure side profile, detail "
        "close-up of distinctive mechanical features). Right third: a "
        "single large hero front three-quarter view. All views show the "
        "same mecha at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus, high-resolution "
        "photorealistic texture with sharp definition of metal, panel "
        "lines and wear, neutral color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "environment context, no distorted structure, no dramatic shadows, "
        "no oversaturated colors."
    ),
}


def build_reference_prompt(subject_type: str, subject: str) -> str:
    """Build a subject-styled reference prompt. Returns empty string for unknown types."""
    template = REFERENCE_PROMPT_TEMPLATES.get(subject_type)
    if not template:
        return ""
    return template.format(subject=subject.strip())
