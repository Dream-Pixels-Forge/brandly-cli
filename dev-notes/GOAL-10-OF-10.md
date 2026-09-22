# GOAL — Structural 10/10: cmd/ split, director demotion, hygiene, import-linter

> **Project:** brandly-cli · **Created:** session goal (goal-writer skill)
> **Base:** main @ 134f41a (v0.3.17) · **Blueprint:** `dev-notes/ARCHITECTURE-DIAGRAM.md` §5

## Goal: Raise structural groundedness from 8/10 to 10/10 without breaking the CLI surface

### Objective
Refactor `brandly_cli` so that (a) `cli.py` becomes a thin registration
module backed by `cmd/*` groups, (b) `director.py` is a pure prompt composer
(no provider/state imports), (c) provider modules are dumb (no prompting-layer
imports, no `agent_tools⇄agnes_client` cycle), (d) `utils.py` is split into
`planning.py` + `io.py` with a re-export shim, and (e) all layer rules are
enforced in CI via `import-linter` — with **zero behavioral change** to the
64-command CLI surface, proven by a before/after `--help` snapshot diff and
the full 500-test suite.

### Context
The static import-graph analysis (ARCHITECTURE-DIAGRAM.md) scores the package
8/10: layers are clean and cycle-free, but `cli.py` (fan-out 30, 4.8k lines)
and `director.py` (fan-out 13) are god modules, two providers reach upward
into the prompting layer (deferred imports), one deferred cycle exists
(`agent_tools ⇄ agnes_client`), and `utils.py` (fan-in 8) is a kitchen sink.
Without CI-enforced layer rules, the structure decays on the next feature.

### Deliverables (each own PR, in order)

**PR A — `cmd/` split (P0-1)** — DONE
- [x] `brandly_cli/cmd/{__init__,production,gate,post,providers,tools,generation}.py`
- [x] each module: commands defined with `@click.command()`, `register(cli)` entry point
- [x] `cli.py` reduced to: group definition, `register()` calls, shared helpers
      (784 lines; helpers like `_record_media_spend`/`_human_review_gate`/`_save_artifact`
      stay here until PR C moves them out)
- [x] CLI surface snapshot: `--help` for the group + all 64 subcommands captured
      BEFORE the split and diffed AFTER — byte-identical
- [x] target: `cli.py` ≤ ~600 lines — 784 now; the remainder is exactly the
      shared-helpers block PR C splits out (so the ≤600 target lands with PR C)

**PR B — director demotion + provider hygiene (P0-2, P1-3, P1-4)** — DONE
- [x] `director.py` fan-out 0 (pure prompt composer: `DIRECTOR_PROMPT` +
      `get_director_prompt()`; target was ≤ 4). `Director`/`DirectorConfig`
      moved to the caller layer `cmd/production.py`.
- [x] `agnes_client.py` / `ark_client.py` no longer import `style_presets`;
      style application happens in the callers (`cmd/generation.py` video,
      `cmd/production.py` batch + Director, `cmd/providers.py` ark commands).
      `style_preset` kwarg removed from the four provider entry points;
      Ark video task's hard-coded "cinematic" application now explicit in callers.
- [x] `agent_tools ⇄ agnes_client` cycle broken via new `job_polling.py`
      shared helper (one-directional arrows: both modules → job_polling).
- [x] Re-run static graph (`scripts/import_graph.py`): zero hard cycles,
      zero upward provider→prompting edges; one runtime-safe deferred cycle
      (`cli ⇄ cmd.generation`, intentional end-of-module `register` design).

**PR C — utils split + import-linter + layout contract tests (P1-5, P2-6, P2-8)**
- [ ] `utils.py` split: `planning.py` (generation/production plans),
      `io.py` (JSON I/O, download, timestamps, sanitizers);
      `utils.py` keeps re-export shims (marked deprecated) so nothing breaks
- [ ] `.importlinter` config: layered (L0→L5 as in ARCHITECTURE-DIAGRAM.md §5),
      no-cycles forbidden; CI step added to `.github/workflows/ci.yml`
- [ ] v2 layout contract test: `init --layout v2 → produce (mocked gen) →
      migrate dry-run` idempotency + apply
- [ ] `_record_media_spend` / `_human_review_gate` / `_save_artifact` moved
      out of `cli.py` into testable modules (cost_tracker / gates / utils)

### Definition of Done
- [ ] `PYTHONPATH=src python -m pytest tests/ -q` → 0 failures (500+ tests)
- [ ] `ruff check src/ tests/` and `mypy src/` clean
- [ ] CLI surface snapshot diff is empty (help texts identical before/after)
- [ ] Static import graph: 0 cycles, 0 upward edges, `cli` fan-out ≤ 6,
      `director` fan-out ≤ 4
- [ ] `import-linter` passes locally AND in CI; a deliberate upward import
      in a scratch file FAILS it (sanity check)
- [ ] Wheel builds, `twine check` passes; version stays 0.3.17 (refactors
      only — no version bump needed; note it in CHANGELOG if behavior-adjacent)

### Verification Steps
1. BEFORE any PR: capture `PYTHONPATH=src python -m brandly_cli --help` and
   every subcommand's `--help` to `dev-notes/_cli_snapshot_before.txt`
2. AFTER each PR: regenerate `dev-notes/_cli_snapshot_after.txt` and
   `diff` — must be empty
3. `PYTHONPATH=src python -m pytest tests/ -q` — 0 failures
4. `ruff check src/ tests/` + `mypy src/` — clean
5. Re-run the static graph script (`dev-notes/_arch.json` generator) —
   verify fan-out targets and zero cycles
6. `python -m build --wheel` + `python -m twine check dist/*`
7. Per PR: CI green on GitHub before merge

### Anti-Drift Rules
- **Behavioral equivalence is the contract.** Any test that changes a help
  string, exit code, or file path is a defect, not a fix — revert the edit.
- One concern per PR; if a PR needs to touch another PR's files, stop and
  re-plan the boundary.
- Do not delete `utils.py` re-export shims inside PR C (deprecation is a
  later version).
- No new third-party runtime deps (import-linter is dev-only).
- If blocked by a hidden behavioral coupling, report the blocker with the
  failing test/command — do not work around it silently.

### Estimated Effort
PR A: 1–2 days (mechanical but large diff). PR B: half a day.
PR C: half a day + 1h for import-linter setup. Total ≈ 2–3 days.
