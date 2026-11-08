# GOAL — Issue #184: `init` must create the project in the cwd

> **Phase:** 3 (Engineer) · **Status:** in-progress
> **Issue:** <https://github.com/Dream-Pixels-Forge/brandly-cli/issues/184>

## 1. Objective

`brandly init` must create the project in the **current working directory**,
never in an ancestor `.brandly/` store (most notably the user's home, where the
persistent global store lives).

## 2. Root cause

`brandly_cli/cli.py::_get_root` — when neither `--root` nor `$ROOT` is set, it
walks **up** from `cwd` and returns the first ancestor containing a
`.brandly/` directory. The walk-up exists to prevent double-nesting when
running *from inside* `.brandly/<project-id>/`, but it also hijacks the root to
any ancestor that merely *has* a store.

Call site: `src/brandly_cli/cmd/production.py::init` line 114 — `root = _get_root(ctx)`.

## 3. Fix (issue option 1 + option 3)

1. `_get_root(ctx, *, create: bool = False)` — when `create=True` (i.e. `init`),
   the upward auto-detect is **skipped** and the root is `cwd`: the `.brandly`
   marker only matters when *reading* an existing project, never when
   *creating* a new one.
2. `_warn_if_ancestor_store(cwd)` — when `init` skips a detected ancestor
   store, tell the user (issue option 3): *"an ancestor .brandly store was
   found at `<path>`; creating the project here instead. Pass --root to use
   another location."*
3. **Explicit `--root` / `$ROOT` still win** — unchanged.
4. **Read/resume commands keep the walk-up** — unchanged (that behaviour is
   correct: `config` reports where the store actually *is*).

**Deliberately NOT changed:** `web/server.py::_discover_root` (the server is
only ever started by `brandly studio` to *read* an existing project, so its
walk-up is correct). Surgical change — no drive-by refactors.

## 4. Verification gates

| # | Gate | Command |
|---|---|---|
| 1 | Regression tests (RED first) | `python -m pytest tests/test_issue_184_init_root.py -v` |
| 2 | Existing CLI tests | `python -m pytest tests/test_cli.py tests/test_issue_19_24.py -q` |
| 3 | Lint | `ruff check src/ tests/` |
| 4 | Type check | `mypy src/` |
| 5 | Full suite | `python -m pytest tests/ -q` |
| 6 | E2E smoke | `make e2e` |
