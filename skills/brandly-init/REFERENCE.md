# brandly-init — Detailed Phase Reference (WHERE things land)

This file contains the complete phase-by-phase reference for the brandly-cli pipeline. SKILL.md holds the quick start; this file holds the details.

**Concern separation:** `brandly-init` teaches WHERE artifacts land (layout contract, directory structure, phase order, gates). `brandly-video-generation` teaches HOW things are generated (image/video/audio prompting, camera, lighting, provider routing, download, assembly, editing). Do not mix the two.

---

## Related skills — no collision

| Skill | Concern | Responsibility |
|-------|---------|----------------|
| `brandly-video-generation` | **HOW** things are generated | Prompting, camera moves, lighting presets, provider models, image/video/audio generation, download, assembly, editing |
| `brandly-init` (this skill) | **WHERE** things land | Layout contract, directory structure, artifact paths, phase order, gate approvals, project init, verification |

They are complementary. `brandly-video-generation` handles generation technique; `brandly-init` handles pipeline orchestration and artifact placement. Read `brandly-video-generation` for how to generate; read `brandly-init` for where each result must be placed and when to approve.

---

## Phase 1: Init (WHERE — project root + layout)

**Command**: `brandly init -n <name> -i "<idea>" [-s <style>] [--shots <N>] [--target-duration <S>] [--budget <C>]`

**Directory enforcement**: `brandly init` must always create the project in the **current working directory** (where the terminal is launched). Before running init, confirm `pwd` is the intended project root. After init, verify `AGENTS.md` and `.brandly/` exist in cwd. If brandly init created the project in an ancestor `.brandly` store instead of cwd, re-run from the correct directory. Never let init drift to a user root or ancestor store.

**Inputs**: product name (required), idea/brief (required), style (default: cinematic), shots (3-10, default 5), target duration, budget (default 500).

**Outputs** (WHERE):
- `.brandly/<id>/project.json`
- `AGENTS.md` at project root (cwd)

**Gate**: `brandly status <id>` → exit 0.

**Next**: `brandly approve <id> init`

---

## Phase 2: Trends

**Command**: `brandly run <id>` (agent runs trends phase)

**Artifact (WHERE)**: `docs/general/trends.md` (non-empty).

**Gate**: `brandly status <id>` → trends.md exists and non-empty.

**Next**: `brandly approve <id> trends`

---

## Phase 3: Concept

**Command**: `brandly run <id>` then verify artifact exists.

**Artifact (WHERE)**: `docs/general/concept.md` — write manually if agent runner doesn't produce it.

**Contents**: premise, visual style, tone, key beats, audio direction.

**Gate**: `brandly status <id>` → concept.md non-empty.

**Next**: `brandly approve <id> concept`

---

## Phase 4: Bible

**Command**: `brandly run <id>` then verify artifact exists.

**Artifact (WHERE)**: `docs/bible/production_bible.md` with **Section 4: Characters** (mandatory — feeds casting verbatim).

**Contents**: project overview, visual style, tone, characters (Section 4), environments, sound design, shot plan table.

**Gate**: `brandly approve <id> bible` — fails closed if no Characters section.

**Next**: `brandly approve <id> bible`

---

## Phase 5: Casting (WHERE — all artifacts must land)

**This is the most commonly mis-landed phase. Do not approve early.**

**Artifacts (WHERE)** — ALL must exist:

| Artifact | Where it lands |
|----------|---------------|
| Character cast image | `pre-production/<id>/character/char_<name>_cast-*.jpg` |
| Mecha cast image | `pre-production/<id>/mecha/<name>/char_<name>_cast-*.jpg` |
| Character sheet (gated) | `pre-production/<id>/mecha/sheets/char_<name>_sheet.jpg` (or `character/sheet/`) |
| Location sheet | `pre-production/<id>/location/loc_<name>_sheet-*.jpg` |
| Wardrobe variation | `pre-production/<id>/wardrobe/char_<name>_wardrobe-*.jpg` or `mecha/<name>/` |

**Gate**: Run `brandly gate <id> <path> -o json` on each sheet/image. Exit 0 = pass. Then `brandly approve <id> casting`.

**Anti-drift**: Casting is complete ONLY when character + location + wardrobe + sheets ALL exist AND gate-passed AND user-approved. Missing any one = incomplete.

**Example casting commands** (image generation technique deferred to brandly-video-generation):
```bash
# Generate character cast image (WHERE: pre-production/<id>/character/)
brandly image --project-id <id> -p "<prompt>" --output pre-production/<id>/character/char_<name>_cast-01.jpg

# Generate mecha cast image (WHERE: pre-production/<id>/mecha/<name>/)
brandly image --project-id <id> -p "<prompt>" --output pre-production/<id>/mecha/<name>/char_<name>_cast-01.jpg

# Generate character sheet (WHERE: pre-production/<id>/mecha/sheets/)
brandly image --project-id <id> -p "<prompt>" --output pre-production/<id>/mecha/sheets/char_<name>_sheet.jpg

# Gate the sheet (WHERE check)
brandly gate <id> pre-production/<id>/mecha/sheets/char_<name>_sheet.jpg -o json --lenient --threshold 50

# Generate location sheet (WHERE: pre-production/<id>/location/)
brandly image --project-id <id> -p "<prompt>" --output pre-production/<id>/location/loc_<name>_sheet-01.jpg

# Generate wardrobe variation (WHERE: pre-production/<id>/wardrobe/)
brandly image --project-id <id> -p "<prompt>" --output pre-production/<id>/wardrobe/char_<name>_wardrobe-standard.jpg
```

---

## Phase 6: Screenplay

