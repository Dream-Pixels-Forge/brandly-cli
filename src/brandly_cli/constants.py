"""Common types and constants for the Brandly pipeline."""

from __future__ import annotations

from typing import Any, Literal

# ---------------------------------------------------------------------------
# Video styles
# ---------------------------------------------------------------------------

VideoStyle = Literal[
    "cinematic",
    "ugc",
    "montage",
    "multi_shot",
    "continuous",
    "unboxing",
    "lifestyle",
    "collage_motion_graphic",
    "brand_short_video",
    "explainer_video",
]

VIDEO_STYLES: list[VideoStyle] = [
    "cinematic",
    "ugc",
    "montage",
    "multi_shot",
    "continuous",
    "unboxing",
    "lifestyle",
    "collage_motion_graphic",
    "brand_short_video",
    "explainer_video",
]

STYLE_COSTS: dict[VideoStyle, int] = {
    "cinematic": 250,
    "ugc": 150,
    "montage": 200,
    "multi_shot": 300,
    "continuous": 200,
    "unboxing": 180,
    "lifestyle": 170,
    "collage_motion_graphic": 350,
    "brand_short_video": 280,
    "explainer_video": 400,
}

# Per-shot extra cost table
SHOT_COSTS: dict[int, int] = {
    3: 0,
    4: 15,
    5: 30,
    6: 50,
    7: 75,
    8: 100,
    9: 140,
    10: 180,
}

# ---------------------------------------------------------------------------
# Pipeline phases
# ---------------------------------------------------------------------------

Phase = Literal[
    "init",
    "trends",
    "concept",
    "script",
    "asset",
    "audio",
    "re_edit",
    "validate",
    "publish",
    "done",
]

PHASE_ORDER: list[Phase] = [
    "init",
    "trends",
    "concept",
    "script",
    "asset",
    "audio",
    "re_edit",
    "validate",
    "publish",
    "done",
]

# ---------------------------------------------------------------------------
# Status literals
# ---------------------------------------------------------------------------

ProjectStatus = Literal["pending", "running", "completed", "failed", "paused", "cancelled"]
PhaseStatus = Literal["pending", "running", "completed", "failed"]

# ---------------------------------------------------------------------------
# Target platforms
# ---------------------------------------------------------------------------

TargetPlatform = Literal["tiktok", "instagram", "youtube", "all"]
TARGET_PLATFORMS: list[TargetPlatform] = ["tiktok", "instagram", "youtube", "all"]

# ---------------------------------------------------------------------------
# Style presets for Agnes AI (avoid AI slop)
# ---------------------------------------------------------------------------

StylePreset = Literal["photorealistic", "editorial", "cinematic", "commercial", "documentary"]

STYLE_PRESET_OPTIONS: list[StylePreset] = [
    "photorealistic",
    "editorial",
    "cinematic",
    "commercial",
    "documentary",
]

