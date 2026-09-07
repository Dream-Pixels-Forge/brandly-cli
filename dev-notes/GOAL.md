# GOAL — brandly-cli Alignment & Full Functionality

> **Project:** brandly-cli  
> **Category:** `Dev/cli/brandly-cli`  
> **Started:** 2026-09-07  
> **Phase:** Phase 0 (Bootstrap) → Phase 2 (Governance)  
> **Status:** In Progress

---

## 1. Objective

Make brandly-cli **fully functional** and **aligned with DPF standards**:

1. Fix all test failures (✅ completed — 170/170 passing)
2. Establish pipeline governance via dev-notes/ artifacts
3. Add missing CI/CD, env documentation, and development tooling
4. Verify end-to-end CLI workflow (init → run → approve → export)

---

## 2. Verification Gates

| # | Gate | Command | Status |
|---|------|---------|--------|
| 1 | Unit tests | `pytest tests/ -v` | ✅ PASS (170/170) |
| 2 | Linting | `ruff check src/` | ✅ PASS |
| 3 | Syntax | `python -m py_compile src/brandly_cli/*.py` | ✅ PASS |
| 4 | CLI help | `brandly --help` | ✅ PASS |
| 5 | Config display | `brandly config` | ✅ PASS |
| 6 | Cost estimate | `brandly estimate --style cinematic --shots 5` | ✅ PASS |
| 7 | Project init | `brandly init --name "Test" --idea "x" --style cinematic` | ✅ PASS |
| 8 | Pipeline flow | `brandly run <id> && brandly approve <id> init` | ✅ PASS |
| 9 | Export | `brandly export <id>` | ✅ PASS |
| 10 | Director prompt | `brandly director` | ✅ PASS |
| 11 | Prompt builder | `brandly prompt --subject "x" --action "y" --environment "z" --shots 3` | ✅ PASS |
| 12 | Cost graceful fallback | `brandly cost <id>` when no cost.json exists | ✅ PASS |
| 13 | Models list | `brandly models` | ✅ PASS |
| 14 | Memory view | `brandly memory view` | ✅ PASS |
| 15 | CI/CD | `.github/workflows/ci.yml` exists | ✅ PASS |
| 16 | .env.example | `.env.example` documents all required vars | ✅ PASS |

---

## 3. Changes Made This Session

### 3.1 Fixed Path Resolution Bug in `utils.py`
- Added `root: Path | None = None` parameter to:
  - `write_generation_plan()`
  - `write_generation_doc()`
  - `_update_plans()`
  - `detect_project_artifacts()`
- Updated all call sites in `cli.py` to pass `root=_get_root(ctx)`
- **Root cause:** Functions used `Path(f".brandly/projects/{id}")` resolving to cwd instead of the configured root directory

### 3.2 Test Results
- **Before fix:** 166 passed, 4 failed
- **After fix:** 170 passed, 0 failed

---

## 4. Remaining Work

### 4.1 High Priority
- [x] Create `.github/workflows/ci.yml` (copy from DPF template)
- [x] Create `.env.example`
- [x] Run end-to-end pipeline test (init → run → approve → export)
- [x] Create `dev-notes/PROGRESS.md`
- [x] Fix `brandly cost` graceful fallback for missing cost state

### 4.2 Medium Priority
- [x] Bump version to 0.2.0
- [x] Add pre-commit hooks (ruff + pytest)
- [x] Add Makefile for common tasks

### 4.3 Nice to Have
- [x] Add `brandly models` output verification
- [x] Test sync command with mock tool configs
- [x] Document skill reference system in README
- [x] Add SECURITY.md (low-risk assessment)
- [x] Add SPEC.md (architecture specification)

---

## 5. Technical Debt

| ID | Description | Priority | Status |
|----|-------------|----------|--------|
| DPF-BC-001 | No CI/CD pipeline | Medium | ✅ Resolved |
| DPF-BC-002 | No .env.example | Low | ✅ Resolved |
| DPF-BC-003 | Path resolution bug | Medium | ✅ Resolved |
| DPF-BC-004 | `brandly cost` unhandled crash | Low | ✅ Resolved |
| DPF-BC-005 | No pre-commit hooks | Low | ✅ Resolved |
| DPF-BC-006 | No Makefile/justfile | Low | ✅ Resolved |
| DPF-BC-007 | Version not bumped to 0.2.0 | Low | ✅ Resolved |

---

## 6. Notes

- brandly-cli is a **Python** project using `hatchling` build system
- No TypeScript/JS involved — TanStack ecosystem not applicable
- The `package/` directory contains a separate Node.js binary wrapper for BytePlus Ark CLI — this is a third-party tool, not brandly-cli itself
- All API clients use async httpx with exponential backoff retry

---

*Goal achieved: brandly-cli is fully functional with 170/170 tests passing, CI/CD in place, and all verification gates green.*
