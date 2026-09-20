# Changelog

All notable changes to this project are documented here.

## [0.3.15] — 2026-09-20

### Added
- Image converter (`src/brandly_cli/image_convert.py`): large local reference
  images auto-shrink to webp/jpeg before base64 upload (JPEG for opaque
  images, WebP when alpha must be preserved; only when it saves ≥ 10 KB;
  opt-out with `BRANDLY_IMAGE_CONVERT=off`).
- `brandly produce <project_id> --shots shots.json`: multi-shot film
  production driven by the production plan (`docs/plan/production_plan.md`,
  the source of truth). ALL shots are registered on the plan first, then
  generated **one shot at a time** with a 60 s wait between requests (Agnes:
  1 request/minute). No batch/parallel mode. Resumable: COMPLETED shots are
  skipped, a failure stops the run and remaining shots stay PENDING.
- `brandly video --no-auto-refs` and `--auto-ref-category <name>` to scope
  auto-injected reference images (issue #20).
- `brandly reference <project_id> --image <path> [--no-generate]` to import
  an existing plate as `primary_reference` without generating (issue #23).
- `brandly batch --interval` (default 60.0 s): rate-limited variant
  submission, kept as the future batch path for when Agnes supports true
  batch (decision: batch NOT removed).

### Fixed
- `create_video_task` takes `style_preset` — the preset now follows `--style`
  (cinematic only for cinematic) instead of being hardcoded; disabled for
  non-photographic styles (issue #21).
- Video create failures print `ExceptionType: detail` — empty timeout
  messages no longer vanish; create timeout raised 60 s → 180 s (issue #24).
- `brandly jobs` degrades gracefully on HTTP 404 (unsupported endpoint)
  with a hint to use `brandly job-resume <video_id>` (issue #19).
- Skills/docs aligned: `refs/` → `images/<category>/` (single layout),
  storyboard + video-generation skills document `brandly produce`,
  troubleshooting model pin corrected to `agnes-video-2.5-flash`.
- README documents `brandly produce`, the converter, scoped refs and the
  reference import; `.env.example` documents `BRANDLY_IMAGE_CONVERT`.

### Closed issues
- #19, #20, #21, #22, #23, #24.

## [0.3.14] — 2026-09-20

- Single layout (no refs/), plan reuse + production plan, HITL gates,
  keyframe archiving.
