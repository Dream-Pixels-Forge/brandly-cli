# cmd

## Overview
Click command implementations grouped by domain.

## Interface
- brand.py, capabilities.py, gate.py, generation.py, metrics.py, plugin.py, post.py, production.py, providers.py, publish.py, team.py, tools.py

## Invariants
- Commands must be discoverable via `brandly --help`
- Each command validates arguments before execution

## Side Effects
- CLI may mutate project state
- May invoke external processes

## Verification
- Run: `python -m pytest tests/test_cli*.py -q`
