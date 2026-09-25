# DECISION — G6 publish path in scope for v0.4 (DEV-G6-001)

> **Date:** 2026-09-25 · **Status:** DECIDED · **Gates:** G6 anti-drift rules
> (one platform at a time; no live-by-default; no secrets in `.env` — F2).

## Decision

**Yes** — build the dry-run-first publish path now, per the G6 decision gate
(`GOAL-AGENTIC-PIPELINE.md` §Goal 6). The last mile (export → post) is the
audit's stated gap for creators/marketers (F9); a dry-run path is
credential-safe and reversible, so it can ship without the external-account
commitment live posting implies.

## Platform set (start with 1–2, one at a time)

1. **YouTube** — first adapter in this PR: documented upload API
   (`youtube/v3/videos`), supports private + `publishAt` scheduling. Live
   upload is implemented but only runs behind an explicitly stored
   credential; the e2e dry-run test proves payload correctness without
   network.
2. **TikTok** — follow-up PR on the same `Adapter` interface.
3. **Instagram/Shorts** — later; no scheduler service, no UI (anti-drift).

## Bounds

- **Dry-run is the safe mode.** `--dry-run` renders the exact request
  payload and never touches the network; with no stored credential a live
  request **fails closed** (non-zero exit, actionable message) — live
  posting is never the default.
- **Credentials via `brandly config set <platform> <token>`** into the user
  config dir (`~/.brandly/credentials.json`); no keys in `.env` (the F2
  failure mode) and none in project artifacts (CI tree-scan test).
- **Capability matrix stays honest:** `publish_schedule` = `partial`
  (dry-run implemented; live YouTube pending credential proof; TikTok/IG
  adapters not built). The G5 guard keeps README claims in sync.

## Reversal

Revoking this decision reverts the publish command/adapter (one PR's worth
of code: `publish.py`, `cmd/publish.py`, `config_store.py`, tests) and
restores the capability row to `absent`. Nothing else depends on it.
