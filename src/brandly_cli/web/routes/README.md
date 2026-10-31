# routes

## Overview
FastAPI route handlers for Brandly Studio web API.

## Interface
- projects.py, timeline.py, clips.py, cast.py, gate.py, review.py, monitor.py, config.py, docs.py, export.py, waveform.py

## Invariants
- All endpoints validate with Pydantic models
- Auth checks enforced where required
- Errors returned as structured JSON

## Side Effects
- Reads/writes project state
- Triggers background jobs

## Verification
- Run: `python -m pytest tests/test_web*.py -q`
