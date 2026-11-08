# GOAL — brandly-casting skill + release v0.12.1

> **Project:** brandly-cli · **Created:** goal-writer session (2026-10-09)
> **Base:** `origin/main` @ `a296679` (v0.12.0)
> **Convention:** every increment is RED → GREEN (contract test first),
> all gates green before commit; release follows the proven v0.12.0 flow
> (branch → PR → squash-merge → tag → GitHub release → PyPI → verify).
> **User request:** "set a new goal for version 0.12.1, add new skill called
> 'brandly-casting', this one generate image from production bible, the image
> of the character, a portrait of the character and also full body portrait
> for wardrobe all of this can serve for the generation of the character
> sheet, the pipeline can become cast from production bible, try wardrobe and
> generate character sheet from cast" — and "they are also skill shipped with
> brandly-cli don't forget".

## Program Objective

Add the **`brandly-casting` bundled Agent Skill** — the casting pipeline:
**cast from production bible → try wardrobe → character sheet from cast** —
and ship it inside the brandly-cli wheel as release **v0.12.1**, verified at
the same latest version on code, GitHub, and PyPI.

## The casting pipeline (what the skill teaches)

```
production bible (Section 4: Characters)
      │
      ▼
1. CAST — per character, generate the cast set:
   ├── character image   (hero shot of the character in context)
   ├── portrait          (headshot — face detail for identity locking)
   └── full-body portrait for wardrobe (standing, head-to-toe)
      │
      ▼
2. TRY WARDROBE — wardrobe variations generated image-to-image from the
   full-body portrait (the wardrobe reference), one variation per outfit
      │
      ▼
3. CHARACTER SHEET FROM CAST — the cast set (portrait + full-body +
   wardrobe tries) serves as the reference set for the character sheet /
   GOLD reference plate
```

## Phases

### P1 — the `brandly-casting` skill (RED → GREEN)

**Deliverables**
- [x] `skills/brandly-casting/SKILL.md` — frontmatter `name: brandly-casting`,
      description = single activation sentence with trigger phrases; states
      which `brandly` command(s) it drives (the skills/README.md rule 3);
      SKILL.md ≤ ~100 lines with long material in `references/`
- [x] `skills/brandly-casting/references/prompt-variants.md` — the cast /
      portrait / full-body-wardrobe / wardrobe-try prompt templates (linked
      from SKILL.md; the link must exist — test_skills.py checks)
- [x] `skills/README.md` — skill map row for `brandly-casting` (drives
      `brandly image` + `brandly reference` + `brandly gate`)
- [x] Installed copy `~/.agents/skills/brandly-casting/` (identical to the
      bundled one — the two trees stay in sync; `diff -r` clean)
- [x] RED-first proof: created the skill dir and observed
      `tests/test_skills.py` FAIL (5 failed, missing SKILL.md) before
      writing the real SKILL.md, then observed PASS (5 passed)

**Definition of Done**
- [x] `tests/test_skills.py` green — all 5 contract tests over every bundled
      skill including `brandly-casting` (folder==name, description, referenced
      docs exist, mentions the CLI)
- [x] Full suite green (1528 passed / 1 skipped); ruff clean; mypy clean (5
      pre-existing PIL-only)
- [x] The skill teaches the cast → wardrobe → sheet pipeline and never
      bypasses the production plan or the 1 req/min rate limit (README rule 4
      — the never-bypass rule lives in prompt-variants.md:112 AND ships in
      the wheel; verified in the released 0.12.1 wheel)
- [x] Cast image paths follow the real layout: `pre-production/<id>/character/`
      with the `char_` prefix convention (auto-injectable + resolvable by stem)

**Verification Steps**
1. `python3 -m pytest tests/test_skills.py -v` — green (5/5)
2. `diff -r skills/brandly-casting ~/.agents/skills/brandly-casting` — identical
3. `grep -c "brandly" skills/brandly-casting/SKILL.md` — ≥1 (drives the CLI)

### P2 — release v0.12.1 (code + GitHub + PyPI all match)

**Deliverables**
- [x] `src/brandly_cli/__about__.py` → `0.12.1` (single source)
- [x] `CHANGELOG.md` → `[0.12.1]` entry (the casting skill); `[Unreleased]` emptied
- [x] Commit via branch → PR #269 → squash-merge `987de37` (all 4 CI checks green, zero warnings)
- [x] Tag `v0.12.1` + GitHub release (triggers the Release-to-PyPI workflow)
- [x] PyPI publish lands (trusted publishing; version-check gate passes;
      PEP 740 attestations; 2 files, not yanked)
- [x] Wheel contains the new skill (`brandly_cli/skills/brandly-casting/`
      verified in a fresh venv install)

