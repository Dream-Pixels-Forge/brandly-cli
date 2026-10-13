# PR checklist — brandly-cli

> **Merge condition (non-negotiable):** every CI check green, zero lint
> warnings, no unresolved review threads. Never merge without review.

## Issues closed

<!-- One `Closes` line per issue. A squash-merge only auto-closes the FIRST
     linked issue — remaining issues MUST be closed manually with fix
     evidence after merge (see Round 31: PR #316 closed #309 only;
     #310–#315 needed manual closeout). Never rely on a single
     "Closes #a, #b, #c" line. -->

- Closes #
- Closes #

## Gates (all green or the PR is not done)

- [ ] Full suite: `python -m pytest tests/ -q` (report passed/skipped)
- [ ] `ruff check src/ tests/` clean
- [ ] `npm --prefix web run lint` — 0 warnings / 0 errors (if web touched)
- [ ] `npm --prefix web run build` + bundle freshness (if web touched)
- [ ] `python scripts/version_check.py` (if releasing)

## Post-merge (for multi-issue PRs)

- [ ] Verified every linked issue actually closed (not just the first)
- [ ] Manually closed leftovers with fix location + test evidence
