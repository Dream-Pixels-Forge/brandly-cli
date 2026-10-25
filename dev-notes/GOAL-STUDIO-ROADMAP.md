# GOAL — brandly-cli: Agentic Film Studio Roadmap

> **Project:** brandly-cli  
> **Category:** `Dev/cli/brandly-cli`  
> **Base version:** `0.14.2`  
> **Status:** Draft — awaiting audit  
> **Program:** Distribute all studio-grade improvements across versioned releases  
> **North star:** brandly-cli is not an AI video generator. It is an agentic film studio CLI — a complete production office (script, casting, storyboard, dailies, gate, stitch, publish, metrics) where AI providers are the crew and human directors approve the dailies.

---

## 1. Objective

Ship every studio-grade improvement identified in the deep brainstorm as a **versioned release plan** starting at `0.14.3`. Each version delivers one coherent capability set (tools A added in X.Y.Z, tools B added in X.Y.Z+1, etc.) so that:

1. **Every version is shippable** — CI green, tests pass, no half-features.
2. **No unbounded loops** — each version has a defined scope and acceptance criteria.
3. **Skill ↔ tool ↔ CLI ↔ MCP mapping** is preserved — every new tool is documented in its owning `skills/*/SKILL.md` and exposed through the MCP manifest.
4. **Data honesty** — nothing is reported as `PASS` unless it was actually measured.

---

## 2. Version Roadmap

### v0.14.3 — Audio Pipeline (sound_design becomes real)

| Tool | Skill | What it does |
|------|-------|--------------|
| `sound_design` | (new `brandly-audio` skill) | Generates soundtrack / SFX / foley / voiceover via MiniMax/Higgsfield audio endpoints; writes to `production/<id>/audio/{category}/`; returns duraton + local path |

**Deliverables:**
- `sound_design` tool actually calls an audio provider instead of writing JSON metadata only
- Audio files persisted under `production/<id>/audio/soundtrack/`, `sfx/`, `foley/`, `voiceover/`
- `list_jobs`/`job-poll` aware of audio jobs (not just video)
- Cost tracker records audio credit spend

**Acceptance criteria:**
- `brandly sound-design --type music --description "opening theme" --prompt "cinematic orchestral"` produces a local `.mp3`/`.wav` file
- Tool returns `output_path` pointing at the real file
- No provider = honest error, not a silent no-op

**MCP annotations:** `readOnlyHint: false, destructiveHint: false, idempotentHint: false`  
**Domain:** `pre_production`

---

### v0.14.4 — Download + Verify + Dailies Review + Multi-Provider Router (Agnes output becomes real media)

| Tool | Skill | What it does |
|------|-------|--------------|
| `create_video_task` | `brandly-video-generation` | After Agnes returns `video_id`, download the clip, verify duration/resolution via ffprobe, store locally with checksum |
| `poll_video` | `brandly-video-generation` | On completion, auto-downloads video and merges verification results (`requested_s`, `measured_s`, `delta_s`, `duration_status`) |
| `produce` (existing) | `brandly-video-generation` | Passes `project_id` and `requested_duration` to `poll_video`; stores duration truth in task record |
| `stitch` (existing) | `dpf-senior-editor` | Before stitching, checks each clip is approved in the review queue; fails unless `--force` |
| `review_queue` / `review_approve` / `review_reject` | `brandly-review-queue` | CLI commands for the dailies review queue; approve/reject clips; reject re-flags shot for re-run |
| `VideoBackend` protocol | `brandly-video-generation` | Pluggable video backend interface — Agnes is one implementation; `shot_runner` depends on protocol |

**Deliverables:**
- `create_video_task` waits for completion, downloads the MP4/WebM, writes to `production/<id>/videos/scenes/<video_id>.mp4`
- Shot record gains `requested_s`, `measured_s`, `delta_s` (duration truth — G7 from GOAL-ACCURACY)
- Short clips are **never** recorded as `OK`
- `stitch` refuses to assemble unapproved clips (unless `--force`)
- `brandly review queue` lists unapproved clips; `review approve`/`review reject` manage them
- `VideoBackend` protocol with `AgnesVideoBackend` implementation; `shot_runner` depends on protocol not concrete client

**Acceptance criteria:**
- A stub Agnes returning 4.5s for a 6s request produces a `SHORT` record, not `OK`
- Local file exists and is playable after `produce --wait`
- Checksum matches source download
- `stitch` fails on unapproved clips unless `--force`
- `brandly review queue` lists unapproved clips; `review approve`/`review reject` manage them

