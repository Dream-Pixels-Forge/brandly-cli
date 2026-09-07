# IMPLEMENTATION PLAN — brandly-cli v0.3.0

> **Project:** brandly-cli  
> **Version Target:** 0.3.0  
> **Date:** 2026-09-07  
> **Method:** Subagent-driven development + Test-driven development

---

## Pipeline Phase

**Current:** Phase 3 (Engineer) — Feature Implementation  
**Approach:** TDD (RED → GREEN → REFACTOR) + Subagent Parallel Execution

---

## Feature List (Ranked by Impact)

### Phase 3A — Core Pipeline Completion (P0)
| # | Feature | Module | CLI Command | Priority |
|---|---------|--------|-------------|----------|
| 1 | stitch | `stitch.py` | `brandly stitch` | 🔴 P0 |
| 2 | platform exports | `export_platforms.py` | `brandly export --platforms` | 🔴 P0 |
| 3 | thumbnails | `thumbnails.py` | `brandly thumbnail` | 🔴 P0 |

### Phase 3B — Quality Enhancements (P1)
| # | Feature | Module | CLI Command | Priority |
|---|---------|--------|-------------|----------|
| 4 | voice-match (dubbing) | `dubbing.py` | `brandly voice-match` | 🟡 P1 |
| 5 | beat-sync | `beat_sync.py` | `brandly beat-sync` | 🟡 P1 |
| 6 | auto-direct | `autodirector.py` | `brandly autodirect` | 🟡 P1 |
| 7 | trend research | `trends.py` | `brandly trend` | 🟡 P1 |

### Phase 3C — Developer Features (P2)
| # | Feature | Module | CLI Command | Priority |
|---|---------|--------|-------------|----------|
| 8 | analyze | `analyzer.py` | `brandly analyze` | 🟢 P2 |
| 9 | templates | `templates.py` | `brandly init --template` | 🟢 P2 |
| 10 | batch | `batch.py` (enhance) | `brandly batch` | 🟢 P2 |
| 11 | webhook | `webhook.py` | `brandly webhook` | 🟢 P2 |

### Phase 3D — Ecosystem (P3)
| # | Feature | Module | CLI Command | Priority |
|---|---------|--------|-------------|----------|
| 12 | share | `sharing.py` | `brandly share` | 🟣 P3 |
| 13 | team | `team.py` | `brandly team` | 🟣 P3 |
| 14 | plugin | `plugin_system.py` | `brandly plugin` | 🟣 P3 |

---

## Implementation Discipline

### Test-Driven Development (TDD) Cycle
```
1. RED: Write failing test first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up, add type hints, optimize
```

### Subagent Delegation Pattern
- Each feature gets its own subagent
- Subagents receive: feature spec, existing module patterns, test expectations
- Subagents return: implementation + tests + docs
- Orchestrator validates: tests pass, lint clean, CLI smoke test works

### Verification Gate Per Feature
| Gate | Command |
|------|---------|
| Unit tests | `pytest tests/test_<feature>.py -v` |
| Lint | `ruff check src/brandly_cli/<feature>.py` |
| Type check | `python -m py_compile src/brandly_cli/<feature>.py` |
| CLI smoke | `brandly <command> --help` |
| Integration | `brandly <command> <args>` |

---

## File Structure Changes

```
src/brandly_cli/
├── stitch.py              # NEW: multi-shot assembly
├── export_platforms.py    # NEW: platform-specific exports
├── thumbnails.py          # NEW: thumbnail generation
├── dubbing.py             # NEW: multi-language voice matching
├── beat_sync.py           # NEW: music-reactive editing
├── autodirector.py        # NEW: script-to-video pipeline
├── trends.py              # NEW: trend research
├── analyzer.py            # NEW: performance prediction
├── templates.py           # NEW: project templates
├── batch.py               # ENHANCED: A/B variant generation
├── webhook.py             # NEW: CI/CD webhook server
├── sharing.py             # NEW: cloud upload
├── team.py                # NEW: multi-user support
└── plugin_system.py       # NEW: plugin discovery

tests/
├── test_stitch.py         # NEW
├── test_export_platforms.py  # NEW
├── test_thumbnails.py     # NEW
├── test_dubbing.py        # NEW
├── test_beat_sync.py      # NEW
├── test_autodirector.py   # NEW
├── test_trends.py         # NEW
├── test_analyzer.py       # NEW
├── test_templates.py      # NEW
├── test_batch.py          # NEW (enhanced)
├── test_webhook.py        # NEW
├── test_sharing.py        # NEW
├── test_team.py           # NEW
└── test_plugin_system.py  # NEW
```

---

## Subagent Delegation Map

| Subagent | Features | Dependencies |
|----------|----------|--------------|
| `stitch-subagent` | #1 stitch | edit.py (existing) |
| `export-subagent` | #2 platform exports | export.py (existing) |
| `thumbnail-subagent` | #3 thumbnails | edit.py, video_prompts.py |
| `dubbing-subagent` | #4 voice-match | audio_client.py, edit.py |
| `beat-sync-subagent` | #5 beat-sync | edit.py, audio_client.py |
| `autodirector-subagent` | #6 auto-direct | director.py, all clients |
| `trend-subagent` | #7 trend research | types.py, constants.py |
| `analyzer-subagent` | #8 analyze | edit.py, video_prompts.py |
| `template-subagent` | #9 templates | project_manager.py |
| `batch-subagent` | #10 batch | video_prompts.py, edit.py |
| `webhook-subagent` | #11 webhook | cli.py, project_manager.py |
| `sharing-subagent` | #12 share | utils.py, edit.py |
| `team-subagent` | #13 team | project_manager.py, types.py |
| `plugin-subagent` | #14 plugin | cli.py, sync.py |

---

## Version Bump Schedule

| Milestone | Version | Changes |
|-----------|---------|---------|
| Phase 3A complete | 0.3.0-alpha | stitch + export + thumbnails |
| Phase 3B complete | 0.3.0-beta | + dubbing + beat-sync + auto-direct |
| Phase 3C complete | 0.3.0-rc | + analyze + templates + batch + webhook |
| Phase 3D complete | 0.3.0 | + share + team + plugin |
| Final release | 0.3.0 | All features, docs, changelog |

---

## Success Criteria

- [ ] 14 new modules implemented
- [ ] 14+ new test files (target: 300+ total tests)
- [ ] All tests passing (`pytest tests/ -v`)
- [ ] Zero lint errors (`ruff check src/`)
- [ ] CLI smoke tests pass for all new commands
- [ ] Documentation updated (README, SPEC.md)
- [ ] Version bumped to 0.3.0

---

*Plan approved. Starting Phase 3 implementation with subagent delegation.*
