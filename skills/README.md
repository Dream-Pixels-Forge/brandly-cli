# Brandly CLI Skills Index

Complete reference for all agent skills in the brandly-cli skill system.

## Core Generation Skills

| Skill | Purpose | Triggers On |
|-------|---------|-------------|
| [brandly-video-generation](brandly-video-generation/SKILL.md) | Master skill — generate AI video & images with prompt engineering, camera control, lighting presets | "generate video", "create video ad", "AI video generation", "cinematic prompt" |
| [brandly-storyboard](brandly-storyboard/SKILL.md) | Plan shot-by-shot visual blueprints before generating | "storyboard", "shot list", "shot sequence", "scene breakdown" |
| [brandly-production-bible](brandly-production-bible/SKILL.md) | Single source of truth document for the entire campaign | "production bible", "campaign bible", "style guide", "project document" |
| [brandly-consistency](brandly-consistency/SKILL.md) | Lock visual identity across all shots and assets | "keep consistent", "character drifting", "lock identity", "consistency check" |

## Asset Reference Sheet Skills

| Skill | Purpose | Triggers On |
|-------|---------|-------------|
| [brandly-character-sheet](brandly-character-sheet/SKILL.md) | Character reference sheets — face, hair, wardrobe, posture | "character sheet", "character design", "character reference" |
| [brandly-object-sheet](brandly-object-sheet/SKILL.md) | Product/object reference sheets — dimensions, materials, branding | "object sheet", "product reference", "product photography" |
| [brandly-location-sheet](brandly-location-sheet/SKILL.md) | Location/set reference sheets — layout, lighting, atmosphere | "location sheet", "environment design", "set design" |
| [brandly-vehicle-sheet](brandly-vehicle-sheet/SKILL.md) | Vehicle reference sheets — cars, trucks, aircraft specs | "vehicle sheet", "car reference", "automotive prompt" |
| [brandly-mecha-sheet](brandly-mecha-sheet/SKILL.md) | Mecha/robot reference sheets — technical design, materials | "mecha sheet", "robot design", "machine reference" |
| [brandly-animal-sheet](brandly-animal-sheet/SKILL.md) | Animal/creature reference sheets — species, behavior, habitat | "animal sheet", "creature design", "wildlife prompt" |
| [brandly-plant-sheet](brandly-plant-sheet/SKILL.md) | Plant/botanical reference sheets — species, growth, seasons | "plant sheet", "botanical reference", "garden design" |

## Recommended Workflow

```
New Campaign →
  1. brandly-production-bible   (define everything)
  2. brandly-storyboard          (plan every shot)
  3. Asset sheets                (generate reference images)
  4. brandly-consistency         (set up anchoring)
  5. brandly-video-generation    (execute generation)
```

## Skill Dependencies

```
brandly-video-generation
  ├── brandly-storyboard        (recommended before generation)
  ├── brandly-production-bible  (recommended before generation)
  ├── brandly-consistency       (recommended for multi-shot campaigns)
  ├── brandly-character-sheet   (needed for character scenes)
  ├── brandly-object-sheet      (needed for product scenes)
  ├── brandly-location-sheet    (needed for environment scenes)
  ├── brandly-vehicle-sheet     (needed for automotive scenes)
  ├── brandly-mecha-sheet       (needed for sci-fi/tech scenes)
  ├── brandly-animal-sheet      (needed for wildlife scenes)
  └── brandly-plant-sheet       (needed for nature scenes)
```