**MCP annotations:** `readOnlyHint: false, destructiveHint: false, idempotentHint: false`

---

### v0.14.5 — Blender Spatial Execution (spatial_blocking renders frames)

| Tool | Skill | What it does |
|------|-------|--------------|
| `spatial_blocking` | `brandly-3d-spatial` | Launches Blender headless (via natron or subprocess) to render camera frames, depth maps, keyframes from the spatial record |

**Deliverables:**
- `spatial_blocking` writes actual camera position/rotation, depth maps, and keyframe images to `3d-spatial/{cameras,keyframes,depthmaps}/`
- Blender script generated from `lens_mm`, `camera_position`, `camera_rotation`, `aspect_ratio`
- Depth map PNGs are real renders, not placeholders

**Acceptance criteria:**
- `spatial_blocking --shot-id shot-001 --lens-mm 35mm ...` produces a depth map file under `3d-spatial/depthmaps/`
- Render fails honestly if Blender is not installed

**MCP annotations:** `readOnlyHint: false, destructiveHint: false, idempotentHint: false`  
**Domain:** `pre_production`

| Tool | Skill | What it does |
|------|-------|--------------|
| `spatial_blocking` | `brandly-3d-spatial` | Launches Blender headless (via natron or subprocess) to render camera frames, depth maps, keyframes from the spatial record |

**Deliverables:**
- `spatial_blocking` writes actual camera position/rotation, depth maps, and keyframe images to `3d-spatial/{cameras,keyframes,depthmaps}/`
- Blender script generated from `lens_mm`, `camera_position`, `camera_rotation`, `aspect_ratio`
- Depth map PNGs are real renders, not placeholders

**Acceptance criteria:**
- `spatial_blocking --shot-id shot-001 --lens-mm 35mm ...` produces a depth map file under `3d-spatial/depthmaps/`
- Render fails honestly if Blender is not installed

**MCP annotations:** `readOnlyHint: false, destructiveHint: false, idempotentHint: false`  
**Domain:** `pre_production`

---

### v0.14.8 — Post-Production Assembly (stitch becomes a real editor)

| Tool | Skill | What it does |
|------|-------|--------------|
| `stitch` (existing) | `dpf-senior-editor` | Transition library (fade, wipe, dissolve, iris, L-cut, J-cut), color grade LUTs (cinematic, teal/orange, desaturated, B&W), caption burning from SRT |
| `editor` (existing) | `dpf-senior-editor` | Per-clip trim, transition, grade, volume persisted as edit decisions; applied at stitch time |

**Deliverables:**
- `stitch --transition fade --transition-duration 0.5 --color-grade cinematic` applies real ffmpeg filters
- `editor` cut decisions (start_time, end_time, transition, color_grade, volume) are honored during assembly
- Caption/SRT burning for social vertical formats (9:16 with safe zones)

**Acceptance criteria:**
- `stitch` with `--transition fade` produces a crossfade, not a hard cut
- `--color-grade teal_orange` visibly shifts the output
- SRT captions are burned into the output video

**MCP annotations:** `readOnlyHint: false, destructiveHint: false, idempotentHint: false`  
**Domain:** `production`

---

### v0.14.9 — Autonomous Orchestrator (the production office runs itself)

| Tool | Skill | What it does |
|------|-------|--------------|
| `plan` (existing) | `brandly-init` | Orchestrator reads `plan --json`, dispatches phase workers |
| `approve` (existing) | `brandly-film-collaborator` | Human gate escalation — agent escalates via `approve` on failure |
| `memory` (existing) | `brandly-init` | Shared project memory: agents read/write `docs/general/` + memorius vector index |

**Deliverables:**
- `brandly run <id> --execute` walks the phase plan autonomously: trends → concept → bible → casting → screenplay → script → asset → audio → re_edit → validate → publish
- On gate failure, agent escalates via `brandly approve <id> <phase>` instead of silent failure
- Agents can query shared memory: "what did Elias look like in Scene 2?" → returns reference plate path

**Acceptance criteria:**
- A full `brandly run --execute` on a fresh project produces a publishable short film end-to-end
- Gate failure triggers an `approve` escalation (not a silent continue)
- Memory query returns the correct reference plate path for a named character

**MCP annotations:** `plan`/`status`/`progress`/`estimate`/`memory` read-only; `approve` write-destructive  
**Domain:** `project`

