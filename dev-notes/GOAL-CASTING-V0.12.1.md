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
- [ ] `skills/brandly-casting/SKILL.md` — frontmatter `name: brandly-casting`,
      description = single activation sentence with trigger phrases; states
      which `brandly` command(s) it drives (the skills/README.md rule 3);
      SKILL.md ≤ ~100 lines with long material in `references/`
- [ ] `skills/brandly-casting/references/prompt-variants.md` — the cast /
      portrait / full-body-wardrobe / wardrobe-try prompt templates (linked
      from SKILL.md; the link must exist — test_skills.py checks)
- [ ] `skills/README.md` — skill map row for `brandly-casting` (drives
      `brandly image` + `brandly reference` + `brandly gate`)
- [ ] Installed copy `~/.agents/skills/brandly-casting/` (identical to the
      bundled one — the two trees stay in sync)
- [ ] RED-first proof: create the skill dir and observe
      `tests/test_skills.py` FAIL (missing SKILL.md / frontmatter) before
      writing the real SKILL.md, then observe PASS

**Definition of Done**
- [ ] `tests/test_skills.py` green — all 5 contract tests over every bundled
      skill including `brandly-casting` (folder==name, description, referenced
      docs exist, mentions the CLI)
- [ ] Full suite green; ruff clean; mypy clean (5 pre-existing PIL-only)
- [ ] The skill teaches the cast → wardrobe → sheet pipeline and never
      bypasses the production plan or the 1 req/min rate limit (README rule 4)
- [ ] Cast image paths follow the real layout: `pre-production/<id>/character/`
      with the `char_` prefix convention (auto-injectable + resolvable by stem)

**Verification Steps**
1. `python3 -m pytest tests/test_skills.py -v` — green
2. `diff -r skills/brandly-casting ~/.agents/skills/brandly-casting` — identical
3. `grep -c "brandly" skills/brandly-casting/SKILL.md` — ≥1 (drives the CLI)

### P2 — release v0.12.1 (code + GitHub + PyPI all match)

**Deliverables**
- [ ] `src/brandly_cli/__about__.py` → `0.12.1` (single source)
- [ ] `CHANGELOG.md` → `[0.12.1]` entry (the casting skill); `[Unreleased]` emptied
- [ ] Commit via branch → PR → squash-merge (all CI checks green, zero warnings)
- [ ] Tag `v0.12.1` + GitHub release (triggers the Release-to-PyPI workflow)
- [ ] PyPI publish lands (trusted publishing; version-check gate passes)
- [ ] Wheel contains the new skill (`brandly_cli/skills/brandly-casting/`)

**Definition of Done**
- [ ] Version 0.12.1 = the same latest on code, GitHub, and PyPI
- [ ] Version-check gate: `tag v0.12.1 matches single source 0.12.1`
- [ ] Full workflow run success (all steps); attestations published
- [ ] Smoke test: fresh venv `pip install brandly-cli==0.12.1` → import OK,
      the bundled skill present in the wheel install
- [ ] goal-met audit: verdict **MET** (independent, re-runs every Verification
      Step; confidence 10/10)

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
