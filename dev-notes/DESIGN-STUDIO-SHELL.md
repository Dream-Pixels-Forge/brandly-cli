# DESIGN — Brandly Studio Shell (Paper-sourced, FROZEN)

> **Source of truth:** Paper file `01M3VWT0PHVWKPN9JSECCES8T4`, page `p-3-0`
> (“Brandly Studio — Web UI”), artboards `01 · Preview Player` (`8R-0`),
> `02 · Shot List` (`8S-0`), `03 · Render Queue` (`8T-0`),
> `04 · Production Monitor` (`8U-0`).
> **Status:** FROZEN. Implement exactly this; do not improvise layout.

## 1. Scope

**In scope**
- App shell: **Toolbar** (new) + **Status Bar** (new) + sidebar restructure.
- Artboards 01–04 structural/UX deltas (below).

**OUT of scope — no design exists, do NOT build**
- Screen 05 (Review Queue) and 06 (Agnes AI Synthesizer): the Paper
  artboards are **empty (0 children)**. Their design pass is pending.
- New API endpoints, new providers, or new data models.

## 2. Shell metrics (1440×900 reference)

| Region | Metric |
|---|---|
| Header | 52px, fixed (unchanged) |
| **Toolbar** | **40px, new** — sits directly under Header |
| Body | `flex:1`, row |
| ↳ Sidebar | 248px fixed (`16rem` today → 248px) |
| ↳ Main | `flex:1`, `padding:14px`, `gap:12px` |
| **Status Bar** | **28px, new** — pinned bottom |

Stack: `0–52` Header · `52–92` Toolbar · `92–872` Body · `872–900` Status Bar.
Body inner width = `1440 − 248 = 1192`; Main content = `1192 − 28 = 1164`.

## 3. Token contract — reuse MD3, do not fork

The Paper `--studio-*` tokens are **aliases** of the existing MD3 variables.
Do **not** add a second token namespace. Instead **define the variables that
are referenced but missing today** in `web/index.html` (`:root`):

```
--md-radius-sm: 4px;  --md-radius-md: 8px;  --md-radius-lg: 12px;
--md-transition-fast: 150ms;
--md-font-display-lg: 'Space Mono', monospace;
--md-font-code-inline: 'Space Mono', monospace;
--md-font-body-md:    'Hanken Grotesk', sans-serif;
```

Alias map (studio → existing md):

| Paper token | Code variable |
|---|---|
| `--studio-bg` | `--md-surface` (#131316) |
| `--studio-surface-low/-lowest/-high/-highest` | `--md-surface-container-low` / `-lowest` / `-high` / `-highest` |
| `--studio-border` | `--md-surface-container-highest` |
| `--studio-primary` | `--md-primary` |
| `--studio-text` / `--studio-text-muted` | `--md-on-surface` / `--md-on-surface-variant` |
| `--studio-success / warning / danger` | `#4ade80` / `#facc15` / `#f87171` |

## 4. Toolbar (new, 40px)

`[breadcrumb: project name › panel label] · spacer · [search "Search shots, commands…  ⌘K", width 280] · [undo, redo] · [Share, ?]`

## 5. Status Bar (new, 28px)

- **Left:** `PHASE n · <phase>` pill (from `activeProject.current_phase`), gate,
  budget.
- **Centre:** worker / mem / fps.
- **Right:** zoom · selection · frame · version.

**Data-honesty rule:** render only values the store actually has; omit or show
an em-dash otherwise. Never fabricate telemetry as if it were live.

## 6. Sidebar restructure

1. **Remove** the `Engine Status` telemetry block (moves to Status Bar).
2. **Add** `SidebarFooter`: primary “New Project” CTA + `Docs · Shortcuts · v{version}`.
3. **Add** keyboard-shortcut chips to nav rows:
   `P` Preview · `T` Timeline · `A` Asset Manifest · `I` Props ·
   `R` Render · `M` Monitor · `Q` Review · `G` Agnes AI.
4. **Keep** `fetchProjects` boot + `loading`/`error` surfacing
   (pinned by `tests/test_web_shell_boot.py`).

## 7. Screen deltas (01–04)

| # | Screen | Delta |
|---|---|---|
| 01 | Preview Player | transport becomes an **overlay** on the frame; **ClipInspector rail (300px)**; timeline **206px** with V2/V1/A1 |
| 02 | Shot List | Shot Inspector **tabs** (Overview/Prompt/Gate); row **checkboxes** + **Selection Bar** |
| 03 | Render Queue | **PipelineStepper** (Plan locked → Rendering → Encode → Publish); settings column fixed **440px** |
| 04 | Monitor | **PhaseStepper** (P R I D E S) |

## 8. Verification gates

| Gate | Command |
|---|---|
| Source contract | `python -m pytest tests/test_web_studio_shell.py -v` |
| Existing SPA contracts | `python -m pytest tests/test_web_panels_wired.py tests/test_web_shell_boot.py tests/test_web.py -v` |
| Frontend lint | `npm --prefix web run lint` |
| Frontend build | `npm --prefix web run build` (emits into `src/brandly_cli/web/static`) |
| Bundle freshness | `git diff --exit-code -- src/brandly_cli/web/static/` (CI `web-quality`) |
| Python suite | `python -m pytest tests/ -q` |
