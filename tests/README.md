# tests

## Overview
pytest source-contract tests for CLI and web SPA.

## Interface
- test_web_*.py: web contract tests
- test_agent_*.py: agent surface tests
- test_*_client.py: provider client tests

## Invariants
- All tests must pass with `python -m pytest tests/ -q`
- No test files in production code
- Contract tests must fail before code changes

## Side Effects
- Reads source files for contract verification
- May write coverage artifacts

## Verification
- Run: `python -m pytest tests/ -q`
