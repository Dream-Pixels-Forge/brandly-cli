---
name: brandly-audio
description: >
  Audio generation for brandly-cli — text-to-speech (voiceover) and music
  generation via MiniMax Audio API. Produces downloadable MP3 files stored under
  production/<id>/audio/{category}/. Triggers on "sound design", "audio track",
  "voiceover", "TTS", "music generation", "soundtrack", "sfx", "foley".
  NOT for video generation (use brandly-video-generation), NOT for image
  generation (use brandly-video-generation), NOT for spatial/3D blocking
  (use brandly-3d-spatial).
---

# Brandly Audio

## Concern separation (read first)

| Skill | Concern | Responsibility |
|-------|---------|----------------|
| **brandly-audio** (this skill) | **HOW** audio is generated | TTS (voiceover) and music generation via MiniMax Audio API; file download and local persistence |
| **brandly-init** | **WHERE** things land | Layout contract, directory structure, artifact paths, phase order, gate approvals, project init cwd enforcement |
| **brandly-video-generation** | **HOW** video execution | CLI execution via `brandly video` / `brandly produce` |

This skill does NOT teach project init, phase ordering, artifact placement, or gate management. For where each artifact lands (audio goes to `production/<id>/audio/{category}/`), see brandly-init. For CLI execution of video, see brandly-video-generation. This skill only covers HOW to generate and download audio.

## Routing Table

| Want to... | Read |
|------------|------|
| TTS voiceover generation | Section 1 |
| Music / SFX generation | Section 2 |
| Audio file download + storage | Section 3 |
| Tool contract for `sound_design` | Section 4 |

---

## 1. Text-to-Speech (Voiceover)

MiniMax `speech-2.8-hd` TTS endpoint. Converts text to spoken audio.

- Default model: `speech-2.8-hd`
- Default voice: `English_Insightful_Speaker`
- Output format: URL (MP3)
- Supports inline tags like `(laughs)`, `(sighs)` and pause markers

Call: `generate_tts(text, model, voice_id, output_format, speed, vol, pitch, emotion)`

Returns: `{url, hex, model, voice_id}` where `url` is a downloadable MP3 URL.

---

## 2. Music Generation

MiniMax `music-3.0` music generation endpoint. Generates background music, SFX, or instrumental tracks.

- Default model: `music-3.0`
- Default duration: 30 seconds
- Instrumental by default (can include lyrics)
- Output format: URL (MP3)

Call: `generate_music(prompt, model, duration_seconds, instrumental, lyrics, sample_rate, bitrate, format)`

Returns: `{url, duration_ms, model, sample_rate, bitrate}` where `url` is a downloadable MP3 URL.

---

## 3. Audio File Download + Storage

After generation, the remote URL is downloaded via httpx and stored locally:

```
production/<project_id>/audio/<category>/<track_id>.mp3
```

where `<category>` is one of: `soundtrack`, `sfx`, `foley`, `voiceover`, `general`.

The `<track_id>` is derived from the description (first 40 chars, lowercased, spaces → underscores).

A `SoundTrack` record is also written as JSON alongside the audio file.

---

## 4. Tool contract for `sound_design`

The `sound_design` tool maps to this skill. Inputs:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | Yes | Project ID |
| `sound_type` | string | Yes | `music` \| `sfx` \| `foley` \| `voiceover` |
| `description` | string | Yes | Track description (also used for track_id) |
| `prompt` | string | Yes | TTS text or music generation prompt |
| `duration` | integer | No | Duration in seconds (music only) |
| `output_path` | string | No | Explicit output path (override) |
| `category` | string | No | `soundtrack` \| `sfx` \| `foley` \| `voiceover` \| `general` (default `general`) |
| `root` | string | No | Project root directory |

Outputs:
- `project_id`, `type`, `description` — echoed inputs
- `output_path` — local MP3 file path (empty if download failed)
- `url` — remote download URL from the provider
- `duration_ms` — duration from provider (music only)
- `path` — JSON metadata file path
- `downloaded` — boolean, whether local download succeeded

The `sound_design` tool is in the `pre_production` domain and is **write** (spends credits, creates audio files).
