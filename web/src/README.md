# web/src

## Overview
React 19 + TypeScript frontend for Brandly Studio.

## Interface
- App.tsx, main.tsx, Shell.tsx
- components/: UI components
- hooks/: custom React hooks

## Invariants
- TypeScript strict mode
- No direct DOM manipulation
- Components must be pure

## Side Effects
- Fetches from FastAPI backend
- Modifies URL search params

## Verification
- Run: `npm --prefix web run lint`
- Run: `npm --prefix web run build`
