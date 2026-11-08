# Subgoals — v0.15.4 Per-Take Prompt Files (`prompts/` prompt pack)

**Status:** Implemented — all §8 criteria met, gates green, PR pending
**Version:** v0.15.4 (minor: new capability)
**Base:** brandly-cli 0.14.9
**Roadmap slot:** v0.15.4 — scheduled after v0.15.3 (Casting Validation &
Wardrobe Continuity); see `GOAL-STUDIO-ROADMAP.md`
**Owner:** TBD
**Design authority:** this file (freeze before Phase 3 code)

---

## Overview

Today a shot's generation prompt lives **only** inside the shot list
(`.brandly/<id>/shots.json` / the timeline editor). Writing, reviewing and
rewriting a single take's prompt therefore means hand-editing a large JSON
document — painful for humans and token-expensive for agents.

This subgoal introduces a **prompt pack**: one Markdown file per take, laid
out as one folder per scene.

```
Screenplay: 5 scenes, 20 takes
→ .brandly/<project>/prompts/
    Scene 1/
        Scene 1.1.md        ← Take 1 of Scene 1
        Scene 1.2.md
        Scene 1.3.md
        Scene 1.4.md
    Scene 2/
        Scene 2.1.md
        ...
    Scene 5/
        Scene 5.4.md
```

`Scene 1` is the **scene** (folder). `Scene 1.1` is **Take 1 of Scene 1**
(file). The folder exists so takes are addressable without a flat namespace
and so a scene can later own scene-level direction (see §12 — deferred).

The feature is a *file projection* of the shot list plus an explicit sync
contract. It is **not** a second pipeline: generation still runs from
`shots.json`, and the pack is fail-closed when it drifts (§5).

---

## 1. Problem statement

| Pain | Evidence in the current code |
|---|---|
| A prompt has no standalone address | `Shot.prompt` is only reachable through `shots.json` (`shot_runner.py` reads `shot.prompt` at flatten time) |
| Editing one take means editing a whole plan | `shots.json` holds acts, references, durations, beats, folders and prompts in one document |
| Agents burn tokens rewriting structure to change one sentence | an agent must read + rewrite the full shot list to touch a prompt |
| No reviewable diff per take | one JSON blob produces one noisy diff |
| No drift detection | nothing verifies that an edited prompt is the one generation will use |

## 2. Goals

1. A take's prompt can be created, read, edited and reviewed as a single
   `.md` file at a stable, human-readable path.
2. The mapping file ↔ shot is deterministic and derived from
   `docs/general/scenes.json` (scene order), not from fragile string matching.
3. Drift between the pack and `shots.json` is **detected and surfaced**, never
   silently ignored.
4. If the pack exists, `brandly produce` refuses to generate from a stale or
   conflicting pack.
5. Legacy projects (no `prompts/` folder) behave exactly as today.

## 3. Non-goals (v1)

- No scene-level prompt inheritance file (deferred, §12).
- No web/Paper UI for editing takes (no design artifact exists → out of scope).
- No per-take generation **parameters** (duration/refs/model/beat). Only the
  prompt **text** moves. Parameters stay in `shots.json`.
- No automatic renumbering when the shot list is restructured.
- No MCP tool (§12) — the files are directly editable; the CLI covers the
  sync contract.

---

## 4. Directory + naming contract

### 4.1 Location

```
.brandly/<project>/prompts/
```

Rationale: prompts are consumed at **generation time** next to `shots.json`,
not a research document under `docs/`. `layout.py` is the single source of
truth for `.brandly/` paths (AGENTS.md §1, `layout.py` docstring), so the
path must be added there and nowhere else.

> **Anti-drift note:** `prompts/` is **never created eagerly**. `layout`
> creates its media/doc tree on project init; creating `prompts/`
> automatically would silently activate the fail-closed contract (§5) for
> every existing project. It is created only by `brandly takes export`.

### 4.2 Naming

