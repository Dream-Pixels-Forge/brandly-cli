# HANDOFF — brandly-cli: casting skill + release v0.12.1 + live pipeline test
> Status: **v0.12.1 SHIPPED & VERIFIED (casting goal MET at 10/10) — 13-issue fix queue open (#270–#283)** · For new session

## 1. Current state

**DONE (all merged to main, CI all green):**
- **v0.12.0** (`5a2c356`, PR #267): version bump + CHANGELOG + README rewrite (fixed BOM/corrupted fences/eaten chars; real 83-command / 22-tool surface). 0.11.1's publish FAILED at the version-check gate (tag said 0.11.1, `__about__.py` said 0.11.0); PyPI skipped it; 0.12.0 superseded. Verified on all three + smoke test.
- **GOAL-ALL-OPEN-ISSUES close-out** (`040f289`, PR #266): 16 issues closed, goal-met MET.
- **brandly-casting skill** (`987de37`, PR #269) + **release v0.12.1**: cast from production bible (Section 4) → try wardrobe → character sheet from cast. Cast set per character: hero `3:2` / portrait `3:4` / full-body `2:3`; wardrobe tries i2i via auto-refs (dedicated `wardrobe/` REF_CATEGORY, `wardrobe_` prefix); GOLD plate (16:9, `char_<slug>_<ts>`) auto-injected. RED-first: 5 contract tests FAILED (empty dir) → 5 passed. Ships in the wheel + installed `~/.agents/skills/brandly-casting/` (in sync) + skills/README.md row. Verified: code/GitHub/PyPI all **0.12.1**, wheel carries skill + never-bypass rule, goal-met **MET 10/10**. Ledger Round 27 (`a296679`) + findings (`0c4924f`, PR #279).
- **Live pipeline test** (`brewmaster-one` at `/tmp/brandly-demo`, ~100 credits): CAST (6) → WARDROBE (2) → SHEET (2 GOLD plates) all working; gate caught a real mismatch honestly (68/100, exit 1); #250 auto-approve approved the passing plate. **Video BLOCKED: provider 503 from `apihub.agnes-ai.com/v1/videos`** (images 10/10; external — matches closed #191/#192).

**THE FIX QUEUE — 13 open issues (#270–#283):**
- **#270 [HIGHEST]** `current_phase="video"` (invalid, not in PHASE_ORDER) written by `generation.py:2340` `_sync_project` → poisons project.json → `run`/`approve`/`run --execute` ALL crash unhandled ValueError at `production.py:3290/363/531`. Project BRICKS.
- **#271 [HIGH]** `cli.py:125` `_load_project_reference` bare `asyncio.run(` → RuntimeError swallowed → **GOLD reference silently dropped** on pipeline-path video calls (#249 fix missed cli.py). Also audit `agent_tools.py`/`web/` sites.
- **#272 [HIGH]** `image --output` resolves relative to the **CLI cwd**, ignoring `--root` — 6 cast images landed INSIDE the brandly-cli repo; project root stayed empty. (Inverse of #184.)
- **#273** trends silently writes an EMPTY trends.md — pipeline passes the project's **style** as the research **category**; `TREND_DATABASE` only has product categories (beauty/fashion/fitness/food/tech).
- **#274** script phase hardcodes `beat_durations` (4/5/5/6) **conflicting** with `scenes.BEAT_DURATIONS` (5/6/6/5) — shots.json vs scenes.json disagree; + beat cycle wraps the closing 5th shot to "setup".
- **#275** `primary_reference` updated BEFORE the gate (`generation.py:488` before 490) — a gate-FAILED plate becomes the identity anchor.
- **#276** film duration never reaches the pipeline — no `--target-duration` on init/project.json; 30s request → 24s unchecked.
- **#277** `run --execute` dead-ends at concept — CLI never wires `agent_runner` (agnes-chat could be the default).
- **#278** reference/image `--help` state WRONG paths (`.brandly/<id>/images/` vs real `pre-production/<id>/`) + WRONG prefix (`reference_*` vs `char_*`); `reference` lacks `--json`.
- **#280** screenplay declared (DOC_CATEGORIES + analyze-project checks against it) but NEVER created — no writer. Screenplay = core shots; **transitions/inserts are additional elements the Director can add** for cinema-completeness.
- **#281** duplicate storyboard trees — `brandly storyboard` writes legacy `.brandly/<id>/images/storyboard/` while v2 declares `pre-production/<id>/storyboard/`; AND the pipeline never generates storyboards (skips #33's catch-at-image-cost step).
- **#282** `reference` REJECTS `--subject-type wardrobe` (not in choices) though layout declares it first-class; no wardrobe-only mode (garment flat-lay WITHOUT a person).
- **#283** duplicate video trees — `migrate.py:33-34` maps singular→PLURAL (`transitions`, `inserts`) while `VIDEO_CATEGORIES` (layout.py:63) + `shot_runner.py:959` use singular; AND clips never land in their respective folder (all primary clips → `videos/scenes/`).

## 2. Remaining work (in order)

1. **Fix round via git-driven-development** — branch-per-issue, RED-first, PR per fix. Start #270 (bricks), #271 (silent data loss), #272 (root-path hijack).
2. Then #275 (metadata ordering), #274 (import scenes.BEAT_DURATIONS), #273 (product_category field or fail-honest), #277 (wire agnes-chat as default concept runner).
3. Then #281–#283 (pick ONE singular/plural convention, route clips by folder), #282 (wardrobe subject-type), #276 (target-duration → script), #278 (docstrings + --json).
4. After the round: release v0.12.2 (bump + CHANGELOG + tag + GitHub release + PyPI verify — the proven flow).
5. Re-run the live pipeline test end-to-end (video when the 503 clears) — expect storyboard step runs, clips land in respective folders, concept passes via --execute.

**NEXT COMMAND:** `/home/dimona/bin/gh issue list --state open` then `git checkout -b fix/phase-poisoning-270` — RED-first test for #270.

## 3. Verified ground truth (MUST carry forward)

- **`python` is not on PATH — use `python3`.** mypy/import-linter not preinstalled: `pip install --break-system-packages mypy import-linter` (test_architecture_contracts.py collection-ERRORs without it).
- **PyPI simple-index lags the version endpoint by minutes** — `pip install` can fail right after a green publish; retry before declaring it broken. The workflow's hard gate (version endpoint with files) is the truth for "did the publish land".
- **Version lives in ONE place**: `src/brandly_cli/__about__.py` (hatch dynamic). Gate: `python3 scripts/version_check.py --tag vX.Y.Z`.
- **`current_phase="video"` is POISON** — not in PHASE_ORDER (constants.py:79). Writer: `generation.py:2340`. Crash sites: production.py:3290 (run_pipeline), 363 (run), 531 (approve).
- **`TREND_DATABASE` keys are product categories** (beauty/fashion/fitness/food/tech), NOT styles.
- **`scenes.BEAT_DURATIONS`** = setup 5/turn 6/consequence 6/resolve 5 — the script phase's local copy (4/5/5/6) is WRONG (#274).
- **Cast/reference conventions**: `IMAGE_NAME_PREFIXES` character→`char`, location→`loc`, object/prop→`prop`; unknown → lowercased type (`wardrobe_`). `REF_CATEGORIES` = (character, location, prop, wardrobe). Plates land in `pre-production/<id>/<category>/` (v2 root — NOT `.brandly/<id>/images/`, dead but `brandly storyboard` still writes it — #281).
- **`brandly reference` has NO `--json`**; `--subject-type` choices OMIT wardrobe (#278/#282).
- **Reference auto-approve**: `ai_verdict="pass"` + score ≥ 90 → auto-approves; warn/fail prompts Y/n — and **CliRunner AUTO-ANSWERS Y** (beware in tests).
- **AGNES_API_KEY IS set** — real runs spend credits (image ~10 @2K; video 503'd this session — provider outage, images unaffected).
- **Storyboard mandatory** (#216/#218): 4x4 grid + **graphite pencil on white paper** + same-face/same-silhouette continuity + one model call per frame + local PIL tiling — `skills/brandly-storyboard/references/grid-style-lock.md`, MANDATORY/STRICT.
- **`gh issue view` needs `--json <fields> -q '...'`** (plain view errors).
- **ALWAYS `git branch --show-current` before committing** — after `gh pr merge --delete-branch` git checks main out (Round 24 break — not repeated since).

## 4. Files changed this session

`__about__.py` (0.11.0→0.12.1) · `CHANGELOG.md` ([0.12.0]+[0.12.1]) · `README.md` (rewrite) · `skills/brandly-casting/` (NEW) · `skills/README.md` (row) · `dev-notes/GOAL-CASTING-V0.12.1.md` (NEW, audit MET) · `dev-notes/PROGRESS.md` (Rounds 26–27) · `HANDOFF.md` (this file; old record preserved at `040f289`)

## 5. How to verify when you land

```bash
git pull && git log --oneline -4   # expect 0c4924f on top
python3 -m pytest tests/ -q        # expect: 1528 passed / 1 skipped
python3 scripts/version_check.py --tag v0.12.1   # tag OK
ruff check src/ tests/             # All checks passed
curl -s https://pypi.org/pypi/brandly-cli/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"   # 0.12.1
```

## 6. Goal spec & verdict

- Goal: `dev-notes/GOAL-CASTING-V0.12.1.md` — brandly-casting skill + release v0.12.1
- Verdict: **MET** (16 checks via `check_goal.py all`, confidence 10/10, `goal_loop.py gate` PASS; fingerprint `41dc6ef4187af2d7…`)

## 7. Environment facts

- Node v24 / pnpm 11.5.1; web uses npm (`npm --prefix web run lint/build`)
- Python 3.12.3 → `python3`; mypy + import-linter via `pip install --break-system-packages`
- On `main` @ `0c4924f`; repo `/home/dimona/Dream-Pixels-Forge/Dev/cli/brandly-cli`
- Demo: `/tmp/brandly-demo` (`brewmaster-one`, state repaired for #270 diagnosis; video blocked by provider 503)
- memorius diary MCP tool BROKEN for multi-word titles (#59 on pi-memorius) — use `memorius_store`
