"""Cinematic enhancer — adds film stock, lens, and lighting specifics.

Transforms basic video prompts into professional cinematography descriptions
with specific film stocks, lens characteristics, and lighting patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Film stock library
# ---------------------------------------------------------------------------

FILM_STOCKS = {
    "kodak_portra_400": {
        "name": "Kodak Portra 400",
        "look": "warm skin tones, soft pastels, fine grain",
        "tags": "Kodak Portra 400 film stock, warm natural skin tones, soft pastel colors, fine grain structure, gentle highlight rolloff",
        "best_for": "portraits, lifestyle, fashion",
    },
    "kodak_portra_800": {
        "name": "Kodak Portra 800",
        "look": "faster film, slightly more grain, warm tones",
        "tags": "Kodak Portra 800 film stock, warm tones, moderate grain, low-light capable, natural colors",
        "best_for": "low light, events, documentary",
    },
    "kodak_vision3_50d": {
        "name": "Kodak Vision3 50D",
        "look": "clean cinema, fine grain, vibrant colors",
        "tags": "Kodak Vision3 50D cinema film, ultra-fine grain, vibrant saturated colors, clean digital-like clarity, cinema production",
        "best_for": "commercial, high-end production",
    },
    "kodak_vision3_250d": {
        "name": "Kodak Vision3 250D",
        "look": "versatile cinema, natural colors",
        "tags": "Kodak Vision3 250D cinema film, natural color reproduction, moderate grain, versatile daylight film",
        "best_for": "general cinema, narrative",
    },
    "kodak_vision3_500t": {
        "name": "Kodak Vision3 500T",
        "look": "tungsten cinema, rich shadows, controlled highlights",
        "tags": "Kodak Vision3 500T tungsten cinema film, rich deep shadows, controlled highlight retention, cinematic grain, Hollywood production look",
        "best_for": "narrative, dramatic scenes, night",
    },
    "fuji_pro_400h": {
        "name": "Fuji Pro 400H",
        "look": "cool tones, soft greens, airy highlights",
        "tags": "Fuji Pro 400H film stock, cool blue-green tones, soft pastel greens, airy bright highlights, fine grain",
        "best_for": "weddings, soft portraits, nature",
    },
    "fuji_superia_400": {
        "name": "Fuji Superia 400",
        "look": "consumer film, slightly cool, green cast",
        "tags": "Fuji Superia 400 film stock, slightly cool tones, green undertones, moderate grain, consumer film look",
        "best_for": "casual, vintage, everyday",
    },
    "cinestill_800t": {
        "name": "CineStill 800T",
        "look": "tungsten halation, glowing highlights, red halation",
        "tags": "CineStill 800T film stock, tungsten balanced, glowing halation around lights, red light bleed, cinematic night look",
        "best_for": "night, urban, neon-lit scenes",
    },
    "cinestill_50d": {
        "name": "CineStill 50D",
        "look": "clean daylight, halation, cinematic",
        "tags": "CineStill 50D film stock, daylight balanced, subtle halation, clean cinematic look, fine grain",
        "best_for": "daylight cinema, commercial",
    },
    "ilford_hp5": {
        "name": "Ilford HP5+",
        "look": "classic black and white, moderate contrast",
        "tags": "Ilford HP5+ black and white film, classic monochrome, moderate contrast, visible grain, timeless look",
        "best_for": "documentary, artistic, noir",
    },
    "kodak_trix_400": {
        "name": "Kodak Tri-X 400",
        "look": "high contrast B&W, punchy blacks",
        "tags": "Kodak Tri-X 400 black and white film, high contrast, deep blacks, punchy highlights, photojournalism classic",
        "best_for": "documentary, photojournalism, drama",
    },
    "digital_clean": {
        "name": "Clean Digital",
        "look": "no grain, maximum sharpness, clinical",
        "tags": "clean digital capture, no visible noise, maximum sharpness, clinical precision, modern digital sensor",
        "best_for": "commercial, product, clean aesthetic",
    },
}


# ---------------------------------------------------------------------------
# Lens library
# ---------------------------------------------------------------------------

LENSES = {
    "anamorphic_40mm": {
        "name": "Anamorphic 40mm",
        "look": "oval bokeh, horizontal flares, widescreen",
        "tags": "anamorphic lens, oval bokeh, horizontal lens flares, 2.39:1 widescreen, cinematic anamorphic look",
        "fov": "moderate wide",
    },
    "anamorphic_75mm": {
        "name": "Anamorphic 75mm",
        "look": "portrait anamorphic, compressed background",
        "tags": "anamorphic portrait lens, compressed background, oval bokeh, horizontal flares, shallow depth",
        "fov": "portrait",
    },
    "primer_14mm": {
        "name": "Ultra-Wide 14mm",
        "look": "dramatic perspective, exaggerated depth",
        "tags": "ultra-wide 14mm lens, dramatic perspective distortion, exaggerated depth, expansive field of view",
        "fov": "ultra-wide",
    },
    "primer_24mm": {
        "name": "Wide 24mm",
        "look": "natural wide, environmental context",
        "tags": "wide 24mm lens, natural perspective, environmental context, moderate depth",
        "fov": "wide",
    },
    "primer_35mm": {
        "name": "Standard 35mm",
        "look": "natural perspective, versatile",
        "tags": "standard 35mm lens, natural human perspective, versatile focal length, moderate depth of field",
        "fov": "standard",
    },
    "primer_50mm": {
        "name": "Normal 50mm",
        "look": "closest to human eye, natural",
        "tags": "normal 50mm lens, closest to human eye perspective, natural rendering, moderate compression",
        "fov": "normal",
    },
    "primer_85mm": {
        "name": "Portrait 85mm",
        "look": "flattering compression, shallow DOF",
        "tags": "portrait 85mm lens, flattering facial compression, shallow depth of field, beautiful bokeh",
        "fov": "portrait",
    },
    "primer_135mm": {
        "name": "Telephoto 135mm",
        "look": "compressed perspective, isolated subject",
        "tags": "telephoto 135mm lens, compressed perspective, strongly isolated subject, extreme shallow depth",
        "fov": "telephoto",
    },
    "macro_100mm": {
        "name": "Macro 100mm",
        "look": "extreme detail, razor-thin focus",
        "tags": "macro 100mm lens, extreme close-up detail, razor-thin depth of field, magnified textures",
        "fov": "macro",
    },
    "tilt_shift_90mm": {
        "name": "Tilt-Shift 90mm",
        "look": "miniature effect, selective focus",
        "tags": "tilt-shift 90mm lens, miniature world effect, selective plane of focus, creative blur",
        "fov": "tilt-shift",
    },
}


# ---------------------------------------------------------------------------
# Lighting patterns
# ---------------------------------------------------------------------------

LIGHTING_PATTERNS = {
    "three_point": {
        "name": "Three-Point Lighting",
        "tags": "three-point lighting setup, key light, fill light, back light, professional studio",
        "mood": "neutral, professional",
    },
    "rembrandt": {
        "name": "Rembrandt Lighting",
        "tags": "Rembrandt lighting, triangle of light on cheek, dramatic side lighting, classical portrait",
        "mood": "dramatic, artistic",
    },
    "butterfly": {
        "name": "Butterfly Lighting",
        "tags": "butterfly lighting, shadow under nose, glamorous, beauty lighting, Paramount lighting",
        "mood": "glamorous, beauty",
    },
    "split": {
        "name": "Split Lighting",
        "tags": "split lighting, half face lit, half face shadow, dramatic contrast, noir",
        "mood": "dramatic, mysterious",
    },
    "rim": {
        "name": "Rim Lighting",
        "tags": "rim lighting, backlit silhouette, edge light, subject separation, halo effect",
        "mood": "dramatic, ethereal",
    },
    "broad": {
        "name": "Broad Lighting",
        "tags": "broad lighting, wider side of face lit, traditional portrait, soft shadows",
        "mood": "classic, flattering",
    },
    "short": {
        "name": "Short Lighting",
        "tags": "short lighting, narrower side of face lit, slimming effect, dramatic shadows",
        "mood": "dramatic, slimming",
    },
    "clamshell": {
        "name": "Clamshell Lighting",
        "tags": "clamshell lighting, beauty dish above and below, even flattering light, minimal shadows",
        "mood": "beauty, commercial",
    },
    "natural_window": {
        "name": "Natural Window Light",
        "tags": "natural window light, soft diffused daylight, directional shadows, organic feel",
        "mood": "natural, intimate",
    },
    "golden_hour": {
        "name": "Golden Hour",
        "tags": "golden hour sunlight, warm amber tones, long shadows, lens flares, magic hour",
        "mood": "warm, romantic",
    },
    "blue_hour": {
        "name": "Blue Hour",
        "tags": "blue hour twilight, cool ambient light, city lights glowing, soft even illumination",
        "mood": "cool, serene",
    },
    "neon_practical": {
        "name": "Neon/Practical",
        "tags": "neon lighting, practical light sources, colored reflections, urban night, cyberpunk",
        "mood": "urban, futuristic",
    },
}


# ---------------------------------------------------------------------------
# Cinematic enhancer class
# ---------------------------------------------------------------------------

@dataclass
class CinematicProfile:
    """A complete cinematic profile for enhancing prompts."""

    film_stock: str = "kodak_vision3_250d"
    lens: str = "primer_50mm"
    lighting_pattern: str = "three_point"
    color_temperature: str = "neutral"
    contrast_level: str = "medium"
    grain_intensity: str = "subtle"
    diffusion: str = "none"
    custom_tags: list[str] = field(default_factory=list)

    def to_prompt_suffix(self) -> str:
        """Generate a prompt suffix from this profile."""
        parts = []

        # Film stock
        stock = FILM_STOCKS.get(self.film_stock)
        if stock:
            parts.append(stock["tags"])

        # Lens
        lens = LENSES.get(self.lens)
        if lens:
            parts.append(lens["tags"])

        # Lighting
        lighting = LIGHTING_PATTERNS.get(self.lighting_pattern)
        if lighting:
            parts.append(lighting["tags"])

        # Color temperature
        temp_tags = {
            "warm": "warm color temperature, amber tones",
            "neutral": "neutral color balance",
            "cool": "cool color temperature, blue tones",
            "mixed": "mixed color temperatures, practical lights",
        }
        if self.color_temperature in temp_tags:
            parts.append(temp_tags[self.color_temperature])

        # Contrast
        contrast_tags = {
            "low": "low contrast, lifted shadows, soft look",
            "medium": "medium contrast, natural tonal range",
            "high": "high contrast, deep blacks, punchy highlights",
            "extreme": "extreme contrast, crushed blacks, blown highlights",
        }
        if self.contrast_level in contrast_tags:
            parts.append(contrast_tags[self.contrast_level])

        # Grain
        grain_tags = {
            "none": "no visible grain, clean image",
            "subtle": "subtle film grain texture",
            "moderate": "moderate film grain, organic texture",
            "heavy": "heavy film grain, vintage texture",
        }
        if self.grain_intensity in grain_tags:
            parts.append(grain_tags[self.grain_intensity])

        # Diffusion
        diff_tags = {
            "none": "sharp, no diffusion",
            "light": "light diffusion, softened highlights",
            "medium": "medium diffusion, dreamy glow",
            "heavy": "heavy diffusion, ethereal soft focus",
        }
        if self.diffusion in diff_tags:
            parts.append(diff_tags[self.diffusion])

        # Custom tags
        parts.extend(self.custom_tags)

        return ", ".join(parts)


class CinematicEnhancer:
    """Enhances video prompts with professional cinematography details.

    Adds specific film stock characteristics, lens behaviors, lighting
    patterns, and other cinematic elements to transforms basic prompts
    into professional-grade cinematography descriptions.
    """

    # Preset profiles for common looks
    PRESETS = {
        "hollywood_narrative": CinematicProfile(
            film_stock="kodak_vision3_500t",
            lens="primer_50mm",
            lighting_pattern="three_point",
            contrast_level="high",
            grain_intensity="subtle",
        ),
        "indie_film": CinematicProfile(
            film_stock="kodak_portra_400",
            lens="primer_35mm",
            lighting_pattern="natural_window",
            contrast_level="medium",
            grain_intensity="moderate",
        ),
        "commercial_clean": CinematicProfile(
            film_stock="digital_clean",
            lens="primer_85mm",
            lighting_pattern="clamshell",
            contrast_level="medium",
            grain_intensity="none",
        ),
        "night_noir": CinematicProfile(
            film_stock="kodak_vision3_500t",
            lens="primer_35mm",
            lighting_pattern="split",
            contrast_level="extreme",
            grain_intensity="moderate",
        ),
        "vintage_70s": CinematicProfile(
            film_stock="kodak_portra_400",
            lens="primer_50mm",
            lighting_pattern="golden_hour",
            color_temperature="warm",
            contrast_level="low",
            grain_intensity="heavy",
            diffusion="light",
        ),
        "music_video": CinematicProfile(
            film_stock="cinestill_800t",
            lens="anamorphic_40mm",
            lighting_pattern="neon_practical",
            contrast_level="high",
            grain_intensity="subtle",
        ),
        "documentary": CinematicProfile(
            film_stock="kodak_vision3_250d",
            lens="primer_35mm",
            lighting_pattern="natural_window",
            contrast_level="medium",
            grain_intensity="subtle",
        ),
        "beauty_editorial": CinematicProfile(
            film_stock="kodak_portra_400",
            lens="primer_85mm",
            lighting_pattern="butterfly",
            contrast_level="low",
            grain_intensity="none",
            diffusion="light",
        ),
    }

    def __init__(self, profile: CinematicProfile | str | None = None) -> None:
        """Initialize with a profile or preset name."""
        if isinstance(profile, str):
            self.profile = self.PRESETS.get(profile, CinematicProfile())
        elif profile is None:
            self.profile = CinematicProfile()
        else:
            self.profile = profile

    def enhance_prompt(self, prompt: str) -> str:
        """Add cinematic details to a prompt."""
        suffix = self.profile.to_prompt_suffix()
        if suffix:
            return f"{prompt}, {suffix}"
        return prompt

    def enhance_for_shot_type(
        self,
        prompt: str,
        shot_type: str,
    ) -> str:
        """Enhance prompt with shot-type-appropriate cinematic details."""
        # Adjust lens based on shot type
        lens_overrides = {
            "establishing": "primer_24mm",
            "wide": "primer_24mm",
            "medium": "primer_50mm",
            "close_up": "primer_85mm",
            "extreme_close_up": "macro_100mm",
            "portrait": "primer_85mm",
            "action": "primer_35mm",
            "low_angle": "primer_24mm",
            "high_angle": "primer_35mm",
        }

        # Create a copy with lens override
        enhanced_profile = CinematicProfile(
            film_stock=self.profile.film_stock,
            lens=lens_overrides.get(shot_type, self.profile.lens),
            lighting_pattern=self.profile.lighting_pattern,
            color_temperature=self.profile.color_temperature,
            contrast_level=self.profile.contrast_level,
            grain_intensity=self.profile.grain_intensity,
            diffusion=self.profile.diffusion,
            custom_tags=self.profile.custom_tags,
        )

        enhancer = CinematicEnhancer(enhanced_profile)
        return enhancer.enhance_prompt(prompt)

    def get_available_presets(self) -> list[str]:
        """Return available preset names."""
        return list(self.PRESETS.keys())

    def get_profile_info(self) -> dict[str, Any]:
        """Return information about the current profile."""
        return {
            "film_stock": FILM_STOCKS.get(self.profile.film_stock, {}),
            "lens": LENSES.get(self.profile.lens, {}),
            "lighting": LIGHTING_PATTERNS.get(self.profile.lighting_pattern, {}),
            "color_temperature": self.profile.color_temperature,
            "contrast_level": self.profile.contrast_level,
            "grain_intensity": self.profile.grain_intensity,
            "diffusion": self.profile.diffusion,
        }


def enhance_prompt_cinematic(
    prompt: str,
    preset: str = "hollywood_narrative",
    *,
    shot_type: str | None = None,
    custom_tags: list[str] | None = None,
) -> str:
    """Convenience function to enhance a prompt with cinematic details.

    Args:
        prompt: The base video prompt.
        preset: Preset name or profile to use.
        shot_type: Optional shot type for lens adjustment.
        custom_tags: Additional tags to add.

    Returns:
        Enhanced prompt with cinematic details.
    """
    profile = CinematicEnhancer.PRESETS.get(preset, CinematicProfile())
    if custom_tags:
        profile.custom_tags.extend(custom_tags)

    enhancer = CinematicEnhancer(profile)

    if shot_type:
        return enhancer.enhance_for_shot_type(prompt, shot_type)
    return enhancer.enhance_prompt(prompt)
