# Subgoals — v0.15.7 Working Team Invitations

**Status:** Frozen design — implement after this spec is ratified  
**Version:** v0.15.7 (minor: one broken feature made real)  
**Base:** brandly-cli 0.15.6  
**Closes:** the `team.py` / `cmd/team.py` invitation stubs — the last two
no-op actions in the codebase.

**Design authority:** this file (freeze before code). No code without RED→GREEN
tests.

---

## Problem

`brandly team` has a broken round trip:

1. `brandly team invite <team_id> <email>` prints **"✓ Invitation sent"** —
   but `invite_to_team()` never persists the invitation. It is a phantom: it
   cannot be listed, loaded, or accepted. Nothing was sent either.
2. `brandly team accept <invitation_id>` prints **"Note: Invitation acceptance
   is a stub implementation"** and **"Would accept invitation …"**. It performs
   no action and still exits **0** — a false success.
3. `accept_invitation()` in `team.py` unconditionally returns `None`.

Both commands are therefore no-ops that report success. This violates the repo
rule "never fabricate telemetry or wire no-op actions" (AGENTS.md §0.5) and
"never fabricate data in the UI".

## Design

### Storage

- **Path:** `.brandly/teams/invitations/<invitation_id>.json`.
- **Why a sub-directory:** `list_teams_for_user()` globs `*.json` in
  `.brandly/teams/` (non-recursive). Keeping invitations in
  `invitations/` guarantees an invitation is never mistaken for a team.
- **Format:** the existing `TeamInvitation` model, JSON — the same shape
  `Team` uses, so `to_dict()` / `from_dict()` round-trip unchanged.

### New functions (`team.py`)

| Function | Behaviour |
|---|---|
| `save_invitation(invitation, root)` | Write the invitation JSON; return its path. |
| `load_invitation(invitation_id, root)` | Load + parse; return `None` if absent or unreadable. |

### `invite_to_team()` — persist

After building the `TeamInvitation`, write it to disk before returning it. The
returned object is unchanged (same fields, same ids) — only persistence is
new.

### `accept_invitation()` — implement

Signature stays `(invitation_id, user_id, username, root) -> Team`. It now
**raises `ValueError`** for every invalid state (matching `invite_to_team()`,
which already raises `ValueError` / `PermissionError`) and **returns the
`Team`** on success:

1. Load the invitation — not found → `ValueError("Invitation not found: <id>")`.
2. Already accepted → `ValueError("Invitation already accepted")`.
3. Expired (`expires_at` in the past) → `ValueError("Invitation expired")`.
4. Load the team — missing → `ValueError("Team not found: <id>")`.
5. Add the member with the **invitation's role** and **email**.
6. Mark the invitation `is_accepted = True`; persist the invitation and the
   team.
7. Return the updated team.

Expiry is checked against `expires_at` when it is set; an invitation with no
expiry never expires.

### CLI

- **`brandly team invite`** — replace the false claim **"✓ Invitation sent"**
  with **"✓ Invitation created"**. No mail service is wired, so nothing is
  sent; the command says what actually happened and prints the invitation id
  for the owner to share. The accept command line is already printed.
- **`brandly team accept`** — really accepts. On success it prints the team
  name, the role granted and the team id, and exits 0. On any `ValueError` it
  prints the reason and exits **1** (never a false success).

## Tests (RED→GREEN)

`tests/test_team_invitations.py`:
- The invitation is persisted and round-trips through `load_invitation`.
- `load_invitation` returns `None` for an unknown id.
- Accepting adds the member with the invitation's role **and** email.
- Accepting marks the invitation accepted and persists that.
- Accepting raises for: unknown id, already-accepted, expired, missing team.
- An invitation is never picked up by `list_teams_for_user` (the `*.json` glob
  guard).
- CLI: `team accept` adds the member and exits 0.
- CLI: `team accept` with an unknown id exits 1 with an error message.
- CLI: `team invite` says "created", never "sent".

## Explicit non-goals

- **No email delivery.** The invitation is created on disk; sending it is the
  owner's job (the id is printed). The CLI no longer claims to send anything.
- **No invitation listing command** in v0.15.7 — the id is printed at
  creation and printed again on accept.
- **No revocation and no expiry sweep.** Expired invitations are rejected at
  accept time; they are not garbage-collected.
- **No invitation store outside `.brandly/teams/`** — one root, one place.

## Gates

Full suite green, `ruff check src/ tests/` clean, `mypy src/` clean (PIL
`import-untyped` findings are a pre-existing local-environment artifact), web
lint + bundle freshness unchanged.
