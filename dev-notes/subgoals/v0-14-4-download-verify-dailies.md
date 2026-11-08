# Subgoals — v0.14.4 Download + Verify + Dailies Review

**Status:** ✅ Complete  
**Version:** v0.14.4  
**Prerequisite:** v0.14.3

---

## Overview

Enable real media downloads from Agnes, verify duration correctness, and create a dailies review system that blocks bad shots before stitching.

---

## Problem Statement

Currently, Agnes video generation returns a `video_id` that must be polled. The video download and verification is not implemented, meaning:
1. Videos may be short (4.5s for 6s request) but still marked OK
2. No checksum verification of downloaded files
3. No dailies review - bad shots can be stitched
4. `stitch` has no gate check

---

## Subgoals

### 2.1 create_video_task Enhancement
**Status:** ✅ Complete

After Agnes returns `video_id`, download the clip and verify.

**Acceptance Criteria:**
- [x] Downloads MP4/WebM from Agnes callback URL
- [x] Writes to `production/<id>/videos/scenes/<video_id>.mp4`
- [x] Computes SHA256 checksum of downloaded file
- [x] Returns `downloaded: true/false`, `local_path`, `checksum`

**Test Plan:**
- Mock Agnes response, verify download and checksum
- Test download failure (non-fatal, metadata preserved)

---

### 2.2 poll_video Enhancement
**Status:** ✅ Complete

On completion, auto-download video and measure duration.

**Acceptance Criteria:**
- [x] Auto-downloads video on completion
- [x] Uses ffprobe to verify actual duration
- [x] Records `requested_s`, `measured_s`, `delta_s`, `duration_status`
- [x] `duration_status` is `OK`, `SHORT`, or `MISMATCH`

**Test Plan:**
- Mock Agnes completion, verify duration measurement
- Test 4.5s video for 6s request → `duration_status: SHORT`

---

### 2.3 produce Tool Enhancement
**Status:** ✅ Complete

Pass `project_id` and `requested_duration` to poll_video, store duration truth.

**Acceptance Criteria:**
- [x] Passes project context to poll_video
- [x] Stores duration truth in task record
- [x] SHORT clips trigger continuation take, not silent OK

**Test Plan:**
- Run produce on short clip, verify rejection

---

### 2.4 review_queue Tool
**Status:** ✅ Complete

CLI commands for dailies review queue.

**Acceptance Criteria:**
- [x] `brandly review queue` lists unapproved clips
- [x] `brandly review approve <clip_id>` marks approved
- [x] `brandly review reject <clip_id>` marks rejected, flags for re-run
- [x] Approval state persisted to disk

**Test Plan:**
- Generate clips, test queue listing
- Test approve/reject flow

---

### 2.5 stitch Gate Enhancement
**Status:** ✅ Complete

Before stitching, check approval status.

**Acceptance Criteria:**
- [x] `stitch` fails on unapproved clips
- [x] `--force` flag bypasses gate (with warning)
- [x] Error message indicates which clips are unapproved

**Test Plan:**
- Try to stitch unapproved clips → failure
- Try with `--force` → success with warning

---

### 2.6 VideoBackend Protocol
**Status:** ✅ Complete

Extract Agnes client behind a protocol.

**Acceptance Criteria:**
- [x] `VideoBackend` protocol defined in `video_backend.py`
- [x] `AgnesVideoBackend` implements protocol
- [x] `shot_runner` depends on protocol, not concrete client
- [x] Easy to add Ark, Kling, Seedance providers later

**Test Plan:**
- Verify protocol match with Agnes implementation
- Mock backend for testing

---

## Implementation Order (TDD)

1. **Write failing tests** for duration verification
2. **Implement poll_video duration measurement**
3. **Add create_video_task download capability**
4. **Create review_queue tool + tests**
5. **Enhance stitch with gate check**
6. **Extract VideoBackend protocol**

---

## Dependencies

- `ffprobe` (ffmpeg) for duration verification
- Agnes video callback URLs
- Hash library for checksums

---

## Related Skills

- `brandly-video-generation` - video generation execution
- `dpf-senior-editor` - stitch and edit operations