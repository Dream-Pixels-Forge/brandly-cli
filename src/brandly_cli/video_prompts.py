"""Cinematic video prompt engineering for Agnes AI.

Provides shot-by-shot prompt templates with explicit sectioning:
Scene Context, Camera, Motion, Lighting, Grade, Style, and Constraints.
Each section uses precise, model-parseable language for best generation results.

Prompt section model (single source of truth, issue #42)
---------------------------------------------------------
Canonical shot order, one concern per section:

    [SUBJECT]      who/what is in the shot
    [LOCATION]     where it takes place
    [ACTION]       what happens (timecoded shots)
    [CAMERA]       framing, angle, movement, lens
    [STYLE]        visual style (60:30:10 rule)
    [CONSTRAINTS]  TECHNICAL limits only: model caps, duration, aspect ratio
    [NEGATIVE]     VISUAL exclusions only: what the frame must not look like
    [AUDIO]        dialogue, SFX, ambient
    [CONTINUITY]   links to previous/next shots

``[CONSTRAINTS]`` and ``[NEGATIVE]`` never overlap: constraints describe
hard technical ceilings (model max duration/aspect), negatives list unique
visual artifacts to avoid (deformed faces, artifacts, plastic skin). Entries
shared between the two are emitted once, under ``[NEGATIVE]``.

Scene-aware boilerplate (issue #32): when a shot specifies its own lighting,
color grade, or visual style, the generic style-preset lines must not be
appended — they actively contradict the shot's direction. Pass
``shot_lighting`` / ``shot_grade`` / ``shot_style`` (or ``no_boilerplate``)
to the builders to opt out of the preset boilerplate.

Structured prompts (issue #31): a shot's ``prompt`` may be a dict using the
8-layer film direction framework — see :func:`expand_structured_prompt`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# ---------------------------------------------------------------------------
# Section builders — each returns a single-line, model-optimized tag string
# ---------------------------------------------------------------------------


def _scene_context(environment: str, mood: str = "", scale: str = "") -> str:
    """Build the scene context line."""
    parts = [f"Setting: {environment}"]
    if scale:
        parts.append(f"Scale: {scale}")
    if mood:
        parts.append(f"Mood: {mood}")
    return " | ".join(parts)


def _camera_shot(shot_type: str, lens_mm: str, framing: str = "") -> str:
    """Build the camera line."""
    lens = f"{lens_mm}mm lens" if lens_mm else ""
    parts = [f"Camera: {shot_type}"]
    if lens:
        parts.append(lens)
    if framing:
        parts.append(f"Framing: {framing}")
    return " | ".join(parts)


def _motion(camera_move: str, subject_action: str) -> str:
    """Build the motion line."""
    parts = []
    if camera_move and camera_move != "locked_off":
        parts.append(f"Camera motion: {camera_move}")
    if subject_action:
        parts.append(f"Subject action: {subject_action}")
    return " | ".join(parts) if parts else "Camera: locked off, static"


def _lighting(style: str, preset_key: str = "") -> str:
    """Build the lighting line from a preset key."""
    config = LIGHTING_PRESETS.get(preset_key or style)
    if config:
        return f"Lighting: {config['model_tags']}"
    return "Lighting: balanced studio three-point, soft key, even fill"


def _grade(style: str) -> str:
    """Build the color grade line."""
    config = GRADE_PRESETS.get(style)
    if config:
        return f"Color grade: {config}"
    return "Color grade: natural, filmic LUT, balanced contrast"


def _style(style: str) -> str:
    """Build the style line."""
    config = VIDEO_STYLE_MODELS.get(style)
    if config:
        return f"Visual style: {config['model_tags']}"
    return "Visual style: cinematic commercial, high production value"


def _constraints(style: str) -> str:
    """Build the negative-constraint line (legacy single-line form)."""
    config = VIDEO_STYLE_MODELS.get(style)
    if config and config.get("negatives"):
        return f"Avoid: {config['negatives']}"
    return "Avoid: AI artifacts, plastic skin, oversaturation, digital smear, waxy texture"


def technical_constraints(
    style: str = "cinematic",
    *,
    model: str = "",
    duration: int | None = None,
    aspect: str | None = None,
) -> str:
    """Build a ``[CONSTRAINTS]`` block with TECHNICAL limits only (issue #42).

    Distinct from ``[NEGATIVE]`` (visual exclusions): this section states
    what the model is allowed to produce — duration ceiling, output aspect
    ratio, and the generating model — so the model cannot silently clamp or
    drift outside the plan.
    """
    lines = []
    if model:
        lines.append(f"Generating model: {model}.")
    if duration:
        lines.append(f"Shot duration: exactly {duration}s. Do not exceed it.")
    if aspect:
        lines.append(f"Frame aspect ratio: {aspect}.")
    if not lines:
        lines.append("Respect the planned duration and framing; no silent clamping.")
    return "[CONSTRAINTS]\n" + "\n".join(lines)


def negative_block(style: str = "cinematic") -> str:
    """Build a ``[NEGATIVE]`` block with visual exclusions only (issue #42).

    Contains ONLY the style's visual exclusions — technical limits belong in
    :func:`technical_constraints`, so the two sections never duplicate.
    """
    config = VIDEO_STYLE_MODELS.get(style, VIDEO_STYLE_MODELS["cinematic"])
    negatives = config.get("negatives", "") or (
        "AI artifacts, plastic skin, oversaturation, digital smear, waxy texture"
    )
    return f"[NEGATIVE] Avoid: {negatives}"


def _material(subject: str) -> str:
    """Build a [Material] line based on subject keywords."""
    subject_lower = subject.lower()
    if any(kw in subject_lower for kw in ("skin", "face", "portrait", "woman", "man", "person", "character")):
        return "Material: realistic skin texture, subsurface scattering, natural pores, subtle imperfections"
    if any(kw in subject_lower for kw in ("fabric", "cloth", "dress", "suit", "clothes", "wear")):
        return "Material: realistic fabric weave, cloth micro-detail, natural draping, thread texture visible"
    if any(kw in subject_lower for kw in ("metal", "steel", "chrome", "silver", "gold", "watch")):
        return "Material: brushed metal anisotropy, realistic reflections, surface micro-scratches"
    if any(kw in subject_lower for kw in ("glass", "crystal", "gem", "diamond", "water")):
        return "Material: realistic glass refraction, caustic light patterns, fingerprint smudges"
    if any(kw in subject_lower for kw in ("plant", "leaf", "tree", "flower", "wood")):
        return "Material: organic surface detail, natural imperfections, realistic bark/skin/scale texture"
    return ""


# ---------------------------------------------------------------------------
# Model-optimized data tables
# ---------------------------------------------------------------------------

SHOT_SPECS = {
    "establishing": {"type": "extreme wide shot", "lens": "24", "framing": "full environment, subject small"},
    "wide": {"type": "wide shot", "lens": "24", "framing": "subject + environment context"},
    "medium": {"type": "medium shot", "lens": "50", "framing": "waist-up, centered"},
    "medium_close": {"type": "medium close-up", "lens": "85", "framing": "chest-up portrait"},
    "close_up": {"type": "close-up", "lens": "85", "framing": "face fills frame"},
    "extreme_close_up": {"type": "extreme close-up", "lens": "100", "framing": "detail macro, razor-thin focus"},
    "low_angle": {"type": "low angle shot", "lens": "35", "framing": "hero perspective, looking up"},
    "high_angle": {"type": "high angle shot", "lens": "24", "framing": "looking down, context overhead"},
    "over_the_shoulder": {"type": "over-the-shoulder", "lens": "50", "framing": "behind subject, focus on opposite"},
    "pov": {"type": "POV shot", "lens": "35", "framing": "eye-level, first-person view"},
    "aerial": {"type": "aerial/drone shot", "lens": "24", "framing": "bird's-eye, expansive"},
    "profile": {"type": "profile/three-quarter", "lens": "50", "framing": "side or 3/4 view"},
}

CAMERA_MOVES = {
    "static": "locked off, tripod, no movement",
    "push_in": "slow dolly push-in toward subject",
    "pull_out": "slow dolly pull-out away from subject",
    "track_left": "tracking shot moving left parallel to subject",
    "track_right": "tracking shot moving right parallel to subject",
    "tracking": "tracking shot following subject movement",
    "orbit": "360-degree orbital arc around subject",
    "tilt_up": "tilt up from feet to head",
    "tilt_down": "tilt down from head to feet",
    "pan_left": "pan left horizontally",
    "pan_right": "pan right horizontally",
    "crane_up": "crane rise vertically upward",
    "crane_down": "crane drop vertically downward",
    "whip_pan": "fast whip pan directional swing",
    "handheld": "handheld with natural micro-movement",
    "steadicam": "steadicam smooth glide follow",
    "zoom_in": "optical zoom in",
    "zoom_out": "optical zoom out",
    "rack_focus": "rack focus shift foreground to background",
    "locked_off": "locked off, no camera movement",
}

LIGHTING_PRESETS = {
    "golden_hour": {
        "model_tags": (
            "golden hour sunlight, warm amber directional light, "
            "long soft shadows, lens flare, cinematic bloom, "
            "low-angle sun, warm color temperature ~3200K"
        ),
    },
    "blue_hour": {
        "model_tags": (
            "blue hour twilight, cool ambient fill light, "
            "street lamps and practicals glowing, "
            "soft even illumination, color temperature ~7500K"
        ),
    },
    "studio": {
        "model_tags": (
            "studio three-point lighting, softbox key light, "
            "fill from opposite side at half intensity, "
            "rim light separating subject from background, "
            "clean even exposure, no harsh shadows"
        ),
    },
    "product_studio": {
        "model_tags": (
            "commercial product lighting, clean white cyc background, "
            "three-point setup with soft key, precise rim highlight, "
            "sharp edge definition, zero background distraction"
        ),
    },
    "neon": {
        "model_tags": (
            "neon-lit urban environment, cyan and magenta practicals, "
            "wet surface reflections, volumetric haze, "
            "deep shadows with colored bounce light"
        ),
    },
    "natural": {
        "model_tags": (
            "soft natural window light, diffused overcast daylight, "
            "gentle directional shadows, organic warmth, "
            "no artificial fill, ambient-only exposure"
        ),
    },
    "dramatic": {
        "model_tags": (
            "dramatic side lighting, Rembrandt triangle, "
            "deep chiaroscuro shadows, high contrast ratio 8:1, "
            "moody low-key exposure, controlled highlights"
        ),
    },
    "night": {
        "model_tags": (
            "night scene, practical light sources only, "
            "moonlight blue fill at 1/4 intensity, "
            "street lamp pools of warm light, "
            "atmospheric depth with volumetric haze"
        ),
    },
    "rembrandt": {
        "model_tags": (
            "Rembrandt portrait lighting, triangle of light on cheek, "
            "dramatic side key, soft fill, classical chiaroscuro"
        ),
    },
    "butterfly": {
        "model_tags": (
            "butterfly beauty lighting, key above and center, "
            "shadow under nose, glamorous Paramount style, "
            "even skin rendering, soft diffusion"
        ),
    },
}

GRADE_PRESETS = {
    "cinematic": (
        "teal and orange complementary grade, "
        "lifted black points for film look, "
        "soft highlight rolloff, subtle grain overlay, "
        "Kodak Vision3 500T color science"
    ),
    "commercial": (
        "clean commercial grade, vibrant saturated colors, "
        "crisp midtones, balanced whites, "
        "high-end advertising color science, "
        "no creative tint, accurate color reproduction"
    ),
    "documentary": (
        "natural documentary grade, minimal color correction, "
        "authentic skin tones, slight teal shadows, "
        "Leica M11 color profile, filmic contrast"
    ),
    "ugc": (
        "bright social media grade, high saturation, "
        "warm skin tones, lifted shadows, "
        "Instagram-filter aesthetic, clean highlights"
    ),
    "luxury": (
        "refined luxury grade, desaturated cool tones, "
        "muted gold accents, high-end editorial look, "
        "soft contrast, elegant tonal range"
    ),
    "action": (
        "dynamic action grade, punchy contrast, "
        "enhanced greens and oranges, "
        "slightly desaturated shadows, "
        "energetic color pop"
    ),
    "lifestyle": (
        "warm lifestyle grade, golden tones, "
        "soft contrast, inviting color palette, "
        "natural skin tones with slight warmth"
    ),
}

VIDEO_STYLE_MODELS = {
    "commercial": {
        "model_tags": (
            "commercial quality, clean product focus, professional color grading, "
            "high-end advertisement aesthetic, crisp details, polished finish, "
            "studio lighting, sharp focus on hero element"
        ),
        "negatives": (
            "AI slop, plastic skin, oversaturated colors, "
            "digital smear, noisy artifacts, flat lighting"
        ),
        "lighting": "studio",
    },
    "cinematic": {
        "model_tags": (
            "cinematic film look, anamorphic lens characteristics, "
            "2.39:1 widescreen aspect, film grain texture, "
            "rich color grading, dramatic contrast, Hollywood production value, "
            "Kodak Vision3 500T film stock, depth of field separation"
        ),
        "negatives": (
            "flat digital look, oversaturated, plastic skin, "
            "uncanny valley, airbrushed, cartoonish, low budget"
        ),
        "lighting": "golden_hour",
    },
    "documentary": {
        "model_tags": (
            "documentary realism, available natural light, "
            "hand-held camera aesthetic, authentic moments, "
            "raw unpolished look, Leica M11 50mm summilux character, "
            "photojournalistic composition, candid framing"
        ),
        "negatives": (
            "staged posing, artificial lighting, "
            "overproduced, studio gloss, plastic skin"
        ),
        "lighting": "natural",
    },
    "ugc": {
        "model_tags": (
            "smartphone-native aesthetic, vertical 9:16 composition, "
            "casual authentic vibe, natural lighting, "
            "candid moments, TikTok/Instagram Reels quality, "
            "relatable everyday feel, unscripted energy"
        ),
        "negatives": (
            "overproduced, studio lighting, "
            "formal posing, cinematic gloss, professional setup"
        ),
        "lighting": "natural",
    },
    "luxury": {
        "model_tags": (
            "luxury branding aesthetic, elegant slow motion, "
            "premium product showcase, minimalist composition, "
            "refined desaturated color palette, high-fashion editorial, "
            "soft optical diffusion, expensive feel"
        ),
        "negatives": (
            "cheap-looking, cluttered composition, "
            "oversaturated, plastic sheen, low production value"
        ),
        "lighting": "studio",
    },
    "action": {
        "model_tags": (
            "dynamic action sequence, fast temporal energy, "
            "motion blur on fast elements, energetic camera work, "
            "intense atmosphere, high-energy cinematography, "
            "quick cuts feel within single take, dramatic shadows"
        ),
        "negatives": (
            "static, boring, lifeless, "
            "slow pacing, flat lighting, no energy"
        ),
        "lighting": "dramatic",
    },
    "lifestyle": {
        "model_tags": (
            "lifestyle photography, aspirational setting, "
            "warm inviting atmosphere, natural interactions, "
            "candid beautiful moments, Instagram aesthetic, "
            "golden hour warmth, relatable premium feel"
        ),
        "negatives": (
            "staged, artificial, "
            "overly perfect, cold lighting, studio feel"
        ),
        "lighting": "golden_hour",
    },
    "montage": {
        "model_tags": (
            "montage sequence, rapid visual rhythm, "
            "dynamic transitions, varied shot sizes, "
            "energetic pacing, visually compelling progression"
        ),
        "negatives": (
            "monotonous, static, "
            "repetitive framing, no energy variation"
        ),
        "lighting": "studio",
    },
    "multi_shot": {
        "model_tags": (
            "multi-shot campaign, varied perspectives, "
            "consistent identity across shots, "
            "cohesive visual language, narrative progression"
        ),
        "negatives": (
            "inconsistent identity, varying lighting between shots, "
            "disconnected visual language"
        ),
        "lighting": "studio",
    },
    "continuous": {
        "model_tags": (
            "single continuous shot, unbroken takes, "
            "seamless camera choreography, real-time unfolding, "
            "immersive uninterrupted experience"
        ),
        "negatives": (
            "visible cuts, jump cuts, "
            "edited rhythm, fragmented timeline"
        ),
        "lighting": "natural",
    },
    "unboxing": {
        "model_tags": (
            "product unboxing reveal, hands opening packaging, "
            "smooth reveal motion, clean product presentation, "
            "satisfying unboxing cadence, focused on product details"
        ),
        "negatives": (
            "messy packaging, unclear product reveal, "
            "poor lighting on product, distracting background"
        ),
        "lighting": "product_studio",
    },
    "brand_short_video": {
        "model_tags": (
            "brand short video, concise narrative arc, "
            "strong hook in first 2 seconds, clear product benefit, "
            "memorable visual moment, brand-consistent aesthetic"
        ),
        "negatives": (
            "rambling narrative, weak opening, "
            "unclear product focus, generic content"
        ),
        "lighting": "studio",
    },
    "explainer_video": {
        "model_tags": (
            "explainer video style, clear information delivery, "
            "visual demonstration of concept, clean graphics overlay, "
            "educational but engaging tone, focused subject"
        ),
        "negatives": (
            "confusing visuals, cluttered composition, "
            "unclear messaging, distracting elements"
        ),
        "lighting": "studio",
    },
    "collage_motion_graphic": {
        "model_tags": (
            "motion collage aesthetic, mixed-media composition, "
            "layered visual elements, kinetic typography feel, "
            "editorial design sensibility, dynamic graphic rhythm"
        ),
        "negatives": (
            "plain static composition, "
            "no motion design, overly photographic"
        ),
        "lighting": "studio",
    },
}

# ---------------------------------------------------------------------------
# Character anchors — model-parseable identity locks
# ---------------------------------------------------------------------------

CHARACTER_ANCHOR_TEMPLATE = """\
[IDENTITY LOCK]
Subject: {description}
Fixed traits: {key_traits}
Do not vary: hair color, face shape, clothing colors, body type, accessories.
Maintain identical appearance across every frame.
"""

# ---------------------------------------------------------------------------
# Prompt builders — sectioned, model-optimized output
# ---------------------------------------------------------------------------


def _build_shot_block(
    shot_index: int,
    subject: str,
    action: str,
    environment: str,
    mood: str,
    scale: str,
    shot_type_key: str,
    camera_move: str,
    style: str,
    character_anchor: str,
    duration: int,
) -> str:
    """Build a single shot block with explicit sections."""
    spec = SHOT_SPECS.get(shot_type_key, SHOT_SPECS["medium"])
    lighting_key = VIDEO_STYLE_MODELS.get(style, {}).get("lighting", "studio")

    lines = [
        f"SHOT {shot_index}",
        _scene_context(environment, mood, scale),
        _camera_shot(spec["type"], spec["lens"], spec["framing"]),
        _motion(camera_move, action),
        f"Lighting: {LIGHTING_PRESETS.get(lighting_key, LIGHTING_PRESETS['studio'])['model_tags']}.",
        f"Color grade: {GRADE_PRESETS.get(style, GRADE_PRESETS['cinematic'])}.",
        f"Visual style: {VIDEO_STYLE_MODELS.get(style, VIDEO_STYLE_MODELS['cinematic'])['model_tags']}",
        _material(subject),
        f"Duration: {duration}s.",
    ]

    if character_anchor:
        lines.append(character_anchor)

    return "\n".join(lines)


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
    moods: list[str] | None = None,
) -> str:
    """Build a professional multi-shot video prompt with explicit sections.

    Each shot is structured as:
      SHOT N
      Setting: ... | Scale: ... | Mood: ...
      Camera: ... | Lens: ...mm | Framing: ...
      Motion: ... | Subject: ...
      Lighting: ...
      Color grade: ...
      Duration: Ns.
    """
    shot_keys = list(SHOT_SPECS.keys())
    move_keys = list(CAMERA_MOVES.keys())
    camera_moves = camera_sequence or move_keys[:shots]
    shot_types = shot_keys[:shots]

    character_anchor = ""
    if character_description:
        traits = key_traits or "distinctive features, clothing, proportions"
        character_anchor = CHARACTER_ANCHOR_TEMPLATE.format(
            description=character_description,
            key_traits=traits,
        )

    reference_anchor = ""
    if reference_image:
        reference_anchor = (
            "[REFERENCE ANCHOR]\n"
            "Use the provided image as the exact visual target.\n"
            "Preserve: lighting direction, color temperature, subject position, "
            "composition framing, and atmospheric mood from the reference.\n"
        )

    shot_lines = []
    for i in range(shots):
        mood = (moods[i] if moods and i < len(moods) else "")
        block = _build_shot_block(
            shot_index=i + 1,
            subject=subject,
            action=action,
            environment=environment,
            mood=mood,
            scale="",
            shot_type_key=shot_types[i % len(shot_types)],
            camera_move=camera_moves[i % len(camera_moves)],
            style=style,
            character_anchor=character_anchor if i == 0 else "",
            duration=duration_per_shot,
        )
        shot_lines.append(block)

    master = (
        f"[MASTER CONTEXT]\n"
        f"Product/Subject: {subject}\n"
        f"Action: {action}\n"
        f"Environment: {environment}\n"
        f"Style: {style}\n"
        f"Total shots: {shots}\n\n"
    )

    if reference_anchor:
        master += reference_anchor + "\n"

    master += "\n\n".join(shot_lines)

    # Issue #42: technical constraints and visual negatives never overlap.
    master += "\n\n" + technical_constraints(style) + "\n\n" + negative_block(style)

    return master


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
    shot_type: str = "medium",
    mood: str = "",
) -> str:
    """Build a single high-quality shot prompt with explicit sections."""
    style_config = VIDEO_STYLE_MODELS.get(style, VIDEO_STYLE_MODELS["cinematic"])
    lighting_key = style_config.get("lighting", "studio")
    spec = SHOT_SPECS.get(shot_type, SHOT_SPECS["medium"])

    lines = [
        "[SCENE CONTEXT]",
        f"Subject: {subject}",
        f"Action: {action}",
        f"Setting: {environment}",
        f"Camera: {spec['type']}, {spec['lens']}mm lens, {spec['framing']}",
        f"Motion: {CAMERA_MOVES.get(camera, 'locked off')}",
        f"Lighting: {LIGHTING_PRESETS.get(lighting_key, LIGHTING_PRESETS['studio'])['model_tags']}.",
        f"Color grade: {GRADE_PRESETS.get(style, GRADE_PRESETS['cinematic'])}.",
        _material(subject),
        f"Visual style: {style_config['model_tags']}",
        f"Duration: {duration}s.",
    ]

    if character_description:
        traits = "distinctive features, clothing, proportions"
        lines.insert(1, f"[IDENTITY LOCK] Subject: {character_description} | Fixed traits: {traits}")

    if reference_image:
        lines.insert(1, "[REFERENCE ANCHOR] Use provided image as exact visual target.")

    lines.extend(technical_constraints(style, model="", duration=duration).split("\n"))
    lines.append(negative_block(style))

    return "\n".join(lines)


def build_keyframe_prompt(
    first_frame_subject: str,
    last_frame_subject: str,
    transformation: str,
    *,
    style: str = "cinematic",
    duration: int = 5,
) -> str:
    """Build a keyframe-to-keyframe prompt with explicit sections."""
    style_config = VIDEO_STYLE_MODELS.get(style, VIDEO_STYLE_MODELS["cinematic"])
    lighting_key = style_config.get("lighting", "studio")

    return (
        f"[KEYFRAME TRANSITION]\n"
        f"Start frame: {first_frame_subject}\n"
        f"End frame: {last_frame_subject}\n"
        f"Transformation: {transformation}\n\n"
        f"[SCENE CONTEXT]\n"
        f"Camera: 50mm lens, medium shot\n"
        f"Motion: smooth morph transition\n"
        f"Lighting: {LIGHTING_PRESETS.get(lighting_key, LIGHTING_PRESETS['studio'])['model_tags']}.\n"
        f"Color grade: {GRADE_PRESETS.get(style, GRADE_PRESETS['cinematic'])}.\n"
        f"Visual style: {style_config['model_tags']}\n"
        f"Duration: {duration}s.\n\n"
        f"{technical_constraints(style, duration=duration)}\n"
        f"{negative_block(style)}"
    )


def build_product_showcase_prompt(
    product_name: str,
    product_description: str,
    setting: str,
    *,
    shots: int = 4,
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
    shot_lighting: str | None = None,
    shot_grade: str | None = None,
    shot_style: str | None = None,
    no_boilerplate: bool = False,
    model: str = "",
    duration: int | None = None,
    aspect: str | None = None,
) -> str:
    """Enhance a raw prompt with style-specific sections and constraints.

    Scene-aware boilerplate (issue #32): the generic ``[LIGHTING]`` /
    ``[COLOR GRADE]`` / ``[VISUAL STYLE]`` preset lines are replaced by the
    shot's own direction when ``shot_lighting`` / ``shot_grade`` /
    ``shot_style`` are given, and skipped entirely when ``no_boilerplate``
    is set (a shot that already carries full film direction must not be
    overwritten with generic "make it look cinematic" text).
    """
    style_config = VIDEO_STYLE_MODELS.get(style, VIDEO_STYLE_MODELS["cinematic"])
    lighting_key = style_config.get("lighting", "studio")

    sections = [f"[SCENE CONTEXT] {prompt}"]

    if not no_boilerplate:
        lighting = shot_lighting or LIGHTING_PRESETS.get(
            lighting_key, LIGHTING_PRESETS["studio"]
        )["model_tags"]
        grade = shot_grade or GRADE_PRESETS.get(style, GRADE_PRESETS["cinematic"])
        visual_style = shot_style or style_config["model_tags"]
        sections.append(f"[LIGHTING] {lighting}.")
        sections.append(f"[COLOR GRADE] {grade}.")
        sections.append(f"[VISUAL STYLE] {visual_style}")

    if character:
        # Issue #38: only characters PRESENT in the shot are locked. Callers
        # pass the presence-filtered list; an empty/None character adds no
        # identity block at all.
        sections.append(
            f"[IDENTITY LOCK] Character: {character}. "
            "Maintain identical appearance across all frames. No drift."
        )

    if reference_images:
        sections.append(
            f"[REFERENCE ANCHOR] {len(reference_images)} reference image(s) provided. "
            "Preserve exact appearance, lighting, and composition from references."
        )

    # Even fully-directed shots carry the technical ceiling: the model must
    # still respect duration/aspect/model limits (issue #42: technical
    # constraints are always emitted, independent of the boilerplate flag).
    sections.append(technical_constraints(style, model=model, duration=duration, aspect=aspect))
    sections.append(negative_block(style))

    return "\n".join(sections)


#: The 8-layer film direction framework (issue #31).
STRUCTURED_PROMPT_KEYS: tuple[str, ...] = (
    "subject",
    "emotion",
    "optics",
    "motion",
    "lighting",
    "style",
    "audio",
    "continuity",
)

#: Human-readable labels for each structured layer (block order preserved).
STRUCTURED_PROMPT_LABELS: dict[str, str] = {
    "subject": "[SUBJECT]",
    "emotion": "[EMOTION]",
    "optics": "[OPTICS]",
    "motion": "[MOTION]",
    "lighting": "[LIGHTING]",
    "style": "[STYLE]",
    "audio": "[AUDIO]",
    "continuity": "[CONTINUITY]",
}


def detect_scene_direction(prompt: str) -> dict[str, Any]:
    """Scene-aware boilerplate detection (issue #32).

    A prompt that already carries explicit ``[LIGHTING]`` / ``[COLOR
    GRADE]`` / ``[VISUAL STYLE]`` blocks (structured 8-layer prompts, or
    hand-directed shot text) must NOT have generic style-preset lines
    appended — that used to overwrite correct film direction with "golden
    hour sunlight" on a monitor-lit night scene. Returns keyword overrides
    for :func:`build_enhanced_video_prompt`; ``no_boilerplate: true``
    anywhere in the prompt opts the shot out of ALL preset boilerplate.
    """
    import re

    out: dict[str, Any] = {}
    p = prompt or ""
    m = re.search(r"\[LIGHTING\]\s*(.+)", p)
    if m:
        out["shot_lighting"] = m.group(1).strip()
    m = re.search(r"\[COLOR GRADE\]\s*(.+)", p)
    if m:
        out["shot_grade"] = m.group(1).strip()
    m = re.search(r"\[VISUAL STYLE\]\s*(.+)", p)
    if m:
        out["shot_style"] = m.group(1).strip()
    if re.search(r"no_boilerplate\s*[:=]\s*true", p, re.IGNORECASE):
        out["no_boilerplate"] = True
    return out


def expand_structured_prompt(
    prompt: Mapping[str, Any] | str,
    *,
    character: str | None = None,
    key_traits: str | None = None,
    model: str = "",
    duration: int | None = None,
    aspect: str | None = None,
) -> str:
    """Expand a structured 8-layer prompt dict into a directed prompt (issue #31).

    Accepts either a plain string (returned untouched) or a mapping whose
    keys are a subset of :data:`STRUCTURED_PROMPT_KEYS`. Unknown keys raise
    :class:`ValueError` naming the valid keys — keyword soup must fail
    loudly, not silently.

    Emits the layers in canonical order, skips empty layers, then appends
    the identity lock (only when a character is present), the technical
    ``[CONSTRAINTS]`` block and the ``[NEGATIVE]`` block (issue #42).
    """
    if isinstance(prompt, str):
        return prompt
    if not isinstance(prompt, Mapping):
        raise TypeError(
            f"prompt must be a string or a structured dict, got {type(prompt).__name__}"
        )
    unknown = [k for k in prompt if k not in STRUCTURED_PROMPT_KEYS]
    if unknown:
        raise ValueError(
            f"unknown structured-prompt key(s) {', '.join(sorted(unknown))} — "
            f"valid keys: {', '.join(STRUCTURED_PROMPT_KEYS)}"
        )

    lines = [
        f"{STRUCTURED_PROMPT_LABELS[layer]} {str(prompt[layer]).strip()}"
        for layer in STRUCTURED_PROMPT_KEYS
        if str(prompt.get(layer, "")).strip()
    ]

    if character:
        anchor = CHARACTER_ANCHOR_TEMPLATE.format(
            description=character,
            key_traits=key_traits or "distinctive features, clothing, proportions",
        )
        lines.append(anchor.rstrip())

    lines.extend(technical_constraints(model=model, duration=duration, aspect=aspect).split("\n"))
    lines.append(negative_block())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def list_video_styles() -> list[str]:
    return list(VIDEO_STYLE_MODELS.keys())


def list_camera_moves() -> list[str]:
    return list(CAMERA_MOVES.keys())


def list_lighting_presets() -> list[str]:
    return list(LIGHTING_PRESETS.keys())


def list_shot_types() -> list[str]:
    return list(SHOT_SPECS.keys())


def apply_style_to_prompt(prompt: str, style: str) -> str:
    """Append style model_tags to a prompt. Backward-compatible alias."""
    config = VIDEO_STYLE_MODELS.get(style)
    if not config:
        return prompt
    return f"{prompt}, {config['model_tags']}"


# ---------------------------------------------------------------------------
# Realism boosters — material, lighting, film stock, lens effects
# ---------------------------------------------------------------------------

REALISM_BOOSTERS = {
    "skin": {
        "natural": "realistic skin texture, subsurface scattering, natural pores, subtle imperfections, no airbrushing",
        "editorial": "editorial beauty skin, soft diffused lighting, flawless but natural complexion, minimal makeup",
        "gritty": "weathered skin, visible pores, sweat droplets, natural blemishes, authentic texture",
    },
    "materials": {
        "fabric": "realistic fabric weave, cloth micro-detail, natural draping, thread texture visible",
        "metal": "brushed metal anisotropy, realistic reflections, surface micro-scratches, chrome fingerprints",
        "glass": "realistic glass refraction, caustic light patterns, fingerprint smudges, dust particles",
        "organic": "organic surface detail, natural imperfections, realistic bark/skin/scale texture",
    },
    "lighting": {
        "global_illumination": "global illumination, realistic light bounce, color bleeding from surfaces, ambient occlusion",
        "volumetric": "volumetric lighting, atmospheric haze, light shafts through particles, god rays",
        "practical": "practical lighting only, visible light sources, realistic falloff, no artificial fill",
    },
    "film_stock": {
        "kodak_portra_400": "Kodak Portra 400 film stock, warm skin tones, soft pastels, fine grain, natural highlights",
        "kodak_vision3_500t": "Kodak Vision3 500T tungsten film, cinema look, rich shadows, controlled highlights, cinematic grain",
        "fuji_pro_400h": "Fuji Pro 400H film stock, cool tones, soft greens, airy highlights, fine grain structure",
        "cinestill_800t": "CineStill 800T film stock, tungsten halation, glowing highlights, red halation around lights",
        "digital_clean": "clean digital capture, no visible noise, maximum sharpness, clinical precision",
    },
    "lens_effects": {
        "anamorphic": "anamorphic lens flare, oval bokeh, horizontal streak flares, cinematic widescreen aspect",
        "vintage": "vintage lens softness, chromatic aberration, swirly bokeh, warm color cast",
        "macro": "macro lens detail, razor-thin depth of field, extreme close-up sharpness, background blur",
        "tilt_shift": "tilt-shift miniature effect, selective focus plane, miniature world aesthetic",
    },
}


# ---------------------------------------------------------------------------
# Character anchor system — multi-shot consistency locking
# ---------------------------------------------------------------------------

class CharacterAnchorSystem:
    """Locks character appearance across multiple shots."""

    def __init__(
        self,
        character_description: str,
        key_traits: list[str] | None = None,
        reference_image: str | None = None,
        prop_anchors: dict[str, str] | None = None,
    ) -> None:
        self.character_description = character_description
        self.key_traits = key_traits or []
        self.reference_image = reference_image
        self.prop_anchors = prop_anchors or {}

    def anchor_for_shot(self, shot_index: int) -> str:
        lines = []
        if shot_index == 0:
            lines.append("[IDENTITY LOCK — Shot 1: Establishing]")
            lines.append(f"Subject: {self.character_description}")
            if self.key_traits:
                lines.append(f"Fixed traits: {', '.join(self.key_traits)}")
            if self.reference_image:
                lines.append(
                    "REFERENCE: Match exact appearance, lighting, and composition "
                    "from the provided reference image."
                )
        else:
            lines.append(f"[IDENTITY LOCK — Shot {shot_index + 1}: Continuity]")
            lines.append(f"Same subject: {self.character_description}")
            if self.key_traits:
                lines.append(f"Preserve: {', '.join(self.key_traits)}")
            lines.append("No identity drift. Match previous shot exactly.")

        for prop_name, prop_desc in self.prop_anchors.items():
            lines.append(f"PROP '{prop_name}': {prop_desc}")

        return "\n".join(lines)

    def consistency_block(self) -> str:
        traits_str = ", ".join(self.key_traits) if self.key_traits else "appearance, clothing, proportions"
        return (
            f"[CONSISTENCY LOCK] Subject: {self.character_description}\n"
            f"Must match: {traits_str}\n"
            "No drift, no variation, identical identity across all shots."
        )


# ---------------------------------------------------------------------------
# Shot chain — narrative coherence across shots
# ---------------------------------------------------------------------------

class ShotChain:
    """Builds prompts sequentially with continuity hooks."""

    TRANSITIONS = {
        "cut": "CUT TO",
        "dissolve": "DISSOLVE TO",
        "match_cut": "MATCH CUT TO",
        "whip_pan": "WHIP PAN TO",
        "cross_dissolve": "CROSS DISSOLVE TO",
        "jump_cut": "JUMP CUT TO",
    }

    def __init__(
        self,
        subject: str,
        environment: str,
        style: str = "cinematic",
        character_anchor: CharacterAnchorSystem | None = None,
    ) -> None:
        self.subject = subject
        self.environment = environment
        self.style = style
        self.character_anchor = character_anchor
        self._shots: list[dict[str, str]] = []
        self._previous_action: str | None = None

    def add_shot(
        self,
        shot_type: str,
        action: str,
        camera_move: str = "push_in",
        transition: str = "cut",
        duration: int = 4,
        environment_modifier: str | None = None,
        emotional_beat: str | None = None,
    ) -> ShotChain:
        shot_index = len(self._shots)
        self._shots.append({
            "index": str(shot_index),
            "type": shot_type,
            "action": action,
            "camera_move": camera_move,
            "transition": transition,
            "duration": str(duration),
            "environment_modifier": environment_modifier or "",
            "emotional_beat": emotional_beat or "",
        })
        self._previous_action = action
        return self

    def build_prompt(self) -> str:
        if not self._shots:
            return ""

        style_config = VIDEO_STYLE_MODELS.get(self.style, VIDEO_STYLE_MODELS["cinematic"])
        lighting_key = style_config.get("lighting", "studio")

        lines = [
            "[MASTER CONTEXT]",
            f"Subject: {self.subject}",
            f"Environment: {self.environment}",
            f"Style: {self.style}",
            f"Total shots: {len(self._shots)}",
            "",
        ]

        for i, shot in enumerate(self._shots):
            shot_spec = SHOT_SPECS.get(shot["type"], SHOT_SPECS["medium"])
            transition_word = self.TRANSITIONS.get(shot["transition"], "CUT TO")

            if i > 0:
                lines.append(f"--- {transition_word} ---")

            if self.character_anchor:
                lines.append(self.character_anchor.anchor_for_shot(i))
                lines.append("")

            lines.extend([
                f"[SHOT {i + 1}]",
                f"Setting: {self.environment}{', ' + shot['environment_modifier'] if shot['environment_modifier'] else ''}",
                f"Camera: {shot_spec['type']}, {shot_spec['lens']}mm lens, {shot_spec['framing']}",
                f"Motion: {CAMERA_MOVES.get(shot['camera_move'], 'locked off')}",
                f"Subject action: {self.subject} {shot['action']}.",
                f"Lighting: {LIGHTING_PRESETS.get(lighting_key, LIGHTING_PRESETS['studio'])['model_tags']}.",
                f"Color grade: {GRADE_PRESETS.get(self.style, GRADE_PRESETS['cinematic'])}.",
                _material(self.subject),
                f"Duration: {shot['duration']}s.",
            ])

            if shot["emotional_beat"]:
                lines.append(f"Mood: {shot['emotional_beat']}.")

            self._previous_action = shot["action"]

        if self.character_anchor:
            lines.append("")
            lines.append(self.character_anchor.consistency_block())

        lines.append("")
        lines.extend(technical_constraints(self.style).split("\n"))
        lines.append(negative_block(self.style))

        return "\n".join(lines)

    @property
    def shot_count(self) -> int:
        return len(self._shots)

    def get_shot(self, index: int) -> dict[str, str] | None:
        if 0 <= index < len(self._shots):
            return self._shots[index]
        return None


# ---------------------------------------------------------------------------
# Backward-compatible aliases for existing imports
# ---------------------------------------------------------------------------
SHOT_TYPES = SHOT_SPECS
VIDEO_STYLE_TEMPLATES = VIDEO_STYLE_MODELS
