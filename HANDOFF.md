# HANDOFF — brandly-cli
> Status: **v0.14.2 shipped+verified · ISS-0052 (legacy removal) inventory ready, ZERO code changes · For new session**

## 1. Current state
DONE (evidence):
- CI/CD restored: `d70e6ba` (ISS-0048: missing `run_async` import io.py:461 + F401 cost_tracker), `4223006` (ISS-0051: revert 8c36bbd, #314 paths), `1aa97ab` (changelog 0.14.2). CI green run `38692580349` (4/4 jobs).
- v0.14.2 released: tag + GitHub release + PyPI (workflow `38693605090`). 3-way verified (code=tag=release=PyPI 0.14.2); wheel content inspected — fix present. ISS-0048/0051 closed.
- HEAD `1aa97ab`, tree clean. `LEGACY-REMOVAL-INVENTORY.md` at repo root = untracked, git-excluded (`.git/info/exclude`).

IN PROGRESS — **ISS-0052** (high, blocking): legacy layout removal → v0.15.0. Full audit DONE (explore agent); inventory at `./LEGACY-REMOVAL-INVENTORY.md` (file:line precision, sections A–G, coupling map, 14 RED tests). Two implement-coder dispatches aborted — **no code changes exist**.

## 2. Remaining work (in order)
1. Read `./LEGACY-REMOVAL-INVENTORY.md` fully.
2. Dispatch `implement/implement-coder`: read inventory first, RED-first all 14 negative tests (observe fail, save output — #11 is a live bug), remove/rewrite per A–G + coupling map, version→0.15.0, CHANGELOG after [0.14.2], HANDOFF/PROGRESS append, conventional commit `ISS-0052`. NO push/tag/release. (Subagents CANNOT see swarm context files — embed everything or point at the repo-root inventory.)
3. Verify gates: `ruff check src/ tests/`; `python3 -m mypy src/` (6 PIL baseline only); import-linter (`.importlinter:23` must drop `brandly_cli.migrate`); `python3 scripts/version_check.py` → 0.15.0; full pytest (baseline 1637 passed/1 skipped — expect shrink+grow, demand the arithmetic).
4. Push main → `gh run watch` (~2m15s, 4 jobs).
5. `gh release create v0.15.0 --notes-file` — extract [0.15.0] changelog section (awk from heading to next `## [` — NOT to [0.14.1]; 0.14.2 mistake lesson).
6. Watch "Release to PyPI" workflow → 3-way verify (code=tag=release=PyPI 0.15.0) + download wheel, zipfile-inspect content (fix present).
7. Close ISS-0052, swarm_snapshot, heartbeat. Delete inventory file + its `.git/info/exclude` line.

## 3. Verified ground truth
- Swarm `.prides` state lives OUTSIDE repo → context files invisible to subagents. Embed full context in dispatch prompts.
- `/tmp/opencode` WIPED on server restart (proven 2026-10-16) → durable working files = repo root + `.git/info/exclude`.
- `python3` (no `python`); ruff 0.17.0 at `~/.local/bin/ruff`.
- mypy: 6 PIL `import-untyped` errors = pre-existing LOCAL noise, CI unaffected — never chase.
- `.importlinter:23` lists `brandly_cli.migrate` — MUST edit when migrate.py deleted or gate fails.
- release.yml triggers on release **published** (`gh release create` auto-tags); PyPI = OIDC trusted publishing, no tokens.
- **USER MANDATES LOCKED (do not re-litigate)**: v2-only layout; delete `migrate` entirely (v1 projects not auto-upgradable — accepted); remove ALL legacy location fallbacks; 3d-spatial → `pre-production/<id>/3d-spatial/`; STRICT docs taxonomy: `docs/general`=concept,trends,scenes(+casting doc IF ever — none exists; casting phase outputs are pre-production images, untouched), `docs/screenplay`=screenplay, `docs/plan`=plan+production_plan ONLY, `docs/bible`+`docs/tmp` untouched; ship v0.15.0.
- Latent bug fixed by ISS-0052: `cli.py:446 _latest_project_media` scans legacy-only → `brandly gate` auto-detect blind on v2 (caller `cmd/gate.py:398`).
- #314 `LEGACY_RE` gap: single-line only — `skills/brandly-video-generation/SKILL.md:22-33` multi-line legacy tree evades → widen contract.
- Legacy WRITE path `web/routes/clips.py:163` (writes `.brandly/<id>/videos/scenes/`) must be fixed WITH `state.py` read or regenerated clips 404.
- CHANGELOG newest block ascending — insert [0.15.0] after [0.14.2], before [0.10.2] (~line 228).
- Direct push to main = repo norm; user approves releases; RED→GREEN mandatory (repo AGENTS.md).

## 4. Files changed this session
- `d70e6ba`: io.py, cost_tracker.py, tests/test_issue_73.py, HANDOFF.md
- `4223006`: 6 skills/*.md (#314 paths)
- `1aa97ab`: CHANGELOG.md, HANDOFF.md
- v0.14.2: git tag, GitHub release, PyPI artifacts
- Untracked+excluded: LEGACY-REMOVAL-INVENTORY.md; `.git/info/exclude` (+1 line)

## 5. Verify when you land
```bash
git log --oneline -1    # 1aa97ab, tree clean
ls LEGACY-REMOVAL-INVENTORY.md   # exists (untracked, excluded)
ruff check src/ tests/            # green
python3 scripts/version_check.py # 0.14.2 (until coder bumps 0.15.0)
python3 -m pytest tests/ -q      # 1637 passed, 1 skipped (~108s)
```

## 6. Goal spec & verdict
- Goal A: restore CI/CD + ship v0.14.2 → **MET** (CI 38692580349 green; PyPI 0.14.2; wheel inspected).
- Goal B: legacy removal v0.15.0 (ISS-0052) → **NOT-MET / IN PROGRESS**. Inventory ready; zero code changes. Next = §2 step 2 (dispatch implement-coder).

## 7. Environment facts
- Repo `/home/dimona/Dream-Pixels-Forge/Dev/cli/brandly-cli`; origin `Dream-Pixels-Forge/brandly-cli`; gh authed.
- CI gate order (ci.yml): version_check → ruff → import-linter → mypy → py_compile → pytest → build → twine; web-quality separate (npm — untouched by ISS-0052).
- No JS test runner (repo issue #61) — Python source-contract tests are the SPA verification convention.
