# hooks

## Overview
Custom React hooks for Brandly Studio state and playback.

## Interface
- usePlayback.ts
- usePlayhead.ts
- useWaveform.ts

## Invariants
- Hooks must follow Rules of Hooks
- No direct state mutation

## Side Effects
- Subscribes to WebSocket events
- Manages timers

## Verification
- Run: `npm --prefix web run lint`
