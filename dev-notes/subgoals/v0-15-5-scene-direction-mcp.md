# Subgoals — v0.15.5 Scene Direction Files + MCP `take_prompts`

**Status:** Frozen design — implement after this spec is ratified  
**Version:** v0.15.5 (minor: two new capabilities)  
**Base:** brandly-cli 0.15.4  
**Closes deferrals from Round 37 (v0.15.4):** P1 (scene direction files), P2 (MCP `take_prompts`)  
**Remains deferred (explicit non-goals):** P3 web/Paper editor (no artboard, AGENTS.md §4), P5 auto-renumbering (destructive), P6 YAML frontmatter (no YAML convention). P4 (per-take params) is a v1 non-goal — only prompt text moves.

**Design authority:** this file (freeze before Phase 3 code). No code without RED→GREEN tests.

---

## P1 — Scene-level direction files

### Problem
The per-take pack (§4 of v0-15-4) holds one prompt file per take. A scene has no place to declare direction that applies to every take in it (character, camera, lighting, mood). Agents must repeat that direction in every take file, and editing it means touching N files.

### Design
**File:** `.brandly/<project>/prompts/Scene N/Scene N.md` — one optional direction file per scene folder, sibling of the take files.

**Opt-in / never created eagerly:** like the pack itself, `Scene N.md` is authored directly (by hand or agent). Pack tools never write it.

**Precedence (inheritance), frozen:**
- Scene direction = **base direction** for the scene (prepended).
- Take file = **per-shot override** (the shot's own prompt verbatim).
- At generation time (`flatten_shots`), effective prompt for take `Scene N.T` =
  `scene_direction_text + "\n\n" + take_prompt_text` when a scene direction file exists,
  else just `take_prompt_text`.
- The pack's fail-closed contract is unchanged: `status`/`export`/`apply` treat
  `Scene N.md` as scene metadata, NOT as a take file — it is never an orphan,
  never invalid, never part of the take state matrix.

### Pack-tool changes (`take_prompts.py`)
- `_scan_files`: exempt `Scene N/Scene N.md` (direction file) from the invalid list and from orphan detection.
- Add `load_scene_direction(pack: Path, scene: int) -> str | None` — reads `Scene N/Scene N.md` if present, else `None`.
- `status`: direction files do not appear as takes; they are not scanned into the matrix.
- `export`/`apply`: unchanged behavior for takes; direction files are read-only.

### Generation integration (`shot_runner.flatten_shots`)
- New optional keyword `scene_direction: dict[int, str] | None` — maps scene ordinal → direction text.
- In `flatten_shots`, for each shot in scene `S`, prepend `scene_direction.get(S)` (followed by `\n\n`) to `shot.prompt` when present.
- `production.py produce`: load scene directions for every scene that has a `Scene N.md` file, pass to `flatten_shots`. Direction is read from disk at generate time — zero behavior change for projects without scene direction files (the opt-in default).

### Tests (RED→GREEN)
- `tests/test_scene_direction.py`: reader returns None for missing file, text for present file; `flatten_shots` prepends direction for scene shots, none for scenes without a file; pack scan exempts `Scene N.md` (not invalid, not orphan); `status` matrix unaffected by a direction file.
- Full suite green; ruff clean; mypy clean.

---

## P2 — MCP `take_prompts` tool

### Problem
The MCP server exposes `brandly` pipeline tools via `agent_surface.tool_manifest()`, but there is no tool to read/apply the per-take prompt pack from an external agent. Agents must shell out to `brandly takes` manually.

### Design
Register four CLI-backed MCP tools (no parallel implementation — each maps to the existing `brandly takes` subcommand):

| Tool | CLI mapping | Read-only |
|---|---|---|
| `take_prompts_status` | `brandly takes status <id> [--json]` | yes |
| `take_prompts_list` | `brandly takes list <id> [--scene N] [--json]` | yes |
| `take_prompts_export` | `brandly takes export <id> [--missing-only] [--force] [--prune] [--dry-run]` | no (writes files) |
| `take_prompts_apply` | `brandly takes apply <id> [--scene N] [--take N] [--clear S.T] [--force] [--dry-run]` | no (writes shots.json) |

Each follows the existing `CLI_TOOLS` + `_build_*` + `TOOL_ANNOTATIONS` pattern in `agent_surface.py`. `status`/`list` return parsed JSON (`--json`); `export`/`apply` return exit code + stdout.

### `agent_surface.py` changes
- Add 4 entries to `CLI_TOOLS` with builders `_build_takes_status`, `_build_takes_list`, `_build_takes_export`, `_build_takes_apply`.
- Add `TOOL_ANNOTATIONS` entries (read-only for status/list).
- Add to `TOOL_DOMAINS` under `"project"` (or a new `"takes"` domain).
- `render_agents_md` auto-lists them (iterates manifest) — no manual edit.

### Tests (RED→GREEN)
- `tests/test_agent_surface_takes.py`: manifest contains the 4 tools; `build_command` maps each to correct argv; `dispatch` (injected runner) returns envelopes with ok/exit_code/command.
- Full suite green; ruff clean; mypy clean.

---

## Definition of done (v0.15.5)
1. P1 spec implemented: scene direction files readable, exempt from pack scans, prepended at generation via `flatten_shots`, wired in `produce`.
2. P2 spec implemented: 4 MCP tools registered, manifest + annotations + domains updated.
3. RED→GREEN tests for both; full suite green, 0 ruff warnings, mypy clean.
4. `dev-notes/PROGRESS.md`: Round 39 entry (v0.15.5) with P1/P2 closed, P3/P5/P6 still deferred.
5. `CHANGELOG.md`: `[0.15.5]` section on release; tag `v0.15.5`; GitHub release; PyPI 0.15.5; three-way verification.
6. PR reviewed, squash-merged, branch deleted.
