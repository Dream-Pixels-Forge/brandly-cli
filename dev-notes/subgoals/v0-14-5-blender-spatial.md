# Subgoals — v0.14.5 Blender Spatial Execution

**Status:** ✅ Complete  
**Version:** v0.14.5  
**Prerequisite:** v0.14.4

---

## Overview

Enable real Blender rendering for spatial blocking - creating camera position/rotation, depth maps, and keyframes from spatial records.

---

## Problem Statement

The `spatial_blocking` function in `pre_production.py` writes JSON records but doesn't actually render with Blender. Agnes keyframe mode needs:
1. First/last frame images for composition guides
2. Depth maps for spatial understanding
3. Camera position/angle data

---

## Subgoals

### 3.1 Blender Rendering Engine
**Status:** ✅ Complete

Create headless Blender rendering capability.

**Acceptance Criteria:**
- [x] `render_blender_scene()` function renders frames
- [x] Supports camera position, rotation, lens_mm settings
- [x] Renders depth maps
- [x] Renders keyframe images
- [x] Fails honestly if Blender not installed

**Test Plan:**
- Test render with sample Blender config
- Verify depth map output exists

---

### 3.2 Camera Position Rendering
**Status:** ✅ Complete

`spatial_blocking` writes actual renders to `3d-spatial/`.

**Acceptance Criteria:**
- [x] Camera position/rotation rendered to `cameras/`
- [x] Depth maps written to `depthmaps/`
- [x] Keyframes written to `keyframes/`
- [x] Blender script generated from `lens_mm`, camera params, `aspect_ratio`

**Test Plan:**
- `spatial_blocking --shot-id shot-001 --lens-mm 35mm` produces depth map under `3d-spatial/depthmaps/`

---

### 3.3 Integration with Agnes Keyframe Mode
**Status:** ✅ Complete

Connect spatial renders to video generation.

**Acceptance Criteria:**
- [x] `first_frame` and `last_frame` can be spatial renders
- [x] Depth maps available as reference inputs
- [x] Camera data can inform video prompts

**Test Plan:**
- Generate spatial block, then video with first_frame

---

### 3.4 EEVEE vs Workbench Fallback
**Status:** ✅ Complete

Handle different Blender render engines.

**Acceptance Criteria:**
- [x] EEVEE for quality (default)
- [x] Workbench for headless fallback
- [x] Auto-detect OpenGL availability

**Test Plan:**
- Test render in headless environment
- Verify fallbacks work

---

## Implementation Order (TDD)

1. **Write tests** for Blender render output
2. **Create render function** for basic frame
3. **Add depth map rendering**
4. **Integrate with spatial_blocking**
5. **Add EEVEE/workbench detection**

---

## Dependencies

- Blender 3.0+ installed (headless mode)
- `blender --background` command available
- Camera/lens presets defined

---

## Related Skills

- `brandly-3d-spatial` - spatial reference documentation
- `brandly-video-generation` - keyframe mode usage
- `brandly-camera` - camera language integration