| Artifact | Pattern | Example |
|---|---|---|
| Scene folder | `Scene {N}` | `Scene 1`, `Scene 5`, `Scene 12` |
| Take file | `Scene {N}.{T}.md` | `Scene 1.1.md`, `Scene 3.2.md` |

Rules (all enforced, all tested):

- `N` = **1-based ordinal of the scene in `docs/general/scenes.json`**, i.e.
  the numeric part of the manifest id `S01`, `S02`, … — *not* the raw `scene`
  key. Two acts may both declare `"scene": 1` (issue #312); the manifest
  already disambiguates them as `S01`/`S02`, so the folder ordinal is
  project-unique and stable.
- `T` = the take index already used by the clip name — for structured plans
  the 1-based position inside the scene's `shots[]`; for flat plans
  `shot["shot"]` (default: position in the list), mirroring
  `build_scenes`/`clip_filename`. It must be unique within the scene: a
  duplicate `(N, T)` is `invalid` (it would make two takes collide on one
  file and one clip).
- No zero padding: `Scene 1`, not `Scene 01`; `Scene 1.1`, not `Scene 1.01`.
- ASCII only, exactly one space between `Scene` and the number, `.md`
  extension required.
- Sorting is numeric by `(N, T)`, never lexicographic (`Scene 10` must follow
  `Scene 9`).
- Only `Scene {N}` directories and `prompt-manifest.json` are legal at the
  pack root. Any other entry is `invalid` (hard error, §5.3) — never silently
  skipped, never deleted.
- The number of takes per scene is **not** required to be equal (20 takes
  across 5 scenes may be 4/6/3/4/3). The 4/4/4/4/4 tree above is only an
  illustration.

### 4.3 File format

- The file body **is** the prompt, verbatim. No YAML frontmatter, no added
  heading, no wrapping fence — a heading would become part of the prompt.
- UTF-8. Normalization for hashing/compare is exactly
  `text.replace("\r\n", "\n").rstrip("\n")`; a single trailing newline is
  written on export and stripped on apply.
- An **empty** (or whitespace-only) file is `invalid`. It cannot mean "clear
  the prompt" — clearing is `takes apply --clear <scene.take>`.
- Markdown inside the prompt is preserved byte-for-byte (including `#`,
  lists, `[SECTION]` tags).

---

## 5. Source of truth and sync model

**Rule:** `shots.json` is the structural source of truth (ids, refs,
durations, beats, folders). The **pack is the prompt source of truth whenever
it exists**. There is exactly one prompt per take; divergence is an error
state, never a merge.

### 5.1 Deterministic take walk

`take_prompts.iter_takes(data)` walks the shot list in the *same order* that
`scenes.build_scenes()` uses to build the manifest:

- flat list → enumerate positions; `scene` = `shot["scene"]` (default 1),
  `take` = `shot["shot"]` (default position) — the same pair
  `clip_filename(scene, take)` encodes;
- structured `{"acts": …}` → acts in declaration order, shots in array order;
  scene ordinal assigned in first-appearance order (matching `S01…`), take =
  1-based position in that scene's `shots[]`.

It yields `(scene_ordinal, take_index, shot_ref)`. Because it mirrors
`build_scenes`, the pack map is deterministic without matching prompt text or
relying on possibly-duplicated shot ids (issue #50). A `(scene, take)` pair
seen twice is a structural error and is reported as `invalid`, never silently
written twice.

### 5.2 Manifest (machine-written, not hand-editable)

`prompts/prompt-manifest.json`:

```json
{
  "version": 1,
  "project_id": "…",
  "generated_at": "2026-11-08T12:00:00Z",
  "takes": {
    "1.1": {
      "scene": 1,
      "take": 1,
      "scene_id": "S01",
      "clip": "Scene-01-Shot-1-1.mp4",
      "file": "Scene 1/Scene 1.1.md",
      "synced_file_sha256": "…",
      "synced_prompt_sha256": "…"
    }
  }
}
```

`version` bumps on any incompatible change; an unreadable/unknown manifest
version is `invalid` (fail closed), never "assume in sync".

### 5.3 State matrix (single definition, used by CLI + produce)

| State | Condition | `takes status` exit | `brandly produce` |
|---|---|---|---|
| `in-sync` | file hash = synced file hash **and** shots prompt hash = synced prompt hash | 0 | allowed |
| `edited` | only the file changed | 1 | **refuse**: run `takes apply` |
| `drifted` | only `shots.json` changed | 1 | **refuse**: run `takes export` |
| `conflict` | both changed | 2 | **refuse**: resolve manually |
| `missing` | shot **has** a prompt, take file absent | 1 | **refuse**: `takes export` |
| `unscripted` | shot has **no** prompt and no file | 0 | allowed (nothing to lose) |
| `orphan` | file has no matching shot | 2 | **refuse**: `takes export --prune` or delete the file |
| `invalid` | bad path/name/empty file/manifest | 2 | **refuse** |

Exit codes mirror the existing gate convention (`pass`→0, `warn`→1,
`fail`→2, see `scenes.py`).

**No fabrication:** a shot whose prompt is empty in `shots.json` is
`unscripted`, never exported as a placeholder file and never reported as
`missing`.

---

## 6. CLI surface

### 6.1 Why `brandly takes`, not `brandly prompt`

`brandly prompt` is already a **command** that builds a prompt from
`--subject/--action/--environment` (`cmd/generation.py:2095`). It cannot
become a Click group without breaking that contract. The new group is
therefore `brandly takes`, the domain word already used by the pipeline
("which take are we generating?").

```
brandly takes list   <project_id> [--scene N] [--json]
brandly takes export <project_id> [--missing-only] [--force] [--prune] [--dry-run]
brandly takes apply  <project_id> [--scene N] [--take N] [--clear 1.2] [--force] [--dry-run]
brandly takes status <project_id> [--json]
```

| Command | Behaviour |
|---|---|
| `list` | Take inventory: `scene.take`, state, path, clip, first line of the prompt. Human table by default, `--json` for agents. |
| `status` | State matrix summary + per-take offenders; exit 0/1/2 per §5.3. Never writes. |
| `export` | Create/refresh take files from `shots.json`. Default **never overwrites an `edited` file**; `--force` overwrites (prints a warning and the affected paths); `--missing-only` writes only `missing`; `--prune` deletes `orphan` files (requires `--force` too — no destructive default); `--dry-run` prints the plan only. |
| `apply` | Write take file bodies back into `shots.json` (atomic `write_json`, preserving key order), update the manifest hashes, then report the new state. `--force` makes the file win a `conflict`. `--clear 1.2` empties that shot's prompt (the explicit way to remove direction). `--dry-run` prints the diff summary only. |

`export`/`apply` refuse to run on `invalid` or `orphan` unless the flag that
resolves it is passed. Every write is atomic (`io.write_json` style temp +
`replace`), matching existing repo practice.

### 6.2 Agent surface

`agent_surface.py` layout documentation gains one line:

```
- `.brandly/<id>/prompts/` — per-take prompt files (`Scene 1/Scene 1.1.md`);
  created by `brandly takes export`, authoritative for prompt text when present.
```

No new MCP tool (§12).

---

## 7. Generation integration (fail-closed)

In `produce()` (structured/flat runner entry):

1. If `.brandly/<id>/prompts/` does not exist → today's behaviour, zero
   change, zero warning.
2. If it exists → run the §5.3 status check **before** any provider call.
   - `in-sync` / `unscripted` → proceed; generation uses `shots.json` (which
     `apply` has just made equal to the pack).
   - anything else → print the offending takes + the exact remediation
     command, exit 2. **No request is sent.**
3. `--ignore-prompt-pack` is the documented escape hatch for recovery: it
   prints a loud warning (`⚠ generating from shots.json, prompt pack ignored`)
   so bypassing the contract is visible in the run transcript.

No second prompt-resolution path is introduced: `produce` never reads the
`.md` files itself. This keeps one code path and one source of truth per run.

---

## 8. Subgoals

### 8.1 Layout + take model
**Status:** Implemented — evidence below

New module `src/brandly_cli/take_prompts.py` + `layout.prompts_dir` /
`PROMPTS_DIRNAME`. Pure functions, no Click, no network.

**Acceptance criteria:**
- [x] `layout.PROMPTS_DIRNAME == "prompts"` and `layout.prompts_dir(root, project_id)` returns `.brandly/<id>/prompts`; the path is **not** in the eager-creation list.
- [x] `parse_take_path(path)` → `(scene, take)` for canonical names; returns `None` for non-canonical entries.
- [x] `format_take_path(scene, take)` → `Scene {N}/Scene {N}.{T}.md` (round-trip property test over 1..99 × 1..99).
- [x] `iter_takes(data)` yields `(scene, take, shot_ref)` in `build_scenes` order for flat and structured lists; a 5-scene/20-take fixture yields exactly 20 takes with distinct keys.
- [x] Numeric sort: `Scene 10` sorts after `Scene 9`; `Scene 1.10` after `Scene 1.9`.
- [x] `status(project_id)` returns the §5.3 matrix per take plus a rollup (`ok|edited|drifted|conflict|missing|unscripted|orphan|invalid`).
- [x] Empty file, wrong extension, `Scene 01`, `scene-1`, nested extra dirs and case-variant duplicates all classify as `invalid` with the offending path in the error.
- [x] A duplicated `(scene, take)` pair in the shot list classifies as `invalid`; `export` refuses and writes nothing.
- [x] Manifest round-trips; unknown `version` → `invalid` (no silent in-sync).
- [x] No function mutates `shots.json` except `apply()`; no function creates `prompts/` except `export()`.

**Test plan (RED first):** `tests/test_take_prompts.py` — fixtures for flat
and structured plans, the 5/20 layout, numeric ordering, every §5.3 state,
round-trip parse/format, `layout` contract.

### 8.2 CLI group `brandly takes`
**Status:** Implemented — evidence below

**Acceptance criteria:**
- [x] `takes` is registered on the root CLI; `brandly --help` lists it; `brandly takes --help` lists `list|export|apply|status`.
- [x] `takes export` on a project with 20 shots creates the exact tree in §4.2 (`Scene 1/Scene 1.1.md` … `Scene 5/Scene 5.4.md`) plus `prompt-manifest.json`.
- [x] `export` is idempotent: a second run writes nothing and reports 20 `in-sync`.
- [x] `export` never overwrites an `edited` file without `--force`; with `--force` it prints every overwritten path.
- [x] `export --prune` without `--force` is refused with a clear message.
- [x] `apply` after editing one file updates only that shot's prompt in `shots.json` (byte-level diff shows one changed string) and flips state to `in-sync`.
- [x] `apply` on `conflict` is refused without `--force`; with `--force` the file wins and the manifest records the new hashes.
- [x] `apply --clear 1.2` sets that prompt to `""`; state becomes `unscripted`, and the file is removed (no orphan left behind) — the only deletion path in the feature.
- [x] `status` exits 0/1/2 exactly per §5.3; `--json` is stable and machine-readable.
- [x] Every command validates `project_id` via `is_valid_project_id` and handles spaces in scene paths without shell interpolation bugs.
- [x] `--dry-run` on both directions performs zero writes (mtime proof).

**Test plan (RED first):** `tests/test_take_prompts_cli.py` using
`click.testing.CliRunner` + `tmp_path`; assert exit codes, filesystem state
and `shots.json` diffs. Add a registration test to
`tests/test_cli_entrypoints.py`.

### 8.3 Produce fail-closed gate
**Status:** Implemented — evidence below

**Acceptance criteria:**
- [x] Project **without** `prompts/`: `produce` behaviour is byte-identical to 0.14.9 (existing `tests/test_shot_runner*.py` stay green, no new output lines).
- [x] Project with an `edited`/`drifted`/`conflict`/`missing`/`orphan`/`invalid` pack: `produce` exits 2 **before** any backend call, prints the offending takes and the remediation command.
- [x] Project with an `in-sync` pack: `produce` proceeds and the prompt used for each shot equals the take file body (assert against the mocked backend's received prompt).
- [x] `produce --dry-run` runs the check and reports the state without contacting a provider.
- [x] `--ignore-prompt-pack` proceeds with a visible warning; the warning is present in the run transcript.
- [x] `unscripted` shots do not block a run and produce no take file.

**Test plan (RED first):** `tests/test_take_prompts_produce.py` with the
existing fake/mocked video backend; assert "0 calls made" on refusal.

### 8.4 Docs + contract surfaces
**Status:** Implemented — evidence below

**Acceptance criteria:**
- [x] `layout.py` docstring tree documents `prompts/` and the not-eager-created rule.
- [x] `agent_surface.py` layout block mentions `prompts/` (one line).
- [x] `skills/brandly-video-generation/SKILL.md` gains a "Per-take prompt pack" section: tree, naming, `export → edit → apply → produce` loop, fail-closed behaviour.
- [x] `skills/brandly-init/SKILL.md` references the folder without claiming it is auto-created.
- [x] `CHANGELOG.md` `[Unreleased]` → "Added: per-take prompt files (`prompts/`, `brandly takes …`)".
- [x] `dev-notes/PROGRESS.md` records the round and copies the §12 deferrals into its DEFERRED ledger.

**Test plan:** `tests/test_agents_md_sync.py`-style contract assertions if the
skill docs are asserted; otherwise a source-contract test in
`tests/test_take_prompts.py` reading the skill file.

### 8.5 Gates
**Status:** Implemented — evidence below

- [x] `python -m pytest tests/test_take_prompts*.py -v`
- [x] `python -m pytest tests/ -q`
- [x] `ruff check src/ tests/` — zero warnings
- [x] `python -m pytest tests/test_web_*.py -v` (unchanged; no web edits expected)
- [x] `brandly --help` / `brandly takes --help` render correctly (CliRunner)

**Evidence (this round):**

| Check | Result |
|---|---|
| `pytest tests/test_take_prompts.py tests/test_take_prompts_cli.py tests/test_take_prompts_produce.py tests/test_cli_entrypoints.py -q` | `99 passed` |
| `pytest tests/ -q` | `1796 passed, 1 skipped, 3 xfailed` |
| `pytest tests/test_web_*.py -q` | `151 passed, 1 skipped, 3 xfailed` |
| `ruff check src/ tests/` | `All checks passed!` |
| `brandly takes --help` | lists `apply / export / list / status` |

RED evidence: the three test files were each run against the unfiltered
implementation first — `test_take_prompts_cli.py` 21 failed, the
`--scene/--take` cases 4 failed (model) / 2 failed (CLI), and
`test_take_prompts_produce.py` 7 failed — before GREEN.

---

## 9. Implementation order (TDD, RED → GREEN)

1. **RED** `tests/test_take_prompts.py`: names, parse/format, ordering, 5/20 walk, state matrix.
2. **GREEN** `layout.prompts_dir` + `take_prompts.py` pure model.
3. **RED** `tests/test_take_prompts_cli.py`: export tree, idempotence, no-overwrite, apply diff.
4. **GREEN** `cmd/takes.py`, register in the CLI.
5. **RED** `tests/test_take_prompts_produce.py`: fail-closed, no backend call, in-sync prompt equality.
6. **GREEN** `produce` pre-flight in `cmd/production.py` (single guard function in `take_prompts`, called once).
7. **RED/GREEN** `--ignore-prompt-pack` warning + `--dry-run`.
8. Docs (§8.4), full gates (§8.5), CHANGELOG, PROGRESS.
9. PR → review → squash-merge (`gh pr merge --squash --delete-branch`).

**Red evidence is mandatory:** each test file must be run and observed
failing for the documented reason before the implementation lands
(CONVENTIONS.md §2).

---

## 10. Dependencies

- `docs/general/scenes.json` (issue #299) — scene ordinals and `shots[]` are
  the mapping authority. Legacy `docs/plan/scenes.json` is accepted through
  `scenes.load_scenes()`.
- `shot_runner.flatten_shots` / `build_scenes` ordering (must not diverge).
- `io.write_json` atomic write helper.
- `is_valid_project_id` validation.
- No new third-party dependency (no PyYAML, no frontmatter parser).

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Prompt divergence (pack vs `shots.json`) | §5.3 state matrix + `produce` fail-closed; hashes in the manifest |
| Shot ids collide across acts (issue #50) | Mapping uses scene **ordinal + position**, never ids |
| Scene renumbering after plan edits | Orphans are reported, never auto-deleted/renamed; `export --prune` is explicit and double-flagged |
| Spaces in paths break shell flows | All addressing is `--scene N --take N`; paths only in `--json` output; tests cover quoting |
| Case-insensitive filesystems (macOS/Windows) | Only canonical names are written; case-variant entries classify as `invalid` |
| Accidental loss of hand-written prompts | Default export never overwrites `edited`; `--force` lists every path; `--dry-run` first |
| Silent no-op on legacy projects | Presence check: no `prompts/` ⇒ zero behaviour change |
| Pack activating on every project | `prompts/` is never created eagerly; only `takes export` creates it |
| Agents mistaking "take" for a redo clip | Terminology section (§13) + docs state: **take = prompt slot (shot position)**, a redo regenerates the clip but does not create a new `.md` |

---

## 12. Deferrals (record in `PROGRESS.md` at implementation time)

| ID | Item | Why deferred |
|---|---|---|
| P1 | Scene-level direction file `Scene N/Scene N.md` inherited by every take | Not requested; adds inheritance/precedence semantics that need their own design |
| P2 | MCP tool `take_prompts` | Files are directly editable and `brandly takes` covers sync; revisit only if the agent surface needs it |
| P3 | Web/Paper take editor | No frozen Paper artboard → out of scope per AGENTS.md §4 |
| P4 | Per-take parameters (duration/refs/model/beat) | v1 moves prompt **text** only; parameters stay in `shots.json` |
| P5 | Automatic renumber/remap after structural edits | Destructive; orphans are surfaced instead |
| P6 | YAML frontmatter metadata inside take files | No YAML dependency convention; JSON manifest is machine-written |

---

## 13. Terminology (must appear verbatim in the skill doc)

- **Take** — one prompt slot = one shot position inside a scene
  (`scenes.json → scenes[i].shots[t]`). File `Scene N.T.md`.
- **Redo** — regenerating the clip of an existing take (`produce --only`).
  It replaces the clip; it does **not** create `Scene N.T+1.md`.
- **Prompt pack** — the `prompts/` tree + manifest for one project.

---

## 14. Definition of done

1. Every §8 acceptance criterion is ticked with evidence (command + result).
2. All gates in §8.5 green, zero `ruff` warnings, no skipped tests.
3. `prompts/` tree for the 5-scene/20-take fixture matches §4.2 exactly.
4. `produce` refuses a stale pack with exit 2 and zero provider calls.
5. Legacy project fixture (no `prompts/`) is byte-identical in behaviour.
6. PR reviewed and squash-merged; branch deleted; PROGRESS.md updated;
   CHANGELOG updated.

---

## 15. Open questions (defaults are binding until changed before code)

| # | Question | Default |
|---|---|---|
| Q1 | Pack root: `.brandly/<id>/prompts/` vs `.brandly/<id>/docs/prompts/`? | `prompts/` (per the requested structure; generation-time artifact, sibling of `shots.json`) |
| Q2 | Overwrite policy for `export` on an `edited` file | Refuse; `--force` required |
| Q3 | Should `apply` be allowed to create a missing take file? | No — `apply` only reads existing files; `export` creates |
| Q4 | Should `produce` hard-fail or warn on drift? | Hard-fail (exit 2) with `--ignore-prompt-pack` escape hatch |
