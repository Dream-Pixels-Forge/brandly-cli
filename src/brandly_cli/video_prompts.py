"""Cinematic video prompt engineering for Agnes AI.

Provides shot-by-shot prompt templates with character consistency,
camera control, lighting design, and reference image anchoring.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Character/Subject anchors for consistency
# ---------------------------------------------------------------------------

CHARACTER_ANCHOR_TEMPLATE = """\
ANCHOR — Character: {description}
Consistent across every shot: {key_traits}
"""


# ---------------------------------------------------------------------------
# Shot types library
# ---------------------------------------------------------------------------

SHOT_TYPES = {
    "establishing": {
        "label": "ESTABLISHING SHOT",
        "description": "Wide-angle opening, sets location and mood",
        "camera": "wide shot, 24mm lens, slow push in",
    },
    "medium": {
        "label": "MEDIUM SHOT",
        "description": "Standard framing at waist level",
        "camera": "medium shot, 50mm lens, static",
    },
    "close_up": {
        "label": "CLOSE-UP",
        "description": "Intimate framing on face or product",
        "camera": "close-up, 85mm lens, shallow depth of field",
    },
    "extreme_close_up": {
        "label": "EXTREME CLOSE-UP",
        "description": "Macro detail shot",
        "camera": "macro close-up, 100mm lens, rack focus",
    },
    "low_angle": {
        "label": "LOW ANGLE SHOT",
        "description": "Heroic, powerful perspective",
        "camera": "low angle, 35mm lens, tilting up",
    },
    "high_angle": {
        "label": "HIGH ANGLE SHOT",
        "description": "God's eye view, context",
        "camera": "high angle, 24mm lens, crane down",
    },
    "tracking": {
        "label": "TRACKING SHOT",
        "description": "Camera follows subject movement",
        "camera": "tracking shot, 50mm lens, gimbal follow",
    },
    "orbital": {
        "label": "ORBITAL SHOT",
        "description": "Camera orbits around subject",
        "camera": "orbital shot, 35mm lens, 360-degree arc",
    },
    "dutch": {
        "label": "DUTCH ANGLE",
        "description": "Tilted camera for tension",
        "camera": "dutch angle, 35mm lens, tilted 15 degrees",
    },
    "static_product": {
        "label": "PRODUCT HERO SHOT",
        "description": "Clean product showcase",
        "camera": "static product shot, 50mm lens, center-framed",
    },
    "pov": {
        "label": "POV SHOT",
        "description": "Point-of-view perspective",
        "camera": "POV shot, 35mm lens, handheld natural movement",
    },
}


# ---------------------------------------------------------------------------
# Camera movement library
# ---------------------------------------------------------------------------

CAMERA_MOVES = {
    "push_in": "[Push in] — Camera moves forward toward the subject",
    "pull_out": "[Pull out] — Camera moves backward away from the subject",
    "pan_left": "[Pan left] — Camera rotates horizontally left",
    "pan_right": "[Pan right] — Camera rotates horizontally right",
    "tilt_up": "[Tilt up] — Camera rotates vertically up",
    "tilt_down": "[Tilt down] — Camera rotates vertically down",
    "tracking": "[Tracking shot] — Camera follows the subject",
    "static": "[Static shot] — Camera remains stationary",
    "zoom_in": "[Zoom in] — Camera zooms in",
    "zoom_out": "[Zoom out] — Camera zooms out",
    "orbital": "[Orbital] — Camera orbits around the subject",
    "crane_up": "[Crane up] — Camera rises vertically",
    "crane_down": "[Crane down] — Camera lowers vertically",
    "whip_pan": "[Whip pan] — Fast horizontal camera swing",
    "dolly_in": "[Dolly in] — Camera physically moves closer",
    "dolly_out": "[Dolly out] — Camera physically moves away",
    "handheld": "[Handheld] — Natural slight camera shake",
    "locked_off": "[Locked off] — Tripod-fixed, no movement",
}


# ---------------------------------------------------------------------------
# Lighting presets
# ---------------------------------------------------------------------------

LIGHTING_PRESETS = {
    "golden_hour": {
        "description": "Warm late-afternoon sunlight",
        "tags": "golden hour, warm amber light, long shadows, sun flare, cinematic bloom",
    },
    "blue_hour": {
        "description": "Cool twilight pre-sunset",
        "tags": "blue hour, cool ambient light, street lamps glowing, soft fill",
    },
    "studio": {
        "description": "Clean studio three-point lighting",
        "tags": (
            "studio lighting, soft key light, fill from opposite side, "
            "rim light separating subject, clean background"
        ),
    },
    "neon": {
        "description": "Urban neon glow",
        "tags": (
            "neon-lit, cyan and magenta reflections, wet surface bounce, "
            "city bokeh, volumetric haze"
        ),
    },
    "natural": {
        "description": "Soft natural daylight",
        "tags": (
            "soft natural window light, diffused daylight, "
            "gentle shadows, overcast atmosphere"
        ),
    },
    "dramatic": {
        "description": "High contrast chiaroscuro",
        "tags": (
            "dramatic side lighting, deep shadows, high contrast, "
            "chiaroscuro effect, moody atmosphere"
        ),
    },
    "product_studio": {
        "description": "Commercial product lighting",
        "tags": (
            "product photography lighting, clean white background, "
            "three-point setup, soft reflections, sharp focus"
        ),
    },
    "night": {
        "description": "Nighttime with practical lights",
        "tags": (
            "night scene, practical light sources, moonlight blue fill, "
            "street lights, atmospheric depth"
        ),
    },
}


# ---------------------------------------------------------------------------
# Style presets for video
# ---------------------------------------------------------------------------

VIDEO_STYLE_TEMPLATES = {
    "commercial": {
        "suffix": (
            ", commercial quality, clean product focus, professional color grading, "
            "high-end advertisement aesthetic, crisp details, polished finish"
        ),
        "lighting": "studio",
        "camera_default": "static_product",
    },
    "cinematic": {
        "suffix": (
            ", cinematic film look, anamorphic lens flares, 2.39:1 widescreen, "
            "film grain texture, rich color grading, dramatic contrast, "
            "Hollywood production value"
        ),
        "lighting": "golden_hour",
        "camera_default": "medium",
    },
    "documentary": {
        "suffix": (
            ", documentary style, natural available light, hand-held camera work, "
            "authentic moments, raw and unpolished aesthetic, Leica M11 50mm look"
        ),
        "lighting": "natural",
        "camera_default": "tracking",
    },
    "ugc": {
        "suffix": (
            ", smartphone aesthetic, vertical 9:16, casual authentic style, "
            "natural lighting, candid moments, TikTok/Instagram Reels quality, "
            "relatable vibe"
        ),
        "lighting": "natural",
        "camera_default": "medium",
    },
    "luxury": {
        "suffix": (
            ", luxury branding, elegant slow motion, premium product showcase, "
            "minimalist composition, refined color palette, high-fashion aesthetic, "
            "soft diffusion"
        ),
        "lighting": "studio",
        "camera_default": "static_product",
    },
    "action": {
        "suffix": (
            ", dynamic action sequence, fast-paced editing feel, motion blur, "
            "energetic camera work, intense atmosphere, high-energy cinematography"
        ),
        "lighting": "dramatic",
        "camera_default": "tracking",
    },
    "lifestyle": {
        "suffix": (
            ", lifestyle photography, aspirational setting, warm inviting atmosphere, "
            "natural interactions, candid beautiful moments, Instagram aesthetic"
        ),
        "lighting": "golden_hour",
        "camera_default": "medium",
    },
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_video_prompt(
    subject: str,
    action: str,
    environment: str,
    *,
    shots: int = 3,
    style: str = "cinematic",
    character_description: str | None = None,
    key_traits: str | None = None,
    reference_image: str | None = None,
    duration_per_shot: int = 4,
    camera_sequence: list[str] | None = None,
) -> str:
    """Build a professional multi-shot video prompt for Agnes AI.

    Args:
        subject: Main subject (person, product, or object)
        action: What the subject does
        environment: Where the scene takes place
        shots: Number of shots (1-6 for best results)
        style: Video style preset (commercial, cinematic, etc.)
        character_description: Detailed character appearance for consistency
        key_traits: Key visual traits that must stay consistent
        reference_image: URL of reference image to anchor the scene
        duration_per_shot: Seconds per shot
        camera_sequence: Override camera moves for each shot
    """
    style_config = VIDEO_STYLE_TEMPLATES.get(style, VIDEO_STYLE_TEMPLATES["cinematic"])
    lighting_config = LIGHTING_PRESETS.get(
        style_config["lighting"], LIGHTING_PRESETS["golden_hour"]
    )

    # Build subject anchor if character info provided
    character_anchor = ""
    if character_description:
        traits = key_traits or "distinctive features, clothing, proportions"
        character_anchor = CHARACTER_ANCHOR_TEMPLATE.format(
            description=character_description,
            key_traits=traits,
        )

    # Reference image anchor
    reference_anchor = ""
    if reference_image:
        reference_anchor = (
            "Use the provided image as the exact visual reference. "
            "Every shot preserves the lighting, color grade, and composition of the reference.\n\n"
        )

    # Build shots
    shot_lines = []
    camera_moves = camera_sequence or list(CAMERA_MOVES.keys())[:shots]

    for i in range(shots):
        shot_type = SHOT_TYPES.get(
            list(SHOT_TYPES.keys())[i % len(SHOT_TYPES)],
            "medium",
        )
        if isinstance(shot_type, str):
            shot_type = SHOT_TYPES[shot_type]
        move = camera_moves[i % len(camera_moves)]
        move_desc = CAMERA_MOVES.get(move, "[Static shot]")

        shot_line = (
            f"SHOT {i + 1} — {shot_type['label']}:\n"
            f"{reference_anchor if i == 0 else ''}"
            f"{character_anchor if i == 0 else ''}"
            f"The camera {shot_type['camera']}, {move_desc}.\n"
            f"{subject} {action}.\n"
            f"The scene is set in {environment}.\n"
            f"Lighting: {lighting_config['tags']}.\n"
            f"{style_config['suffix']}\n"
            f"Duration: {duration_per_shot}s."
        )
        shot_lines.append(shot_line)

    master_prompt = (
        f"Master Prompt: {subject} {action} in {environment} — {style} commercial video\n\n"
        + "\n\n".join(shot_lines)
    )

    # Clean up any double-style suffixes
    import re

    master_prompt = re.sub(
        r",\s*(commercial|cinematic|documentary|ugc|luxury|action|lifestyle)\s+quality,",
        " ",
        master_prompt,
    )
    master_prompt = re.sub(r"\s{2,}", " ", master_prompt).strip()

    return master_prompt


def build_single_shot_prompt(
    subject: str,
    action: str,
    environment: str,
    *,
    style: str = "cinematic",
    camera: str = "push_in",
    duration: int = 5,
    reference_image: str | None = None,
    character_description: str | None = None,
) -> str:
    """Build a single high-quality shot prompt for Agnes AI."""
    style_config = VIDEO_STYLE_TEMPLATES.get(style, VIDEO_STYLE_TEMPLATES["cinematic"])
    lighting_config = LIGHTING_PRESETS.get(
        style_config["lighting"], LIGHTING_PRESETS["golden_hour"]
    )
    camera_desc = CAMERA_MOVES.get(camera, "[Static shot]")

    lines = []
    if reference_image:
        lines.append("Use the provided image as the exact visual reference.")
    if character_description:
        lines.append(character_description)
    lines.append(f"A {style} scene featuring {subject}.")
    lines.append(f"{subject} {action}.")
    lines.append(f"The scene takes place in {environment}.")
    lines.append(f"The camera {camera_desc}.")
    lines.append(f"Lighting: {lighting_config['tags']}.")
    # Avoid duplicating style in suffix
    suffix = style_config["suffix"]
    if suffix.startswith(","):
        suffix = suffix[1:].strip()
    lines.append(suffix)
    lines.append(f"Duration: {duration} seconds.")

    return "\n\n".join(lines)


def build_keyframe_prompt(
    first_frame_subject: str,
    last_frame_subject: str,
    transformation: str,
    *,
    style: str = "cinematic",
    duration: int = 5,
) -> str:
    """Build a prompt for keyframe-to-keyframe video generation."""
    style_config = VIDEO_STYLE_TEMPLATES.get(style, VIDEO_STYLE_TEMPLATES["cinematic"])
    lighting_config = LIGHTING_PRESETS.get(
        style_config["lighting"], LIGHTING_PRESETS["golden_hour"]
    )

    return (
        f"Keyframe transition video:\n\n"
        f"START: {first_frame_subject}\n\n"
        f"END: {last_frame_subject}\n\n"
        f"TRANSITION: {transformation}\n\n"
        f"Style: {style_config['suffix']}\n"
        f"Lighting: {lighting_config['tags']}\n"
        f"Duration: {duration}s."
    )


def build_product_showcase_prompt(
    product_name: str,
    product_description: str,
    setting: str,
    *,
    shots: int = 4,
    hero_angle: str = "front",
) -> str:
    """Build a product showcase prompt with consistent hero shots."""

    return build_video_prompt(
        subject=product_name,
        action="is showcased and displayed elegantly",
        environment=setting,
        shots=shots,
        style="commercial",
        character_description=product_description,
        key_traits="brand colors, logo placement, material texture, size proportions",
    )


def build_enhanced_video_prompt(
    prompt: str,
    style: str,
    *,
    character: str | None = None,
    reference_images: list[str] | None = None,
) -> str:
    """Enhance a video prompt with style preset and consistency hints.

    Deduplicated from Director.generate_video and CLI video command.
    """
    from brandly_cli.style_presets import apply_style_preset

    enhanced = apply_style_preset(prompt, style)
    enhanced += (
        "\n\nCharacter consistency notes: Maintain identical appearance, clothing, "
        "and physical features across all shots. No identity drift. Same object "
        "properties (color, texture, size) in every frame."
    )
    if character:
        enhanced += (
            f"\n\nCharacter reference: {character}. "
            "Maintain this exact appearance across all frames."
        )
    if reference_images:
        enhanced += (
            f"\n\nReference images provided: {len(reference_images)} image(s). "
            "Preserve exact appearance, lighting, and composition from references."
        )
    return enhanced


def apply_style_to_prompt(prompt: str, style: str) -> str:
    """Append style suffix to an existing prompt."""
    style_config = VIDEO_STYLE_TEMPLATES.get(style)
    if not style_config:
        return prompt
    return f"{prompt}{style_config['suffix']}"


def list_video_styles() -> list[str]:
    """Return available video style names."""
    return list(VIDEO_STYLE_TEMPLATES.keys())


def list_camera_moves() -> list[str]:
    """Return available camera move names."""
    return list(CAMERA_MOVES.keys())


def list_lighting_presets() -> list[str]:
    """Return available lighting preset names."""
    return list(LIGHTING_PRESETS.keys())


def list_shot_types() -> list[str]:
    """Return available shot type names."""
    return list(SHOT_TYPES.keys())
