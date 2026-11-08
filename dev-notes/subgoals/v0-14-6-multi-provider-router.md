# Subgoals — v0.14.6 Multi-Provider Router

**Status:** ✅ Complete  
**Version:** v0.14.6  
**Prerequisite:** v0.14.4 (VideoBackend protocol)

---

## Overview

Implement automatic failover across multiple video generation providers (Agnes, Ark, Kling, Seedance) with cost tracking.

---

## Problem Statement

Currently only Agnes is supported. Single-provider outage blocks entire pipelines. Need:
1. Provider abstraction layer
2. Automatic failover
3. Cost tracking per provider
4. Quota-aware routing

---

## Subgoals

### 4.1 VideoBackend Protocol
**Status:** ✅ Complete (from v0.14.4)

Abstract video providers behind a common interface.

**Acceptance Criteria:**
- [x] `VideoBackend` protocol defined with `capabilities()`, `submit()`, `poll()`, `fetch()`
- [x] `VideoBackendCapabilities` dataclass with max_duration, rate limits, modes
- [x] `VideoTaskResult` with duration truth fields
- [x] `AgnesVideoBackend` implements protocol

**Test Plan:**
- Protocol compliance tests
- Mock backend for testing

---

### 4.2 Ark Video Backend
**Status:** ✅ Complete (NEW PROVIDER)

Add Ark.ai as fallback provider.

**Acceptance Criteria:**
- [x] `ArkVideoBackend` implements `VideoBackend`
- [x] Supports same modes as Agnes (text, keyframe, reference)
- [x] Correct capability descriptors

**Test Plan:**
- Mock Ark API responses
- Verify failover from Agnes to Ark

---

### 4.3 Seedance Video Backend
**Status:** ✅ Complete (NEW PROVIDER)

Add Seedance.ai as second fallback.

**Acceptance Criteria:**
- [x] `SeedanceVideoBackend` implements `VideoBackend`
- [x] Supports video modes
- [x] Correct capability descriptors

**Test Plan:**
- Mock Seedance API
- Verify provider selection

---

### 4.4 ProviderRouter Implementation
**Status:** ✅ Complete (NEW CLASS)

Automatic failover router with cost tracking.

**Acceptance Criteria:**
- [x] Tries backends in priority order
- [x] Falls back on transient error, rate limit, outage
- [x] Tracks cost per backend
- [x] Returns intersection of capabilities

**Test Plan:**
- Test failover scenarios
- Verify cost tracking

---

### 4.5 shot_runner Integration
**Status:** ✅ Complete (REFACTOR)

Use ProviderRouter in shot generation.

**Acceptance Criteria:**
- [x] `shot_runner` accepts `video_backend` parameter
- [x] Default to `ProviderRouter` with Agnes primary
- [x] Cost tracking integrated

**Test Plan:**
- Run shot with failover scenario

---

## Implementation Order (TDD)

1. **Complete VideoBackend protocol** (finish v0.14.4)
2. **Write tests** for router failover logic
3. **Implement ProviderRouter class**
4. **Add ArkVideoBackend**
5. **Add SeedanceVideoBackend**
6. **Integrate into shot_runner**

---

## Dependencies

- Ark API credentials
- Seedance API credentials
- Provider API documentation

---

## Related Skills

- `brandly-video-generation` - video generation
- `brandly-camera` - camera language
- `brandly-consistency` - reference handling

---

## Cost Tracking Schema

```json
{
  "providers": {
    "AgnesVideoBackend": {"credits_spent": 45.0, "api_calls": 15},
    "ArkVideoBackend": {"credits_spent": 20.0, "api_calls": 10},
    "SeedanceVideoBackend": {"credits_spent": 0.0, "api_calls": 0}
  }
}
```