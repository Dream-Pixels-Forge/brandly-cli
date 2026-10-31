# brandly_cli

## Overview
Core Python CLI, agent surface, MCP server, and web server for Brandly.

## Interface
- Public modules: cli, agent_surface, shot_runner, quality_gate, mcp_server, video_backend
- Subdirectories:
  - ./agent_tools/README.md
  - ./cmd/README.md
  - ./web/README.md

## Invariants
- State lives on disk in `.brandly/<project>/` for resumability
- Phases are fail-closed
- Phase handoffs are explicit contracts

## Side Effects
- Writes project artifacts to disk
- Calls external AI providers (Agnes, Minimax)
- Modifies local config/credentials

## Verification
- Run: `python -m pytest tests/ -q`
