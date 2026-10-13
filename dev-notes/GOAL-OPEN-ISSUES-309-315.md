# GOAL — Open Issues #309–#315 (pulse-earbuds run findings, v0.14.0)

> **Base:** `main` @ `aff4022` (v0.14.0) · **Branch:** `fix/open-issues-309-315`
> **Scope:** all 7 open GitHub issues #309–#315 (issues #316+ do not exist yet).
> **Process:** RED → GREEN per issue; full suite + ruff green at the end.

## Issues and rulings

### #309 (bug) — reference gate fails its own multi-view grid output
**Root cause:** the reference-sheet prompts ask for "subtle thin grey divider
lines" between panels (by design). The vision judge may list those divider
lines in `issues[]`; `GateResult.finalize()` maps ANY issue to FAIL — even
when the model's own verdict is `pass` and the score is 90. The matte check
itself (`matte_background: false`) is only a warning; the killer is the
free-text `issues` list.

**Ruling (option 3 + prompt guidance):**
1. `_vision_user_prompt` (sheet kind, `expect_matt_background=True`) tells the
   model that multi-view reference boards are split by thin divider lines BY
   DESIGN — divider/seam/panel-split lines are not issues.
2. `_apply_ai_verdict` demotes divider/seam-only issues to WARNINGS when
   `expect_matt_background` is set (deterministic whitelist — the gate never
   FAILs a sheet for its own by-design grid).
**Promotion follows the gate fix** — no change needed in the promotion path
(#275 ordering already correct: gate → human gate → metadata).

### #310 (bug) — produce retry flags silently ignored by the plan-based runner
**Root cause:** `produce` routing (`cmd/production.py`) selects the
progress-file runner only for structured lists or explicit runner flags.
A flat list with `--retries/--backoff-factor/--continue-on-fail/--park-after`
falls into the plan-based loop, which fail-stops on first failure.

**Ruling (honor the flags — route them):** any non-default retry-family flag
(`--retries N>0`, `--backoff-factor F!=1.0`, `--continue-on-fail`,
`--park-after P!=default`) routes the run through the progress-file runner,
which implements all four. The help text for those flags already describes
runner semantics; the routing just makes it true.

### #311 (bug) — `Setting: | Time | Visual | Audio |` leaks into every shot prompt
**Root cause:** the script phase derives `environment` from the FIRST
non-heading line of `concept.md` (`concept_lines`). A markdown table header
row (`| Time | Visual | Audio |`) is not a heading and not skipped, so it is
embedded verbatim as the environment line of every shot prompt.

**Ruling:** concept-line extraction skips markdown table rows (lines starting
with `|`) and table separator rows, taking the first real prose line instead.
No schema change.

### #312 (enhancement) — flat shot list collapses a 3-act screenplay into one scene
**Root cause:** the script phase hardcodes `"scene": 1` for every shot;
`assemble` applies between-scene transitions only between distinct scenes.

**Ruling (screenplay-derived scene numbers):** the script phase reads
`docs/screenplay/screenplay.md` (optional input), extracts act structure
(markdown headings `ACT …` / `Act …` / `SCENE …` / `Scene …`, or
`INT.`/`EXT.` screenplay headings), and assigns scene numbers to shots
contiguously — shots distribute across the detected acts in order (remainder
spread to earlier acts). When no screenplay exists or no act structure is
found, behavior is unchanged (single scene 1) — backward compatible.

### #313 (enhancement) — auto-ref cap drops every character identity sheet
**Root cause:** `_ref_priority` ranks Scene-* storyboard keyframes (0) ABOVE
`char_/wardrobe_` identity plates (1). With many keyframes, every identity
anchor is dropped at the 5-image cap.

**Ruling (identity anchors first):** new priority order —
`char_/wardrobe_` identity plates (0) → `Scene-*` keyframes (1) →
`loc_/prop_` plates (2) → unknown (9). Junk still ranks last (#295
contract preserved).

### #314 (docs) — docs/skills show legacy `.brandly/<id>/images/` layout
**Root cause:** v2 media layout writes to `pre-production/<id>/<category>/`
(#117), but 10 skill files + README(s) still document
`.brandly/<project_id>/images/<category>/`.

**Ruling:** update every shipped skill + skills/README.md to the v2 layout;
add a contract test that greps the skills tree for the legacy path and fails
on any occurrence (docs↔layout sync pinned).

### #315 (bug) — `brandly report` cannot submit non-interactively
**Root cause:** `ask_permission` reads stdin via rich `Console.input`; on
non-tty EOF it returns False, `report` prints "skipped" and exits 0 — callers
cannot detect the no-op. `_resolve_token` only checks `GITHUB_TOKEN`,
`GH_TOKEN` and `~/.config/gh/hosts.yml` — missing `GH_CONFIG_DIR` and the
Windows `%APPDATA%\GitHub CLI\hosts.yml` location.

**Ruling (explicit headless contract):**
1. Non-tty stdin (EOF at the consent prompt) → explicit `NOT SUBMITTED`
   warning + **exit 2** (distinct from user-declined, which stays exit 0).
2. `--auto` with a failed submission → **exit 1** (was exit 0).
3. `_resolve_token` order: `GITHUB_TOKEN` → `GH_TOKEN` → `$GH_CONFIG_DIR/hosts.yml`
   → `%APPDATA%\GitHub CLI\hosts.yml` (win32) → `$XDG_CONFIG_HOME/gh/hosts.yml`
   → `~/.config/gh/hosts.yml`.

## Deliverables (per repo process)

- [x] `tests/test_issue_309.py` … `tests/test_issue_315.py` — RED first, then GREEN
- [x] Source fixes: `quality_gate.py`, `cmd/production.py`, `cmd/gate.py`,
      `shot_runner.py`, `issue_tracker.py`, skill docs
- [x] `python -m pytest tests/ -q` green — 1630 passed, 1 skipped
- [x] `ruff check src/ tests/` clean
- [x] CHANGELOG entry; dev-notes/PROGRESS.md round entry
- [x] Commit(s) on `fix/open-issues-309-315`, PR to `main` — PR #316 MERGED
      (commit f070c51). NOTE: squash-merge with "Closes #309…#315" only
      auto-closed #309; #310–#315 closed manually with fix evidence
      (chore: Round 31). CHANGELOG "audit PENDING" wording corrected post-merge.

## Non-goals

- No new JS test runner (issue #61 still open).
- No redesign of the screenplay phase — only act STRUCTURE extraction.
- No change to the Agnes 5-image cap itself.
- The auto-promotion path (#275) is not touched beyond what #309's gate fix unlocks.
