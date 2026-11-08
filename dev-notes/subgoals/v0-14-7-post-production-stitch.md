# Subgoals — v0.14.7/0.14.8 Post-Production Assembly (stitch becomes real editor)

**Status:** ✅ Complete  
**Version:** v0.14.7/0.14.8  
**Prerequisite:** v0.14.4, v0.14.5

---

## Overview

Transform `stitch` from a simple concat to a real editor with transitions, color grading, caption burning, and platform-safe zones.

---

## Problem Statement

Current `stitch` implementation is basic concat. Need professional-grade assembly:
1. Transitions (fade, wipe, dissolve, iris, L-cut, J-cut)
2. Color grading LUTs (cinematic, teal/orange, desaturated, B&W)
3. Caption/SRT burning for social formats
4. Platform-safe zones (9:16 with title safe)

---

## Subgoals

### 5.1 Transition Library
**Status:** ✅ Complete

Implement various transition effects.

**Acceptance Criteria:**
- [x] `fade` crossfade
- [x] `wipe` directional wipe
- [x] `dissolve` organic fade
- [x] `iris` circular reveal
- [x] `L-cut` audio continues past video cut
- [x] `J-cut` audio before video starts

**Test Plan:**
- Generate test clips with transitions
- Verify visual correctness

---

### 5.2 Color Grade LUTs
**Status:** ✅ Complete

Apply color grading filters.

**Acceptance Criteria:**
- [x] `cinematic` LUT applied
- [x] `teal_orange` LUT applied
- [x] `desaturated` LUT applied
- [x] `bw` (black & white) LUT applied
- [x] `--color-grade` option working

**Test Plan:**
- Apply LUTs to test clip
- Verify visual difference

---

### 5.3 Caption Burning
**Status:** ✅ Complete

Burn SRT captions into video.

**Acceptance Criteria:**
- [x] Read SRT file
- [x] Burn captions at correct timestamps
- [x] Support for social vertical (9:16) formatting
- [x] Safe zone margins respected

**Test Plan:**
- Burn sample SRT to test video
- Verify captions appear correctly

---

### 5.4 editor Tool Enhancement
**Status:** ✅ Complete (ENHANCEMENT)

Per-clip edit decisions persisted and applied.

**Acceptance Criteria:**
- [x] `start_time`, `end_time` for trimming
- [x] `transition` type per clip
- [x] `color_grade` per clip
- [x] `volume` adjustment per clip
- [x] Edit decisions apply at stitch time

**Test Plan:**
- Set edit decisions, run stitch
- Verify decisions applied

---

### 5.5 Platform Export Optimization
**Status:** ✅ Complete (NEW)

Export-specific settings per platform.

**Acceptance Criteria:**
- [x] 9:16 TikTok export with vertical safe zones
- [x] 1:1 Instagram export
- [x] 16:9 YouTube export with platform bitrates
- [x] `--platforms tiktok,instagram,youtube` option

**Test Plan:**
- Export to each platform
- Verify dimensions and bitrates

---

## Implementation Order (TDD)

1. **Write tests** for transition effects
2. **Implement fade transition**
3. **Add other transitions**
4. **Implement color grading LUTs**
5. **Add caption burning**
6. **Enhance editor decisions**
7. **Add platform exports**

---

## Dependencies

- FFmpeg for video processing
- LUT files for color grading
- SRT format support

---

## Related Skills

- `dpf-senior-editor` - editing operations
- `brandly-video-generation` - shot generation
- `brandly-consistency` - color continuity