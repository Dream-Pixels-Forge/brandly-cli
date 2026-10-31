# utils

## Overview
Web utilities for media probing and thumbnails.

## Interface
- ffprobe.py, thumbnail.py

## Invariants
- Functions are pure except for file I/O
- No network calls

## Side Effects
- Reads video files
- Writes thumbnail images

## Verification
- Run: `python -m pytest tests/ -q`