STYLE_CONFIG: dict[StylePreset, dict[str, str]] = {
    "photorealistic": {
        "prompt_suffix": (
            ", shot on Sony A7IV, 85mm f/1.4 lens, natural skin texture "
            "with visible pores and fine details, subtle film grain, "
            "soft natural window light, authentic material textures, "
            "real fabric weave, genuine metal patina, organic imperfections"
        ),
        "negative_prompt": (
            "ai generated, smooth plastic skin, airbrushed, oversaturated colors, "
            "perfect symmetry, uncanny valley, digital art, 3d render, illustration, "
            "painting, cartoon, anime, oversharpened, hdr overprocessed, "
            "fuzzy out-of-focus, cloned textures, muddy low-contrast wash"
        ),
    },
    "editorial": {
        "prompt_suffix": (
            ", magazine editorial photography, studio lighting with soft key and fill, "
            "clean composition, professional color grading, high-end retouching style, "
            "fashion photography aesthetic"
        ),
        "negative_prompt": (
            "ai generated, amateur photography, flat lighting, cluttered background, "
            "oversaturated, plastic skin, uncanny valley, clipart, illustration, low quality"
        ),
    },
    "cinematic": {
        "prompt_suffix": (
            ", shot through anamorphic lens, teal and orange color grading, "
            "volumetric light rays, shallow depth of field, cinematic color science, "
            "Kodak Vision3 500T film stock, subtle film grain, organic skin texture "
            "with visible pores and natural micro-details, real fabric weave texture, "
            "authentic material sheen, soft practical lighting"
        ),
        "negative_prompt": (
            "ai generated, smooth plastic skin, airbrushed, oversaturated, "
            "fuzzy out-of-focus areas, digital art, illustration, cartoon, anime, "
            "perfect symmetry, uncanny valley, oversharpened, hdr overprocessed, "
            "cloned repetitive textures, muddy low-contrast wash"
        ),
        # Distinct suffix for still-image generation (cinematic photo, not motion)
        "prompt_suffix_still": (
            ", cinematic still photograph, anamorphic lens, teal and orange color grading, "
            "shallow depth of field, volumetric light rays, Kodak Vision3 500T film stock, "
            "subtle film grain, authentic skin texture with visible pores and fine details, "
            "real fabric weave texture, genuine material surfaces, soft practical lighting, "
            "editorial photography quality, no motion blur, sharp static composition"
        ),
    },
    "commercial": {
        "prompt_suffix": (
            ", product photography, clean white or dark studio background, "
            "three-point lighting setup, sharp focus on product, subtle reflections, "
            "high-end commercial quality, professional retouching"
        ),
        "negative_prompt": (
            "ai generated, cluttered background, harsh shadows, flat lighting, "
            "oversaturated, plastic look, low quality, amateur, blurry, noisy"
        ),
    },
    "documentary": {
        "prompt_suffix": (
            ", documentary photography, available light only, photojournalistic style, "
            "candid moment, natural colors, slight motion blur, gritty realistic texture, "
            "Leica M11 with 50mm summilux"
        ),
        "negative_prompt": (
            "ai generated, staged, artificial lighting, oversaturated, plastic skin, "
            "perfect composition, studio, posed, artificial, digital art, illustration"
        ),
    },
}

# ---------------------------------------------------------------------------
# AI Model Catalog
# ---------------------------------------------------------------------------

ImageModel = Literal[
    "agnes-image-2.5-flash",
    "agnes-image-2.1-flash",
    "agnes-image-2.0-flash",
    "stable-diffusion-xl",
    "flux-pro",
    "dall-e-3",
    "minimax-image-01",
    "seedream-4.0",
    "seedream-3.5",
]

IMAGE_MODELS: list[ImageModel] = [
    "agnes-image-2.5-flash",
    "agnes-image-2.1-flash",
    "agnes-image-2.0-flash",
    "stable-diffusion-xl",
    "flux-pro",
    "dall-e-3",
    "minimax-image-01",
    "seedream-4.0",
    "seedream-3.5",
]

# Current model IDs per the official Agnes docs (verified 2026-09-15):
# - Image: agnes-image-2.5-flash is the latest generation and the default.
# - Video: agnes-video-2.5-flash is the current free video model (720P, 4-12s).
# - Text: agnes-2.5-flash is the recommended text/agent model (tool calling).
DEFAULT_AGNES_IMAGE_MODEL = "agnes-image-2.5-flash"
DEFAULT_AGNES_VIDEO_MODEL = "agnes-video-2.5-flash"
DEFAULT_AGNES_TEXT_MODEL = "agnes-2.5-flash"

