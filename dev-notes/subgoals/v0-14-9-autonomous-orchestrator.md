# Subgoals — v0.14.9 Autonomous Orchestrator

**Status:** Complete  
**Version:** v0.14.9  
**Prerequisite:** v0.14.4 - v0.14.8

---

## Overview

Enable `brandly run --execute` to autonomously walk the entire pipeline: trends → concept → bible → casting → screenplay → script → asset → audio → re_edit → validate → publish

---

## Problem Statement

Current pipeline requires manual phase stepping and approvals. Need autonomous orchestration that:
1. Reads plan JSON and dispatches phase workers
2. Escalates on gate failures via `approve`
3. Queries shared memory for context

---

## Subgoals

### 6.1 Pipeline Phase Workers
**Status:** Complete

Implement worker functions for each phase.

**Acceptance Criteria:**
- [x] `worker_trends(project_id)` - research video formats and platform algorithms
- [x] `worker_concept(project_id)` - derive creative concept from trends
- [x] `worker_bible(project_id)` - create production bible with characters/worlds
- [x] `worker_casting(project_id)` - generate character sheets via cast_characters
- [x] `worker_script(project_id)` - write comprehensive shots.json for all scenes
- [x] `worker_asset(project_id)` - generate video shots via produce_shots
- [x] `worker_audio(project_id)` - generate soundtrack via sound_design
- [x] `worker_reedit(project_id)` - mix music into cut via stitch
- [x] `worker_validate(project_id)` - score for virality and engagement
- [x] `worker_publish(project_id)` - export and schedule via export_platforms

**Test Plan:**
- Test each worker in isolation with mocked MCP calls
- Test worker dispatch through plan executor
- Verify error handling and retries

---

### 6.2 Plan JSON Executor
**Status:** Complete

Read plan and execute phases in order.

**Acceptance Criteria:**
- [x] `plan --json` lists all phase contracts with inputs/outputs
- [x] Execute reads and processes each phase sequentially
- [x] Phase handoffs explicit with data validation
- [x] Gate failures trigger `approve` escalation
- [x] Progress persisted to `.brandly/<project>/progress.json`

**Test Plan:**
- Generate plan JSON from template
- Run execute on fresh project
- Verify full end-to-end phase execution
- Test resume from failure point

---

### 6.3 Human Gate Escalation
**Status:** Complete

On failure, escalate via `approve` instead of silent failure.

**Acceptance Criteria:**
- [x] Gate failure sends approve request with context
- [x] Approval tracked in project state (progress.json)
- [x] Re-run after approval continues from failure point
- [x] Reject creates review note with feedback

**Test Plan:**
- Force gate failure in mock environment
- Verify `approve` escalation with context
- Test approval flow and state preservation

---

### 6.4 Shared Memory Query
**Status:** Complete ✓

Agents can query project memory for context.

**Acceptance Criteria:**
- [x] `memory` tool accepts queries for characters, locations, themes
- [x] Returns reference paths for named items
- [x] Vector search capability for semantic similarity

**Test Plan:**
- Query for character by name during worker execution
- Verify correct reference plate returned
- Test memory update after phase completion

---

## Implementation Order (TDD)

1. [x] **Write tests** for pipeline execution and worker dispatch
2. [x] **Implement worker_trends** - research phase with mock data source
3. [x] **Implement worker_concept** - creative direction from trends
4. [x] **Implement worker_bible** - production documentation
5. [x] **Implement worker_casting** - character generation via cast_characters
6. [x] **Implement worker_script** - comprehensive shots.json writer
7. [x] **Implement worker_asset** - video generation via produce_shots
8. [x] **Implement worker_audio** - soundtrack via sound_design
9. [x] **Implement worker_reedit** - post-production mix via stitch
10. [x] **Implement worker_validate** - virality scoring
11. [x] **Implement worker_publish** - platform exports
12. [x] **Create plan executor** - dispatch workers sequentially
13. [x] **Add gate escalation** - integrate with approve MCP tool
14. [x] **Implement memory query** - context-aware workers

---

## Dependencies

- All previous phase implementations (v0.14.3 - v0.14.8) complete
- Project memory system integrated
- Approval workflow via `brandly-film-collaborator` skill
- MCP tools: produce, produce_shots, cast_characters, sound_design, stitch, export_platforms, approve, memory

---

## Related Skills

- `brandly-init` - project initialization
- `brandly-consistency` - memory queries
- `brandly-film-collaborator` - approval workflow
- `brandly-video-generation` - shot generation
- `brandly-camera` - camera language for spatial blocking

---

## Technical Design

### Phase Worker Interface

Each worker follows a consistent pattern:
```python
def worker_phase(project_id: str, **kwargs) -> PhaseResult:
    """
    Execute a single production phase.
    
    Args:
        project_id: Unique identifier for the project
        **kwargs: Phase-specific parameters
        
    Returns:
        PhaseResult: status, outputs, and any errors
    """
    try:
        # 1. Retrieve context from memory if needed
        # 2. Execute phase-specific logic
        # 3. Update progress.json
        # 4. Return PhaseResult
        
    except Exception as e:
        # Escalate via approve on gate failure
        raise GateEscalation(e)
```

### Phase Order Execution

```python
PHASE_ORDER = ["init", "trends", "concept", "bible", "casting", 
               "screenplay", "script", "asset", "audio", 
               "re_edit", "validate", "publish", "done"]
```

### Plan JSON Structure

```json
{
  "version": "0.14.9",
  "phases": {
    "trends": {"enabled": true, "params": {}},
    "concept": {"enabled": true, "params": {}},
    "bible": {"enabled": true, "params": {}},
    "casting": {"enabled": true, "params": {}},
    "script": {"enabled": true, "params": {}},
    "asset": {"enabled": true, "params": {}},
    "audio": {"enabled": true, "params": {}},
    "re_edit": {"enabled": true, "params": {}},
    "validate": {"enabled": true, "params": {}},
    "publish": {"enabled": true, "params": {}}
  },
  "gate_mode": "auto-approve|human-required|review-all",
  "providers": ["AgnesVideoBackend", "ArkVideoBackend"]
}
```

### Progress Tracking

`.brandly/<project>/progress.json`:
```json
{
  "current_phase": "asset",
  "completed_phases": ["trends", "concept", "bible", "casting", "script"],
  "phase_results": {
    "trends": {"status": "completed", "timestamp": "..."},
    "concept": {"status": "completed", "timestamp": "..."}
  },
  "gate_decisions": {
    "asset": {"awaiting": "user", "reason": "low virality score"}
  }
}
```