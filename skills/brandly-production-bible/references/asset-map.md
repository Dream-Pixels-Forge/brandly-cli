---
name: Asset Map
description: How all asset sheets connect and where they live in the bible.
---

# Asset Map

Visual guide to how asset sheets connect within the production bible.

## Asset Relationship Map

```
                    ┌─────────────────────┐
                    │   PRODUCTION BIBLE   │
                    │   (Project Root)     │
                    └─────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │ CHARACTERS  │     │  LOCATIONS  │     │   PRODUCTS  │
   │  (GOLD)     │     │  (SILVER)   │     │  (GOLD)     │
   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
          │                   │                   │
    ┌─────┴─────┐       ┌─────┴─────┐       ┌─────┴─────┐
    │ Sheet PNG │       │ Sheet PNG │       │ Sheet PNG │
    │ Ref URLs  │       │ Ref URLs  │       │ Ref URLs  │
    │ Anchors   │       │ Anchors   │       │ Anchors   │
    └───────────┘       └───────────┘       └───────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │     STORYBOARD      │
                    │  (Shot-by-shot plan) │
                    └─────────┬───────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
               ┌────────┐ ┌────────┐ ┌────────┐
               │ SHOT 1 │ │ SHOT 2 │ │ SHOT 3 │
               │ Assets │ │ Assets │ │ Assets │
               └────────┘ └────────┘ └────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  GENERATED OUTPUTS  │
                    │  (Videos, images)   │
                    └─────────────────────┘
```

## Asset Dependency Rules

1. **Location refs must exist before any shot using that location**
2. **Character refs must exist before any shot featuring that character**
3. **Product refs must exist before any hero/product shot**
4. **Generate all refs FIRST, then build storyboard, then generate shots**

## File Organization

```
project/
├── production-bible.md          ← Single source of truth
├── storyboard.md                ← Shot plan (can be embedded in bible)
├── assets/
│   ├── characters/
│   │   ├── maya.png            ← Character reference image
│   │   └── maya-anchor.txt     ← Anchor traits text file
│   ├── locations/
│   │   ├── modern_bedroom.png
│   │   └── modern_bedroom-anchor.txt
│   ├── products/
│   │   ├── lumiere.png
│   │   └── lumiere-anchor.txt
│   └── videos/
│       ├── shot_01.mp4
│       ├── shot_02.mp4
│       └── ...
└── skills/
    ├── brandly-character-sheet/
    ├── brandly-location-sheet/
    ├── brandly-object-sheet/
    └── brandly-consistency/
```

## Anchor Text File Format

Each asset can have a companion `.txt` file storing the anchor block:

```
--ANCHOR--
type: character
name: Maya
anchors: olive skin warm undertone, emerald green almond eyes, long dark brown hair loose braids, subtle freckles
immutable: eye color, skin tone, hair color, braid style
variable: expression, outfit (neutral tones only)
--END-ANCHOR--
```

## When to Regenerate References

| Situation | Action |
|-----------|--------|
| Character looks different in new shot | Regenerate character ref, update anchor |
| Location lighting shifted | Regenerate location ref with same time-of-day |
| Product color drifted | Regenerate product ref with exact hex codes |
| Starting new campaign variant | Create new asset set, version the bible |
