---
name: brandly-init
description: Teaches agents WHERE every brandly-cli pipeline artifact lands — the layout contract, directory structure, phase-by-phase execution order, gate approvals, and anti-drift guards. Use for project init, pipeline orchestration, artifact placement, and gate management. NOT for generation technique (prompting, camera, lighting, provider routing) — that is brandly-video-generation.
---

# brandly-init — Brandly CLI Pipeline Layout & Orchestration

## Concern separation (read first)

| Skill | Concern | Responsibility |
|-------|---------|----------------|
| **brandly-init** (this skill) | **WHERE** things land | Layout contract, directory structure, artifact paths, phase order, gate approvals, project init, verification |
| **brandly-video-generation** | **HOW** things are generated | Image/video/audio generation, prompting, camera, lighting, provider routing, download, assembly, editing |

**brandly-init does NOT teach prompting, camera moves, lighting presets, provider models, or generation parameters.** It teaches where each artifact must be placed, in what order phases run, and when gates must pass before approval.

## Quick start

```bash
# 1. Discover the tool surface
brandly tools --json

# 2. Init a project (in the current working directory)
brandly init -n <name> -i "<idea>" -s cinematic --shots 8 --target-duration 60 --budget 800

# 3. Read the plan before each phase (WHERE artifacts go)
brandly plan <id> --json

# 4. Run + approve each phase in mandatory order
brandly run <id>
brandly approve <id> <phase>

# 5. Generate video (HOW — see brandly-video-generation for technique)
brandly produce <id> --shots .brandly/<id>/shots.json --interval 60 --character <name>

# 6. Assemble + export
brandly stitch <clips> --output videos/final.mp4
brandly export-platforms <id> --platforms tiktok,instagram
```

## Core rules (never violate)

1. `brandly tools --json` before any call.
2. `brandly plan <id> --json` before starting a phase.
3. Never call AI providers directly — use brandly tools only.
4. Gate before advancing: artifacts must exist AND pass `brandly gate` before `brandly approve`.
5. Layout contract: docs in `.brandly/<id>/docs/<subdir>/` — never improvise paths.
6. Media trees: `pre-production/<id>/` and `production/<id>/` — no scratch files.
7. On 503 `video_queue_full` / ReadTimeout: WAIT and re-run `produce` — never patch shots.
8. Read-only tools (`status`, `progress`, `plan`, `list_*`, `get_*`, `run_gate`) are safe anytime.
9. **Init directory enforcement**: `brandly init` must always create the project in the **current working directory** (where the terminal is launched). Before running init, confirm `pwd` is the intended project root. After init, verify `AGENTS.md` and `.brandly/` exist in cwd. If brandly init created the project in an ancestor `.brandly` store instead of cwd, re-run from the correct directory. Never let init drift to a user root or ancestor store.

## Phase chain (mandatory order — WHERE artifacts land at each phase)

```
trends → concept → bible → casting → screenplay → script → asset → audio → re_edit → validate → publish
```

### Phase → Artifact → Location mapping

| Phase | Artifact | Where it lands | Gate required |
|-------|----------|----------------|---------------|
| init | `project.json`, `AGENTS.md` | `.brandly/<id>/` and project root cwd | `status <id>` |
| trends | `trends.md` | `docs/general/trends.md` | `status <id>` |
| concept | `concept.md` | `docs/general/concept.md` | `status <id>` |
| bible | `production_bible.md` (Sec. 4: Characters) | `docs/bible/production_bible.md` | `approve <id> bible` |
| casting | cast images, sheets, location sheets, wardrobe | `pre-production/<id>/character\|mecha/\|location/\|wardrobe/` | `gate` then `approve <id> casting` |
| screenplay | `screenplay.md` | `docs/screenplay/screenplay.md` | `approve <id> screenplay` |
| script | `shots.json` | `.brandly/<id>/shots.json` | `status <id>` |
| asset | scene clip files | `production/<id>/` | `gate --all-scenes` then `approve <id> asset` |
| audio | `music.mp3` | `production/<id>/audio/` | `status <id>` |
| re_edit | `final.mp4` | `videos/final.mp4` | `stitch` exit 0 |
| validate | scene-gate verdicts | `docs/tmp/gate_*.md` | `gate --all-scenes` exit 0 |
| publish | platform deliverables | `<project>/export/` | `export-platforms` exit 0 |

## Casting gate (most commonly mis-landed — WHERE check)

Casting is complete ONLY when ALL exist AND gate-passed AND user-approved:

| Artifact | Where it lands |
|----------|---------------|
| Character cast image | `pre-production/<id>/character/char_<name>_cast-*.jpg` |
| Mecha cast image | `pre-production/<id>/mecha/<name>/char_<name>_cast-*.jpg` |
| Character sheet | `pre-production/<id>/mecha/sheets/char_<name>_sheet.jpg` (or `character/sheet/`) |
| Location sheet | `pre-production/<id>/location/loc_<name>_sheet-*.jpg` |
| Wardrobe variation | `pre-production/<id>/wardrobe/char_<name>_wardrobe-*.jpg` or `mecha/<name>/` |

## Verification checklist (before declaring any phase complete)

- [ ] `brandly plan <id> --json` read for current phase
- [ ] All required artifacts exist at correct paths (WHERE check)
- [ ] `brandly gate` passed on all gated artifacts
- [ ] `brandly approve <id> <phase>` executed
- [ ] No scratch/debug files in `pre-production/` or `production/`
- [ ] Phase chain order respected (no skipping, no reordering)
- [ ] `AGENTS.md` and `.brandly/` exist in cwd after init

## Detailed reference

See [REFERENCE.md](REFERENCE.md) for full phase-by-phase commands, artifact locations, gates, and anti-drift guards. Generation technique (prompting, camera, lighting, provider routing, download, assembly, editing) lives in `brandly-video-generation`.
