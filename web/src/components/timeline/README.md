# timeline

## Overview
Timeline editor components.

## Interface
- TimelinePanel.tsx, TimelineClip.tsx, Playhead.tsx, TimelineRuler.tsx, TimelineTrackHeader.tsx

## Invariants
- Time calculations in seconds
- Renders are deterministic

## Side Effects
- Sync with playhead state

## Verification
- Run: `npm --prefix web run build`
