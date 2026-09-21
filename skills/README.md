# Brandly Skills

Bundled [Agent Skills](https://agentskills.io) that teach AI agents how to drive
the `brandly` CLI. Every skill ships inside the `brandly-cli` package and must
stay aligned with the CLI's actual surface — `tests/test_skills.py` enforces the
frontmatter spec and that every referenced doc exists.

**The pipeline this skill set drives:**
`brandly init` → `brandly prompt` → `brandly reference` (plates) →
`brandly produce --shots shots.json` (one shot at a time, 1 req/min,
resumable) → `brandly gate` → `brandly stitch` → `brandly export`.

## Skill map — which CLI surface each skill drives

| Skill | Drives | Notes |
|-------|--------|-------|
| `brandly-video-generation` | `brandly reference` · `brandly image` · `brandly video` · `brandly produce` · `brandly job-resume` | **Start here** — routing hub, plan-as-source-of-truth, auto-refs, gates |
| `brandly-storyboard` | `brandly produce` (+ `docs/storyboard/` shot lists) | Shot lists: flat array or structured `{"acts": ...}` schema |
| `brandly-film-director` | prompt writing → `brandly video` / `brandly produce` | Creative-direction layer; execution owned by video-generation |
| `brandly-continuous-action-film` | prompt writing → `brandly produce` | 61 action categories; category grammar, brandly execution |
| `brandly-camera` | prompt writing (camera grammar for any generation) | Reference-only; no commands of its own |
| `brandly-consistency` | `brandly video` / `brandly produce` (anchors + auto-refs) | GOLD/SILVER/PLASTIC lock system |
| `brandly-production-bible` | `docs/bible/` + every generation command | Campaign source of truth |
| `brandly-concept-art` | `brandly reference` / `brandly image` concepts | Pre-production visual development |
| `brandly-character-sheet` | `brandly reference --subject-type character` (+ `brandly image`) | Matte-grey multi-view plates, `char_*` |
| `brandly-location-sheet` | `brandly reference --subject-type location` | `loc_*` plates |
| `brandly-object-sheet` | `brandly reference --subject-type object` | `prop_*` plates |
| `brandly-vehicle-sheet` | `brandly reference --subject-type vehicle` | `veh_*` plates |
| `brandly-mecha-sheet` | `brandly reference --subject-type mecha` | `mech_*` plates |
| `brandly-animal-sheet` | `brandly reference --subject-type animal` | `ani_*` plates |
| `brandly-plant-sheet` | `brandly reference --subject-type plant` | `plant_*` plates |
| `brandly-3d-spatial` | Blender playblast → `brandly video --first-frame/--last-frame` | `3d-spatial/{cameras,keyframes,depthmaps}` |
| `brandly-title-sequence` | design specs → `brandly image` / `brandly produce` | Title-card design; Photoshop/AE specs stay manual |
| `brandly-film-critic-scorer` | review of scripts/shot lists (complements `brandly gate`) | Automated artifact checks belong to `brandly gate` |
| `brandly-film-collaborator` | team workflow over `.brandly/<project>/` | Git roles; brandly tree mapping inside |

## Rules for new skills

1. Folder name == frontmatter `name` (lowercase `a-z0-9-`), `description` is a
   single activation sentence listing trigger phrases.
2. Long material goes to `references/`; only link files that exist (CI checks).
3. Every skill must state which `brandly` command(s) it drives — a skill that
   cannot be executed through the CLI does not belong in this package.
4. Never teach a workflow that bypasses the production plan or the
   1 request/minute Agnes rate limit.