IMAGE_MODEL_INFO: dict[ImageModel, dict[str, Any]] = {
    "agnes-image-2.5-flash": {
        "name": "Agnes Image 2.5 Flash",
        "category": "image",
        "provider": "Agnes AI",
        "speed": "fast",
        "quality": "ultra-high",
        "cost_credits": 10,
        "max_resolution": "4K",
        "features": [
            "text-to-image",
            "image-to-image",
            "multi-image composition",
            "high-density details",
        ],
        "description": (
            "Latest-generation Agnes image model - strongest detail rendering, "
            "composition preservation, and prompt alignment. Same API contract as "
            "2.1-flash (sizes 1K/2K/3K/4K, ratios incl. 21:9). Currently free."
        ),
    },
    "agnes-image-2.1-flash": {
        "name": "Agnes Image 2.1 Flash",
        "category": "image",
        "provider": "Agnes AI",
        "speed": "fast",
        "quality": "high",
        "cost_credits": 10,
        "max_resolution": "4K",
        "features": ["text-to-image", "style transfer", "batch generation"],
        "description": "Fast and high-quality image generation with style presets",
    },
    "agnes-image-2.0-flash": {
        "name": "Agnes Image 2.0 Flash",
        "category": "image",
        "provider": "Agnes AI",
        "speed": "fast",
        "quality": "ultra-high",
        "cost_credits": 15,
        "max_resolution": "4K",
        "features": ["text-to-image", "img2img", "inpainting", "outpainting"],
        "description": "Premium quality image generation with advanced editing",
    },
"stable-diffusion-xl": {
        "name": "Stable Diffusion XL",
        "category": "image",
        "provider": "OpenAI Compatible",
        "speed": "medium",
        "quality": "high",
        "cost_credits": 15,
        "max_resolution": "1024x1024",
        "features": ["text-to-image", "img2img", "controlnet", "lora"],
        "description": "Versatile open-source image generation model",
    },
    "flux-pro": {
        "name": "Flux Pro",
        "category": "image",
        "provider": "Black Forest Labs",
        "speed": "medium",
        "quality": "ultra-high",
        "cost_credits": 25,
        "max_resolution": "4K",
        "features": ["text-to-image", "photorealistic", "artistic"],
        "description": "State-of-the-art photorealistic image generation",
    },
    "dall-e-3": {
        "name": "DALL-E 3",
        "category": "image",
        "provider": "OpenAI",
        "speed": "fast",
        "quality": "high",
        "cost_credits": 20,
        "max_resolution": "1024x1024",
        "features": ["text-to-image", "natural language understanding"],
        "description": "OpenAI's advanced image generation with natural language",
    },
    "minimax-image-01": {
        "name": "MiniMax Image-01",
        "category": "image",
        "provider": "MiniMax",
        "speed": "fast",
        "quality": "high",
        "cost_credits": 12,
        "max_resolution": "2048x2048",
        "features": ["text-to-image", "image-to-image", "subject reference", "prompt optimizer"],
        "description": (
            "MiniMax image generation with subject reference support "
            "and automatic prompt optimization"
        ),
    },
    "seedream-4.0": {
        "name": "Seedream 4.0",
        "category": "image",
        "provider": "BytePlus Ark",
        "speed": "fast",
        "quality": "ultra-high",
        "cost_credits": 30,
        "max_resolution": "4K",
        "features": ["text-to-image", "photorealistic", "cinematic", "style transfer"],
        "description": (
            "BytePlus Ark Seedream 4.0 — state-of-the-art photorealistic "
            "and cinematic image generation with excellent prompt following"
        ),
    },
    "seedream-3.5": {
        "name": "Seedream 3.5",
        "category": "image",
        "provider": "BytePlus Ark",
        "speed": "very-fast",
        "quality": "high",
        "cost_credits": 15,
        "max_resolution": "4K",
        "features": ["text-to-image", "fast generation", "commercial quality"],
        "description": (
            "BytePlus Ark Seedream 3.5 — fast production-quality image "
            "generation ideal for prototyping and commercial use"
        ),
    },
}

VideoModel = Literal[
    "agnes-video-2.5-flash",
    "kling-1.5",
    "hailuo-2.3",
    "runway-gen3",
    "sora-2",
    "minimax-h3",
    "minimax-h3-max",
    "seedance-1.0-t2v",
    "seedance-1.0-i2v",
]

VIDEO_MODELS: list[VideoModel] = [
    "agnes-video-2.5-flash",
    "kling-1.5",
    "hailuo-2.3",
    "runway-gen3",
    "sora-2",
    "minimax-h3",
    "minimax-h3-max",
    "seedance-1.0-t2v",
    "seedance-1.0-i2v",
]

