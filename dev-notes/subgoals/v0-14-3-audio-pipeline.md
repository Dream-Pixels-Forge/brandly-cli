# Subgoals — v0.14.3 Audio Pipeline (sound_design becomes real)

**Status:** ✅ Complete  
**Version:** v0.14.3  
**Base:** brandly-cli 0.14.2

---

## Overview

The `sound_design` tool must generate real audio files instead of just writing JSON metadata. This requires:
1. Voiceover (TTS) generation via MiniMax
2. Music/SFX/foley generation via MiniMax music API
3. Download and local file persistence
4. Proper cost tracking and error handling

---

## Subgoals

### 1.1 Audio Client Implementation
**Status:** ✅ Complete (existing)

The `audio_client.py` module already exists with `generate_tts()` and `generate_music()` functions. Verify implementation is correct.

**Acceptance Criteria:**
- [x] `generate_tts()` calls MiniMax TTS endpoint and returns `{url, hex, model, voice_id}`
- [x] `generate_music()` calls MiniMax music endpoint and returns `{url, duration_ms, model, sample_rate, bitrate}`

---

### 1.2 sound_design Tool Enhancement
**Status:** ✅ Complete

The `_sound_design` function in `agent_tools/pre_production.py` already fully implements audio downloading.

**Acceptance Criteria:**
- [x] `brandly sound-design --type voiceover --prompt "Hello world"` produces local MP3 file
- [x] `brandly sound-design --type music --prompt "cinematic orchestral" --duration 30` produces local MP3 file
- [x] Audio files stored in `production/<id>/audio/<category>/<track_id>.mp3`
- [x] JSON metadata record created alongside audio file
- [x] Download failure is non-fatal (metadata kept, no local file) – already documented
- [x] Provider error surfaces as honest error, not silent no-op

**Test Files:**
- `tests/test_agent_tool_audio.py` (4 tests, all passing)

---

### 1.3 Skill Documentation
**Status:** ✅ Complete

`skills/brandly-audio/SKILL.md` exists with comprehensive documentation.

**Acceptance Criteria:**
- [x] Tool contract for `sound_design` documented in Section 4
- [x] Parameter schema matches implementation
- [x] Output schema documented

---

### 1.4 MCP Manifest Integration
**Status:** ✅ Complete

The `sound_design` tool is properly exposed via MCP with correct annotations.

**Acceptance Criteria:**
- [x] Tool appears in `brandly tools --json` output
- [x] MCP annotations: `readOnlyHint: false, destructiveHint: false, idempotentHint: false`

---

## Implementation Order (TDD)

1. **Write failing tests** for audio file download and storage
2. **Verify audio_client implementation** against MiniMax API
3. **Enhance _sound_design** to call audio_client and download files
4. **Add cost tracking** records to cost.json
5. **Verify MCP exposure** via brandly tools --json

---

## Dependencies

- MiniMax API credentials (TTS and Music endpoints)
- `httpx` for file downloads (already in dependencies)
- `AGNES_API_KEY` or equivalent audio provider key

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Audio download timeout | 60s timeout with retry envelope |
| Large audio files | Stream download, chunked write |
| Provider rate limits | Per-project audio rate tracking |
| No provider key | Honest error, not silent failure |