**Command**: `brandly run <id>` then verify artifact exists.

**Artifact (WHERE)**: `docs/screenplay/screenplay.md` (non-empty).

**Gate**: `brandly approve <id> screenplay` — fails closed if empty.

**Next**: `brandly approve <id> screenplay`

---

## Phase 7: Script

**Command**: `brandly run <id>` then verify artifact exists.

**Artifact (WHERE)**: `.brandly/<id>/shots.json` (written).

**shots.json schema** (flat):
```json
[
  {
    "id": "shot-001",
    "title": "Awakening",
    "description": "<text>",
    "prompt": "<video generation prompt>",
    "duration": 7,
    "character": "unit-734",
    "reference_image": "pre-production/<id>/mecha/unit-734/char_unit-734_cast-01.jpg"
  }
]
```

**Gate**: `brandly status <id>` → shots.json exists.

**Next**: `brandly approve <id> script`

---

## Phase 8: Asset (WHERE — clips land in production/<id>/)

**Command**: `brandly produce <id> --shots <path/to/shots.json> --interval 60 --character <name>`

**Artifacts (WHERE)**: scene clip files in media store (`production/<id>/`).

**Gate**: `brandly gate <id> --all-scenes --json` — exit 0 = pass, 1 = warn, 2 = fail.

**Anti-drift**: On 503 `video_queue_full` / ReadTimeout → WAIT and re-run `brandly produce`. Do NOT patch shots. The run is resumable via `docs/tmp/produce_progress.txt`.

**Resume example**:
```bash
brandly produce <id> --shots .brandly/<id>/shots.json --interval 60 --character unit-734
```

**Next**: `brandly approve <id> asset`

---

## Phase 9: Audio

**Command**: `brandly run <id>` then verify artifact exists.

**Artifact (WHERE)**: `production/<id>/audio/music.mp3` (or videos present — audio optional).

**Gate**: `brandly status <id>` → music downloaded under audio/.

**Next**: `brandly approve <id> audio`

---

## Phase 10: Re-edit (assembly)

**Command**: `brandly stitch <clips...> --output videos/final.mp4`

**Artifact (WHERE)**: `videos/final.mp4` (music mixed in when track exists).

**Gate**: `brandly stitch` exit 0 = stitched; clip count matches scenes.json.

**Next**: `brandly approve <id> re_edit`

---

## Phase 11: Validate

**Command**: `brandly gate <id> --all-scenes --json`

**Gate**: exit 0 = pass (advance); 1/2 = re_edit, do not advance.

**Artifacts (WHERE)**: scene-gate verdicts in `docs/tmp/gate_*.md`.

**Next**: `brandly approve <id> validate`

---

## Phase 12: Publish (export)

**Command**: `brandly export-platforms <id> --platforms <tiktok,instagram,youtube>`

**Artifacts (WHERE)**: platform deliverables in `<project>/export/` for every target platform.

**Gate**: `brandly export-platforms` exit 0 = all deliverables written.

**Next**: `brandly approve <id> publish` → done.

---

## Common pitfalls & how to avoid them

| Pitfall | Prevention |
|---------|------------|
| Approving casting before sheets exist | Check all 5 artifact categories exist + gate-pass before `approve casting` |
| Wrong folder for mecha characters | Mecha cast → `mecha/<name>/`; mecha sheets → `mecha/sheets/`; non-mecha → `character/` |
| Missing Section 4: Characters in bible | Bible must have Section 4 before `approve bible` |
| Skipping gate before approve | Run `brandly gate` on every sheet/image before approving casting |
| Patching shots on 503 error | Wait and re-run `produce`; never hand-fix a shot |
| Dropping scratch files in media trees | Keep scratch/debug out of `pre-production/` and `production/` |
| Improvising docs paths | Use `.brandly/<id>/docs/<subdir>/` per layout contract |
| Running phases out of order | Follow the mandatory phase chain exactly |
| Init creating project in ancestor `.brandly` store instead of cwd | Confirm `pwd` before init; verify `AGENTS.md` + `.brandly/` in cwd after init |
| Using brandly-init for generation technique | Use brandly-video-generation for prompting, camera, lighting, provider routing |

---

## Example: full run on forgecorp-escape

```bash
# 1. Init (run in the intended working directory — WHERE check)
brandly init -n forgecorp-escape -i "Graphite pencil robot escape story" -s cinematic --shots 8 --target-duration 60 --budget 800

# 2-7. Run + approve each phase (WHERE artifacts land per phase chain)
brandly run forgecorp-escape
brandly approve forgecorp-escape trends
brandly run forgecorp-escape
brandly approve forgecorp-escape concept
brandly run forgecorp-escape
brandly approve forgecorp-escape bible
# ... casting, screenplay, script ...

# 8. Asset (WHERE: clips land in production/<id>/)
brandly produce forgecorp-escape --shots .brandly/forgecorp-escape/shots.json --interval 60 --character unit-734

# 9-12. Audio, re_edit, validate, publish
brandly stitch <clips> --output videos/final.mp4
brandly export-platforms forgecorp-escape --platforms tiktok,instagram
```

---

## Verification checklist (run before declaring any phase complete)

- [ ] `brandly plan <id> --json` read for current phase
- [ ] All required artifacts exist at correct paths (WHERE check)
- [ ] `brandly gate` passed on all gated artifacts
- [ ] `brandly approve <id> <phase>` executed
- [ ] No scratch/debug files in `pre-production/` or `production/`
- [ ] Phase chain order respected (no skipping, no reordering)
- [ ] `AGENTS.md` and `.brandly/` exist in cwd after init