---

### v0.14.10 — Distribution & Analytics (publish for real)

| Tool | Skill | What it does |
|------|-------|--------------|
| `publish` (existing) | `brandly-film-collaborator` | Actual YouTube/TikTok/Instagram upload with credential management (not dry-run) |
| `metrics` (existing) | `brandly-film-collaborator` | Automatic metrics pull from platform APIs (views, retention, engagement) → `metrics ingest` |
| `export-platforms` (existing) | `brandly-film-collaborator` | Versioned releases (`v1.0`, `v1.1` director's cut, `v2.0` international cut) |

**Deliverables:**
- `brandly publish <id> --platform youtube` posts the stitched video (not just renders payload)
- `brandly metrics ingest` pulls YouTube Analytics and writes to project metrics
- Platform-optimized exports: 9:16 TikTok, 1:1 Instagram, 16:9 YouTube with platform bitrates

**Acceptance criteria:**
- `--dry-run` still renders the exact payload without posting
- Live upload returns a public URL
- Metrics ingest stores views/retention in project-local snapshots

**MCP annotations:** `publish`/`export-platforms` write-destructive; `metrics` read-only  
**Domain:** `production`

---

### v0.15.0 — Lip-Sync & Co-Speech (dialogue shots move mouths)

| Tool | Skill | What it does |
|------|-------|--------------|
| `director` (existing) | `brandly-film-director` | Dialogue shots with co-speech video generation (MiniMax H3 co-speech or Agnes equivalent) |
| `sound_design` (existing) | `brandly-audio` | Voiceover audio drives lip-sync on the generated character |

**Deliverables:**
- Dialogue shots generate video where the character's mouth moves to the audio track
- TTS audio from `sound_design` is used as the co-speech driver
- Lip-synced clip stored under `production/<id>/videos/scenes/`

**Acceptance criteria:**
- A dialogue shot with TTS audio produces a video with synchronized mouth movement
- Non-dialogue shots (no audio) are not affected

**MCP annotations:** `director` write

---

### v0.15.1 — Credit Ledger Enforcement (no silent over-spend)

| Tool | Skill | What it does |
|------|-------|--------------|
| `estimate` (existing) | `brandly-init` | Hard credit budget enforcement: `produce` stops when `spent >= budget` |
| `record_cost` (existing) | `brandly-init` | Every provider call records credit spend; no silent over-spend |

**Deliverables:**
- `produce` checks `spent >= budget` before every shot; refuses to continue if over
- `record_cost` is called for every provider API call (image, video, audio)
- `estimate --style cinematic --shots 5` shows remaining quota and proposes multi-day schedule if over 500s/day

**Acceptance criteria:**
- A `--budget 10` project stops after ~2 shots (video ~5 credits each)
- No silent over-spend: every credit charge is recorded in `cost.json`
- `--target-duration 900` under 500s remaining proposes a 2-day schedule *before* spending

**MCP annotations:** `estimate`/`record_cost` read-only/write; `produce` write  
**Domain:** `project`

---

### v0.15.2 — Script Breakdown & Storyboard Visualization

| Tool | Skill | What it does |
|------|-------|--------------|
| (new) `script_breakdown` | (new `brandly-script-breakdown` skill) | Auto-extract scenes, characters, props, locations from `.fdx` or `.md` screenplay into shot lists |
| `storyboard` (existing) | `brandly-storyboard` | Automatic storyboard grid generation from `scenes.json` (4x4 graphite contact sheet) |

**Deliverables:**
- `brandly script-breakdown --screenplay screenplay.md` outputs `scenes.json` with per-shot characters, props, locations
- `brandly storyboard` renders a 4x4 contact sheet grid from `scenes.json`
- Casting reads the bible's Section 4 verbatim (already documented)

**Acceptance criteria:**
- A `.md` screenplay with 3 scenes produces 3 scene entries in `scenes.json`
- `storyboard` produces a valid image contact sheet
- Casting references characters from `scenes.json` without manual entry

**MCP annotations:** `script_breakdown` read-only; `storyboard` write  
**Domain:** `pre_production`

---

### v0.15.3 — Casting Validation & Wardrobe Continuity

| Tool | Skill | What it does |
|------|-------|--------------|
| `cast_characters` | `brandly-casting` | Reference images validated against Agnes requirements (resolution, face visibility) before injection |
| `try_wardrobe` | `brandly-casting` | Wardrobe continuity log: tracks which character wears what in which scene |
| `generate_sheet` | `brandly-character-sheet` / location/object/vehicle/mecha/animal/plant-sheet | Reference plate auto-conversion to webp before injection (enforced) |

**Deliverables:**
- `cast_characters` rejects plates that are too small or lack face visibility
- `try_wardrobe` warns if "Elias wears black soutane in Scene 3 but brown coat in Scene 7"
- Large PNG plates auto-converted to webp before being injected as video references

**Acceptance criteria:**
- A 50×50 PNG reference plate is rejected with a clear error
- Wardrobe conflict between two shots is surfaced before `produce`
- A 10MB PNG plate is converted to ~200KB webp automatically

**MCP annotations:** `cast_characters`/`try_wardrobe`/`generate_sheet` write  
**Domain:** `pre_production`

---

## 3. How Each Version Stands Out

| Version | Competitor does | brandly does |
|---------|----------------|--------------|
| v0.14.3 | Type prompt → get silent video | Generate synchronized audio + video with verified download |
| v0.14.4 | Hope the clip is the right length | Measure every clip; never ship short; continuation take |
| v0.14.5 | Ship whatever the model generates | Dailies review + gate blocks bad shots before stitch |
| v0.14.6 | Single provider outage kills the run | Failover router across Agnes/Hailuo/Kling/Seedance |
| v0.14.7 | JSON camera notes | Real Blender depth maps + keyframes for Agnes composition |
| v0.14.8 | Hard cut + raw color | Transitions, LUTs, burned captions, platform-safe zones |
| v0.14.9 | Human types every prompt | `brandly run --execute` walks the pipeline autonomously |
| v0.14.10 | Dry-run publish only | Real YouTube/TikTok upload + analytics pull |
| v0.15.0 | Silent talking heads | Lip-synced dialogue from TTS audio |
| v0.15.1 | Hidden subscription costs | Credit ledger with hard budget stop + multi-day scheduling |
| v0.15.2 | Manual shot list | Auto script breakdown + storyboard contact sheet |
| v0.15.3 | Manual continuity tracking | Wardrobe/prop continuity warnings + plate auto-conversion |

---

## 4. Guardrails (Non-Negotiable)

| Rule | Rationale |
|------|-----------|
| Every version CI green — `pytest`, `ruff`, `mypy`, `build` | No half-features shipped |
| Every new tool has a `SKILL.md` in `skills/brandly-*` | Skill is the source of truth; code implements it |
| Every new tool exposed in MCP manifest with `annotations` | Agents can discover and call it safely |
| No version adds >1 major capability | Prevents unbounded scope creep |
| `UNVERIFIED` is never `PASS` (G11) | Data honesty — trust reality, not requests |
| `--dry-run` never posts; live posting requires stored credential | Security baseline |
| Version bump in `__about__.py` only; hatch propagates | Single source of truth |

---

## 5. Acceptance Summary

| Milestone | Version | Status |
|-----------|---------|--------|
| Audio pipeline real | v0.14.3 | Planned |
| Download + verify clips | v0.14.4 | Planned |
| Dailies review + gate blocks stitch | v0.14.5 | Planned |
| Multi-provider router | v0.14.6 | Planned |
| Blender spatial execution | v0.14.7 | Planned |
| Transitions + LUTs + captions | v0.14.8 | Planned |
| Autonomous orchestrator | v0.14.9 | Planned |
| Real publish + analytics | v0.14.10 | Planned |
| Lip-sync / co-speech | v0.15.0 | Planned |
| Credit ledger enforcement | v0.15.1 | Planned |
| Script breakdown + storyboard | v0.15.2 | Planned |
| Wardrobe continuity + plate conversion | v0.15.3 | Planned |

**End state:** brandly-cli is a complete agentic film studio CLI — script → casting → storyboard → asset (with gate) → audio → lip-sync → stitch → publish → metrics — where every frame is measured, every shot is gated, every credit is tracked, and every version is shippable.

---

## 6. Notes

- Current version: `0.14.2` (`src/brandly_cli/__about__.py`)
- Version bumps follow the single-source-of-truth rule: bump `__about__.py`, hatch propagates to wheel/sdist metadata, CLI `--version`, MCP server info, and web config API
- Each version maps to a `dev-notes/GOAL-*.md` file following the repo convention
- Releases follow the DPF delivery pipeline: commit → review → stage → deploy → deliver (Section 6 of `AGENTS.md`)
