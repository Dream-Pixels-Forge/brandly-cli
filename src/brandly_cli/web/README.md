# web

## Overview
FastAPI web server and WebSocket layer for Brandly Studio timeline editor.

## Interface
- server.py: FastAPI app factory
- routes/: API endpoints
- websocket.py: real-time state sync
- state.py: in-memory project state
- models.py: Pydantic schemas

## Invariants
- State persistence is disk-backed, not in-memory only
- All routes must validate input with Pydantic
- WebSocket messages are JSON only

## Side Effects
- Serves static assets
- Writes logs
- Maintains WebSocket connections

## Verification
- Run: `python -m pytest tests/test_web*.py -q`
