# scripts

## Overview
Utility scripts for repo maintenance and previews.

## Interface
- version_check.py, make_studio_preview.py, import_graph.py

## Invariants
- Scripts must be idempotent
- No side effects on production data

## Side Effects
- May write preview images

## Verification
- Run: `python scripts/version_check.py`