VIDEO_MODEL_INFO: dict[VideoModel, dict[str, Any]] = {
    "agnes-video-2.5-flash": {
        "name": "Agnes Video 2.5 Flash",
        "category": "video",
        "provider": "Agnes AI",
        "speed": "fast",
        "quality": "medium",
        "cost_credits": 20,
        "max_duration": "12s",
        "max_resolution": "720p",
        "features": ["text-to-video", "fast generation"],
        "description": "Fast prototyping with rate limits (1 req/min)",
    },
    "kling-1.5": {
        "name": "Kling 1.5",
        "category": "video",
        "provider": "Kuaishou",
        "speed": "medium",
        "quality": "ultra-high",
        "cost_credits": 100,
        "max_duration": "60s",
        "max_resolution": "1080p",
        "features": ["text-to-video", "cinematic", "action sequences"],
        "description": "High-quality cinematic video generation",
    },
    "hailuo-2.3": {
        "name": "Hailuo 2.3",
        "category": "video",
        "provider": "MiniMax",
        "speed": "fast",
        "quality": "high",
        "cost_credits": 75,
        "max_duration": "30s",
        "max_resolution": "1080p",
        "features": ["text-to-video", "free tier available"],
        "description": "Free tier available, great quality for prototyping",
    },
    "runway-gen3": {
        "name": "Runway Gen-3",
        "category": "video",
        "provider": "Runway",
        "speed": "medium",
        "quality": "ultra-high",
        "cost_credits": 120,
        "max_duration": "60s",
        "max_resolution": "1080p",
        "features": ["text-to-video", "camera control", "motion brush"],
        "description": "Professional-grade video generation with fine control",
    },
    "sora-2": {
        "name": "Sora 2",
        "category": "video",
        "provider": "OpenAI",
        "speed": "slow",
        "quality": "ultra-high",
        "cost_credits": 150,
        "max_duration": "60s",
        "max_resolution": "1080p",
        "features": ["text-to-video", "long-form", "complex scenes"],
        "description": "OpenAI's most advanced video generation model",
    },
    "minimax-h3": {
        "name": "MiniMax H3",
        "category": "video",
        "provider": "MiniMax",
        "speed": "fast",
        "quality": "high",
        "cost_credits": 60,
        "max_duration": "15s",
        "max_resolution": "2K",
        "features": [
            "text-to-video",
            "image-to-video",
            "reference video",
            "reference audio",
            "co-speech video",
            "native stereo audio",
        ],
        "description": (
            "MiniMax H3: Full multimodal video generation with native synchronized "
            "stereo audio, reference inputs, co-speech support, and up to 2K resolution"
        ),
    },
    "minimax-h3-max": {
        "name": "MiniMax H3-Max",
        "category": "video",
        "provider": "MiniMax",
        "speed": "very-fast",
        "quality": "high",
        "cost_credits": 40,
        "max_duration": "15s",
        "max_resolution": "768P",
        "features": ["text-to-video", "first/last frame", "fast generation"],
        "description": (
            "MiniMax H3-Max: Fast video generation with first/last frame control, "
            "lower resolution but quicker turnaround"
        ),
    },
    "seedance-1.0-t2v": {
        "name": "Seedance 1.0 T2V",
        "category": "video",
        "provider": "BytePlus Ark",
        "speed": "fast",
        "quality": "ultra-high",
        "cost_credits": 80,
        "max_duration": "15s",
        "max_resolution": "1080P",
        "features": ["text-to-video", "cinematic", "character consistency", "motion control"],
        "description": (
            "BytePlus Ark Seedance 1.0 — cinematic text-to-video generation "
            "with excellent motion quality and character consistency"
        ),
    },
    "seedance-1.0-i2v": {
        "name": "Seedance 1.0 I2V",
        "category": "video",
        "provider": "BytePlus Ark",
        "speed": "fast",
        "quality": "ultra-high",
        "cost_credits": 90,
        "max_duration": "15s",
        "max_resolution": "1080P",
        "features": ["image-to-video", "reference anchored", "motion control"],
        "description": (
            "BytePlus Ark Seedance 1.0 Image-to-Video — generate videos from "
            "reference images with exact visual consistency"
        ),
    },
}

AudioModel = Literal[
    "google-lyria",
    "eleven_v3",
    "eleven_v4",
    "speech-2.8-hd",
    "music-3.0",
]

AUDIO_MODELS: list[AudioModel] = [
    "google-lyria",
    "eleven_v3",
    "eleven_v4",
    "speech-2.8-hd",
    "music-3.0",
]

