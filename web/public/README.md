# static

## Overview
Built web SPA assets served by FastAPI.

## Interface
- index.html, assets/, favicon.svg, icons.svg, preview.jpg

## Invariants
- Assets are build artifacts, not source
- Do not edit manually

## Side Effects
- Served over HTTP

## Verification
- Run: `npm --prefix web run build`
