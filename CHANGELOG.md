# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added
- `brandly produce` progress-file runner (`src/brandly_cli/shot_runner.py`):
  a structured shot-list schema (`{"character": ..., "acts": {...}}` with
  per-act prompt `prefix`, `style`, `folder` and plate-stem `refs`/`ref`s),
  plus new flags `--no-auto-refs`, `--character`, `--allow-referenceless`,
  `--max-wait`, `--only` and `--max`. Any of these (or the structured
  schema) routes the run through a resumable progress file
  (`.brandly/<project>/docs/tmp/produce_progress.txt`) instead of the
  production-plan loop, so film production no longer needs an external
  runner script:
  - generated clips are renamed to a deterministic, assembly-friendly
    convention — `Scene-<scene:02d>-Shot-<scene>-<shot-in-scene>.mp4`
    (e.g. `Scene-01-Shot-1-2.mp4` for the second shot of scene 1). The
    scene number comes from an act-level or shot-level `"scene"` key, else
    the act's position in the shot list; the trailing number is the shot's
    position inside that scene. A redo replaces the previous take;
  - plate-stem references resolve under `images/<category>/`, preferring
    the optimized `<stem>.opt.jpg` twins (small reference payloads —
    issue #20 free-tier timeouts);
  - a top-level / `--character` identity anchor attaches only to shots
    whose references include a character plate;
  - transition shots (`"folder": "transition"`) have their clips moved
    to `videos/transition/`;
  - a post-generation step failure (e.g. quality-gate crash) still counts
    as OK when a non-empty clip was downloaded (zero-byte / stranded files
    do not count), and the run stops on the first unrecovered failure
    (re-run the same command to resume). `--only` redoes the named shots
    even if a previous run already recorded them as OK;
  Flat shot lists without the new flags keep the existing production-plan
  behaviour. The routing to the resumable runner is announced on stderr,
  and both produce paths now pass scene/shot numbers through to the
  download (flat lists: scene 1, shot order = list order).
- `brandly video --scene <n> --shot <n>`: name the downloaded clip with the
  deterministic `Scene-<scene:02d>-Shot-<scene>-<shot>.mp4` convention
  (both flags required together; without them the timestamped name stays).
- `layout.media_root(proj_dir, "images"|"videos"|"audio")`: the
  un-categorised media top folder (used by the produce runner).

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