AUDIO_MODEL_INFO: dict[AudioModel, dict[str, Any]] = {
    "google-lyria": {
        "name": "Google Lyria",
        "category": "audio",
        "subtype": "music",
        "provider": "Google",
        "cost_credits": 30,
        "features": ["text-to-music", "instrumental", "lyrical"],
        "description": "High-quality AI-generated music",
    },
    "eleven_v3": {
        "name": "ElevenLabs v3",
        "category": "audio",
        "subtype": "tts",
        "provider": "ElevenLabs",
        "cost_credits": 10,
        "features": ["text-to-speech", "multi-language", "voice cloning"],
        "description": "Natural-sounding voiceover generation",
    },
    "eleven_v4": {
        "name": "ElevenLabs v4",
        "category": "audio",
        "subtype": "tts",
        "provider": "ElevenLabs",
        "cost_credits": 15,
        "features": ["text-to-speech", "emotional", "multilingual"],
        "description": "Latest generation TTS with emotional range",
    },
    "speech-2.8-hd": {
        "name": "MiniMax Speech 2.8 HD",
        "category": "audio",
        "subtype": "tts",
        "provider": "MiniMax",
        "cost_credits": 8,
        "features": ["text-to-speech", "high quality", "fast"],
        "description": "High-definition text-to-speech from MiniMax",
    },
    "music-3.0": {
        "name": "MiniMax Music 3.0",
        "category": "audio",
        "subtype": "music",
        "provider": "MiniMax",
        "cost_credits": 25,
        "features": ["text-to-music", "instrumental", "structured"],
        "description": "Structured music generation from prompts",
    },
}


def get_all_models() -> dict[str, list[dict[str, Any]]]:
    """Return all models grouped by category."""
    return {
        "image": [
            {
                "id": mid,
                "name": info["name"],
                "provider": info["provider"],
                "speed": info["speed"],
                "quality": info["quality"],
                "cost": info["cost_credits"],
                "features": info["features"],
            }
            for mid, info in IMAGE_MODEL_INFO.items()
        ],
        "video": [
            {
                "id": mid,
                "name": info["name"],
                "provider": info["provider"],
                "speed": info["speed"],
                "quality": info["quality"],
                "cost": info["cost_credits"],
                "features": info["features"],
            }
            for mid, info in VIDEO_MODEL_INFO.items()
        ],
        "audio": [
            {
                "id": mid,
                "name": info["name"],
                "provider": info["provider"],
                "cost": info["cost_credits"],
                "features": info["features"],
            }
            for mid, info in AUDIO_MODEL_INFO.items()
        ],
    }


def get_model_info(model_id: str) -> dict[str, Any] | None:
    """Return detailed info for a model ID."""
    from typing import cast
    if model_id in IMAGE_MODEL_INFO:
        info = cast(dict[str, Any], IMAGE_MODEL_INFO[model_id])
        info = dict(info)
        info["id"] = model_id
        return info
    if model_id in VIDEO_MODEL_INFO:
        info = cast(dict[str, Any], VIDEO_MODEL_INFO[model_id])
        info = dict(info)
        info["id"] = model_id
        return info
    if model_id in AUDIO_MODEL_INFO:
        info = cast(dict[str, Any], AUDIO_MODEL_INFO[model_id])
        info = dict(info)
        info["id"] = model_id
        return info
    return None


# ---------------------------------------------------------------------------
# Provider rate limits (official docs, verified 2026-09-15)
# ---------------------------------------------------------------------------
# Agnes default/free key effective RPM; enterprise ~2x on 1K/2K, Token Plan
# text 1000 RPM. MiniMax H3 is governed by concurrent tasks (2 free / 15
# paid), not per-minute RPM.
#   https://www.agnes-ai.com/en/docs/tokenplan
#   https://platform.minimax.io/docs/guides/rate-limits
PROVIDER_RATE_LIMITS: dict[str, dict[str, Any]] = {
    "Agnes AI": {
        "docs": "https://www.agnes-ai.com/en/docs/tokenplan",
        "access_type": "default/free key (effective RPM)",
        "text_rpm": 20,
        "image_rpm_by_size": {"1K": 20, "2K": 10, "3K": 1, "4K": 1},
        "video": "500 video-seconds/day free quota (Token Plan); RPM updated 2026-06-28",
        "video_poll_seconds": 1,
    },
    "MiniMax": {
        "docs": "https://platform.minimax.io/docs/guides/rate-limits",
        "note": "H3 video is concurrency-governed, not per-minute RPM",
        "h3_concurrent_tasks_free": 2,
        "h3_concurrent_tasks_paid": 15,
        "text_rpm_free": 20,
        "text_rpm_paid": 200,
        "task_visibility_days": 7,
    },
}
