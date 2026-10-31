# agent_tools

## Overview
Agent-callable tools exposed via MCP server for Brandly CLI.

## Interface
- project.py: project lifecycle tools
- pipeline.py: phase execution tools
- pre_production.py: reference/storyboard tools
- production.py: asset generation tools
- media.py: media utilities
- documents.py: doc generation tools

## Invariants
- All tools must be idempotent where possible
- Read-only tools must not mutate state
- Write tools require explicit approval gates

## Side Effects
- Mutates project state on disk
- Calls external AI providers
- Writes media files

## Verification
- Run: `python -m pytest tests/test_agent_tools.py -q`
