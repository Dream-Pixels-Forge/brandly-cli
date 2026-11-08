# GOAL — Studio Shell implementation (from Paper design)

> **Phase:** 3 (Engineer) · **Status:** in-progress
> **Design source:** `dev-notes/DESIGN-STUDIO-SHELL.md` (FROZEN)

## 1. Objective

Implement the Brandly Studio shell in `web/` to match the frozen Paper design,
without drifting from the ratified repo conventions.

## 2. Anti-drift constraints

1. **Repo convention wins over invention.** This repo verifies frontend work
   with **Python source-contract tests** + build-freshness (`web-quality` CI job).
   `tests/test_web_panels_wired.py` and `test_web_shell_boot.py` both state
   “no JS test runner in CI yet — see #61”. Adding vitest/Jest is a *separate,
   unratified* architecture decision → **do not add one**.
2. **No new token namespace.** Reuse `--md-*`; only *define* the missing vars.
3. **No new API/data.** Build UI against the existing zustand store + `/api`.
   Missing data renders as absent, never faked.
4. **Do not touch** `web/monitor.py`, `web/review.py`, `web/server.py` unless the
   design requires it (it does not).
5. Screens **05/06 are out of scope** (no Paper design exists yet).

## 3. Work breakdown (incremental, TDD per increment)

| Inc | Deliverable | Files |
|---|---|---|
| **A** | Shell: Toolbar + Status Bar + sidebar restructure + tokens | `index.html`, `Toolbar.tsx`, `StatusBar.tsx`, `SidebarNav.tsx`, `Shell.tsx`, `Shell.css` |
| B | Preview: transport overlay + ClipInspector rail + 3-track timeline | `PreviewPanel.tsx`, `TransportControls.tsx`, `ClipInspectorPanel.tsx` (new), timeline/* |
| C | Shot List: inspector tabs + bulk select | `ShotListPanel.tsx`, `store.ts` |
| D | Render/Monitor: steppers + column balance | `RenderDispatchPanel.tsx`, `ProductionMonitorPanel.tsx`, `PipelineStepper.tsx` (new), `PhaseStepper.tsx` (new) |

## 4. Verification gates (all must be green to call an increment done)

| # | Gate | Command |
|---|---|---|
| 1 | New source contract | `python -m pytest tests/test_web_studio_shell.py -v` |
| 2 | Existing SPA contracts | `python -m pytest tests/test_web_panels_wired.py tests/test_web_shell_boot.py tests/test_web.py -v` |
| 3 | Frontend lint | `npm --prefix web run lint` |
| 4 | Typecheck + build | `npm --prefix web run build` |
| 5 | Bundled SPA fresh | `git diff --exit-code -- src/brandly_cli/web/static/` |
| 6 | Full Python suite | `python -m pytest tests/ -q` |

## 5. TDD protocol

Per increment: write the contract test **RED** → run and observe failure →
implement **GREEN** → run all gates. Bug fixes start with a regression test.

## 6. Known latent defect this work resolves

`--md-radius-sm/-md/-lg`, `--md-transition-fast`, `--md-font-display-lg`,
`--md-font-code-inline`, `--md-font-body-md` are **referenced in ~20 components
but never defined**, so radii/fonts/transitions silently fall back to browser
defaults. The frozen design requires them → define them in `web/index.html`.
