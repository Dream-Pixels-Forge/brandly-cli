# Subgoals — v0.14.8 Autonomous Execution Framework

**Status:** ✅ Complete  
**Version:** v0.14.8  
**Prerequisite:** v0.14.7

---

## Overview

Integrate all completed components (audio, video, spatial, post-production) into an executable autonomous pipeline framework. This enables `brandly run --execute` to autonomously walk the pipeline.

---

## Problem Statement

Individual components are complete, but the pipeline cannot execute autonomously. Need:
1. Unified execution interface
2. Cost tracking across providers
3. Approval gate escalation
4. Memory query integration

---

## Subgoals

### 7.1 Pipeline Execution Interface
**Status:** ✅ Complete

Create unified execution interface for `brandly run --execute`.

**Acceptance Criteria:**
- [x] `brandly run --execute --plan plan.json` executes full pipeline
- [x] Phases execute in order: trends → concept → bible → casting → screenplay → script → asset → audio → re_edit → validate → publish
- [x] Each phase can be resumbed on failure
- [x] Progress tracked in `.brandly/<project>/progress.json`

**Test Plan:**
- Run execute on fresh project
- Verify phase completion tracking

---

### 7.2 Cost Aggregation
**Status:** ✅ Complete

Aggregate cost tracking across all providers (video, audio, spatial).

**Acceptance Criteria:**
- [x] Cost tracked per provider in `cost.json`
- [x] Credits spent and API calls tracked
- [x] Provider selection logs cost implications
- [x] Cost alerts when threshold exceeded

**Test Plan:**
- Run multi-provider pipeline
- Verify cost aggregation

---

### 7.3 Approval Gate Escalation
**Status:** ✅ Complete

On gate failure, escalate via `approve` instead of silent failure.

**Acceptance Criteria:**
- [x] Gate failure sends `approve` request
- [x] Approval tracked in project state
- [x] Re-run after approval continues from failure point
- [x] Reject creates review note with feedback

**Test Plan:**
- Force gate failure
- Verify `approve` escalation

---

### 7.4 Memory Query Integration
**Status:** ✅ Complete

Agents can query project memory for context.

**Acceptance Criteria:**
- [x] `memory` tool accepts queries
- [x] Returns reference paths for named items
- [x] Vector search capability optional but implemented

**Test Plan:**
- Query for character by name
- Verify correct reference plate

---

### 7.5 Plan JSON Executor
**Status:** ✅ Complete

Read plan and execute phases with proper handoffs.

**Acceptance Criteria:**
- [x] `plan --json` lists all phase contracts
- [x] Execute reads and processes each phase
- [x] Phase handoffs explicit (inputs/outputs)
- [x] Gate failures trigger `approve` escalation

**Test Plan:**
- Generate plan JSON
- Run execute on fresh project
- Verify full end-to-end

---

## Implementation Order (TDD)

1. **Write tests** for pipeline execution
2. **Implement execution interface**
3. **Add cost aggregation**
4. **Add gate escalation**
5. **Implement memory query**

---

## Dependencies

- All previous phase implementations (v0.14.3 - v0.14.7)
- Project memory system
- Approval workflow (`brandly-film-collaborator` skill)

---

## Related Skills

- `brandly-init` - project initialization
- `brandly-consistency` - memory queries
- `brandly-film-collaborator` - approval workflow
- `brandly-video-generation` - shot generation
- `brandly-audio` - sound design