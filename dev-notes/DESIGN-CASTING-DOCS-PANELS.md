# DESIGN — Casting & Project Docs panels

> **Status:** Ratified 2026-10-19. Extends the frozen shell spec
> (`DESIGN-STUDIO-SHELL.md`) with two new screens. Implements the user
> request: "casting display image of cast and sheet and docs display all
> documents generated".
> All §3 token aliases and §5 data-honesty rules of the frozen spec apply
> unchanged. No new token namespace.

## 1. Scope

**In scope**
- Two new sidebar panels: **Casting** (`casting`) and **Project Docs** (`docs`).
- Four read-only API endpoints backing them (list + media/content serving).
- Sidebar nav entries + keyboard chips for both panels.

**Out of scope — do NOT build**
- Any write path (upload/delete/regenerate). These panels are viewers.
- Non-image cast categories (prop/location/vehicle/…) — those belong to
  the existing Asset Manifest / story surfaces.

## 2. Data sources (on-disk truth)

| Panel | Source (v2 layout) | Legacy fallback |
|---|---|---|
| Casting | `pre-production/<id>/{character,wardrobe}/*.png\|jpg\|jpeg\|webp` via `layout.resolve_media_root(root, id, "images")` | `.brandly/<id>/images/{character,wardrobe}/` |
| Docs | `.brandly/<id>/docs/**` via `layout.discover_docs(proj_dir)` | — |

`hq/` archives are excluded from Casting. Documents include every
category `discover_docs` returns (`plan`, `bible`, `storyboard`,
`screenplay`, `general`, `tmp`) — "all documents generated" means all of
them; `tmp` is labelled **Working** in the UI, never hidden.

## 3. API (read-only)

| Endpoint | Returns |
|---|---|
| `GET /api/projects/{id}/cast` | `{project_id, items:[{category, filename, size_bytes, modified}]}` sorted by category then filename |
| `GET /api/projects/{id}/cast/media/{category}/{filename}` | `FileResponse` (image bytes) |
| `GET /api/projects/{id}/docs` | `{project_id, items:[{path, category, filename, size_bytes, modified}]}` sorted by category then path |
| `GET /api/projects/{id}/docs/content?path=<rel>` | `{path, category, filename, size_bytes, truncated, content}` — UTF-8 text, capped at 1 MiB, `truncated` flag honest |

**Path safety (mandatory):**
- `category` must be in `{character, wardrobe}` (whitelist, not prefix match).
- `filename` must match `^[A-Za-z0-9][A-Za-z0-9._-]*$` (no separators).
- Docs `path` is a relative path resolved with `security.safe_join` against
  the project's `docs/` dir; escape ⇒ 404. File must exist ⇒ 404 otherwise.
- All four endpoints sit under `/api` ⇒ guarded by `LocalGuardMiddleware`
  (token via query param, matching the review media pattern).

Unknown project ⇒ 404 (same as existing routes). Empty folders ⇒ `items: []`
(the UI shows the empty state; the API never invents entries).

## 4. Screens

### 4.1 Casting (nav icon `theater_comedy`, chip `B`)

- Grouped plate grid: section **Characters** (category `character`) then
  **Wardrobe** (category `wardrobe`); each section omitted when empty.
- Cards: image plate (`object-fit: cover`, 4:3, radius `--md-radius-md`,
  background `--md-surface-container-low`), caption = filename in
  `--md-font-code-inline`, sub-line = size + modified (real values from the
  API, em-dash when absent).
- Grid: `repeat(auto-fill, minmax(180px, 1fr))`, gap 12.
- Click a card → lightbox-style enlarged view inside the panel (same data,
  `object-fit: contain`), close on second click / Esc. No new route.
- **Empty state (data honesty):** centered muted text
  `No cast images yet — generate character sheets to populate casting.`
  No placeholder plates, no fabricated names.

### 4.2 Project Docs (nav icon `description`, chip `D`)

- Two-zone layout: **300px left rail** (grouped doc list, matching the
  frozen "300px detail rail" language) + **content viewer** (`flex:1`).
- Rail groups: Plan, Bible, Storyboard, Screenplay, General, Working (tmp).
  Group header = category label, uppercase, muted. Rows: filename +
  size (human-readable). Active row highlighted with `--md-primary`.
- Viewer: document text in a scrollable `<pre>` (`--md-font-code-inline`,
  12.5px, `--md-surface-container-lowest` background); header bar shows
  the relative path + real size/modified. Truncated files show an honest
  `showing first 1 MiB` chip.
- **Empty state:** `No documents yet — run the plan/bible/storyboard
  phases to generate project documents.` No file selected ⇒
  `Select a document to view it.` (mirrors preview-stage "nothing
  selected" pattern).

## 5. Wiring contract

- `PanelKind` gains `'casting' | 'docs'` (`web/src/types.ts`).
- `PANEL_LABELS`: `casting: 'Casting'`, `docs: 'Project Docs'`;
  `PANEL_SHORTCUTS`: `casting: 'B'`, `docs: 'D'` (no collisions with
  P/T/A/I/C/S/R/M/Q/G).
- `SidebarNav` registers both rows (icons per §4).
- `Shell` maps both kinds to `CastingPanel` / `DocsPanel`.
- Components fetch on mount + on project change via `withToken()`
  (same pattern as `ReviewQueuePanel`); abortable, loading + error
  surfaces, no polling (files change only during generation runs).

## 6. Verification gates

Same six gates as the frozen spec, plus the new source-contract test
`tests/test_web_casting_docs_panels.py` (RED first) covering: PanelKind
registration, labels/shortcuts, nav + Shell wiring, backend endpoints,
path-safety refusals, and data-honesty empty states.