**Definition of Done**
- [x] Version 0.12.1 = the same latest on code, GitHub, and PyPI
- [x] Version-check gate: `tag v0.12.1 matches single source 0.12.1`
- [x] Full workflow run success (all steps); attestations published (run 37890500187)
- [x] Smoke test: fresh venv `pip install brandly-cli==0.12.1` → import OK,
      `brandly --version` = 0.12.1, the bundled skill + never-bypass rule
      present in the wheel install
- [x] goal-met audit: verdict **MET** (independent, 16 checks re-run via
      `check_goal.py all`; confidence 10/10; gate PASS)

**Verification Steps**
1. `python3 scripts/version_check.py --tag v0.12.1` — OK
2. `curl -s https://pypi.org/pypi/brandly-cli/0.12.1/json | ...` — 2 files, not yanked
3. `curl -s https://pypi.org/pypi/brandly-cli/json | ...` — latest 0.12.1
4. `gh release view v0.12.1` — exists; `gh release list` — Latest
5. Fresh venv: `pip install brandly-cli==0.12.1` + inspect
   `site-packages/brandly_cli/skills/brandly-casting/SKILL.md` — exists
6. goal-met audit with `check_goal.py all` + `confidence` — MET at 10/10

## Anti-Drift Rules

- The skill is prompt-craft + workflow instructions driving EXISTING CLI
  commands — no new CLI phases, no code changes beyond the version bump.
- Never teach a workflow that bypasses the production plan or the 1 req/min
  Agnes rate limit (skills/README.md rule 4).
- Data honesty: cast image paths, prefixes, and rate limits sourced from the
  code (`layout.py`, `shot_runner.py`), not invented.
- The version is 0.12.1 exactly as the user specified.
- If blocked, report the blocker — do not skip verification silently.

## Estimated Effort

One session: P1 ~30 min (skill + RED proof), P2 ~45 min (bump + release +
verification, paced by CI runs).

## Live pipeline test (2026-10-09) — idea → production, 2 characters presenting

Real end-to-end run (project `brewmaster-one` at `/tmp/brandly-demo`, real
`AGNES_API_KEY`, ~100 credits): **cast from the bible → try wardrobe →
character sheet from cast — all verified working.** Video generation BLOCKED
by a provider-side outage (consistent HTTP 503 from
`apihub.agnes-ai.com/v1/videos` over 521s of retries + WriteTimeout; the
IMAGE service worked 10/10 throughout — matches the closed #191/#192
provider-503 class; external, not a code bug).

**Verified working:**
- init → trends → concept (agent-driven) → script — the phase chain runs
- CAST: 6 images (hero 3:2 / portrait 3:4 / full-body 2:3 × Maya + Theo) via
  the new skill's flow, cost-tracked (10 credits each)
- TRY WARDROBE: 2 variations (i2i via project auto-refs) in the dedicated
  `wardrobe/` REF_CATEGORY
- CHARACTER SHEET FROM CAST: 2 GOLD reference plates (16:9 multi-view,
  `char_<slug>_<ts>.jpg`), auto-injected as primary references
- The reference gate caught a real mismatch honestly (plate 68/100 — missing
  wardrobe render; AI verdict warn; exit 1) and the #250 auto-approve
  auto-approved the passing plate
- The reference cap (model limit 5) capped cleanly with a drop list

**Issues found on the road — filed (git-driven-development):**
- [#270] `current_phase="video"` (invalid phase) poisons project.json →
  run/approve/run --execute all crash with unhandled ValueError (3 sites)
- [#271] `cli.py:125` bare `asyncio.run(` — GOLD reference silently dropped
  on pipeline-path video calls (the #249 fix missed this site)
- [#272] `--output` resolves relative to the CLI cwd, ignoring `--root` —
  6 cast images landed in the brandly-cli repo itself
- [#273] trends phase silently writes an empty trends.md (style passed as
  research category; TREND_DATABASE only has product categories)
- [#274] script phase hardcodes beat_durations conflicting with
  scenes.BEAT_DURATIONS + the beat cycle wraps the closing shot to "setup"
- [#275] reference command updates primary_reference BEFORE the gate — a
  gate-FAILED plate becomes the auto-injected identity anchor
- [#276] the requested film duration never reaches the pipeline (no
  --target-duration on init/project.json; 30s request produced 24s unchecked)
- [#277] `run --execute` dead-ends at concept — the CLI never wires
  DirectorConfig.agent_runner (agnes-chat could be the default)
- [#278] reference/image --help docstrings state wrong save paths + prefix;
  `brandly reference` lacks `--json`

**Demo state:** pipeline bricked at asset by #270 (repaired manually for
diagnosis: current_phase reset to "asset"); video blocked by the provider
503. The 9 issues are the fix queue.
