---
name: brandly-location-sheet
description: >
  Create comprehensive location reference sheets for AI video/image generation.
  Use when designing sets, environments, or backgrounds for campaigns.
  Triggers on "location sheet", "environment design", "set design",
  "location reference", "scene background", "environment reference".
  NOT for interior design consulting (use interior designer),
  NOT for architectural rendering (use dpf-blender-engineer).
---

# Brandly Location Sheet

Create comprehensive location reference sheets that ensure **consistent environments** across all AI-generated content. Essential for establishing shots, background consistency, and world-building.

## When to Use

- Creating consistent background environments
- Designing sets for product shoots
- Establishing location mood and atmosphere
- Building visual continuity across scenes
- Planning multi-shot sequences

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up location types | `references/location-types.md` |
| See lighting setups | `references/lighting-setups.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Location Sheet Structure

### 1. Basic Information
```
Location Name: [Name or descriptor]
Type: [Indoor/Outdoor/Studio/Natural]
Purpose: [Commercial/Residential/Industrial/etc.]
Time Period: [Contemporary/Historical/Futuristic]
Geographic Context: [Urban/Rural/Suburban]
```

### 2. Spatial Layout
```
Room/Space:
- Dimensions: [Approximate size]
- Ceiling height: [Standard/Tall/Vaulted]
- Layout: [Open plan/Divided sections]

Key Areas:
- [Primary focal point]
- [Secondary areas]
- [Transition spaces]

Sightlines:
- [What is visible from main angles]
- [Hidden areas]
- [Obstruction points]
```

### 3. Architectural Details
```
Structure:
- Walls: [Material, color, texture]
- Floor: [Material, finish, pattern]
- Ceiling: [Material, features]
- Windows: [Size, style, orientation]
- Doors: [Type, material, placement]

Fixtures:
- Lighting fixtures: [Type, placement]
- Built-ins: [Shelving, counters, etc.]
- Hardware: [Doorknobs, handles]
```

### 4. Decor & Styling
```
Furniture:
- [Type, style, material, color]
- [Arrangement/layout]
- [Condition: new/vintage/distressed]

Decorative Elements:
- Artwork: [Type, style, placement]
- Textiles: [Rugs, curtains, pillows]
- Accessories: [Vases, candles, books]
- Plants: [Type, placement]

Color Palette:
- Primary: [Dominant wall/floor color]
- Secondary: [Furniture, accents]
- Accent: [Pops of color]
- Neutrals: [Base tones]
```

### 5. Lighting Analysis
```
Natural Light:
- Direction: [North/South/East/West]
- Intensity: [Bright/Moderate/Dim]
- Time of day: [Morning/Noon/Afternoon/Golden hour/Blue hour]

Artificial Light:
- Fixture types: [Recessed/Pendant/Track/etc.]
- Color temperature: [Warm/Cool/Neutral]
- Intensity: [Bright/Dimmable]
- Shadows: [Hard/Soft/None]

Mood:
- Overall atmosphere: [Bright/Dramatic/Warm/Cool]
- Time of day feel: [Day/Evening/Night]
```

### 6. Atmospheric Details
```
Weather/Climate:
- [Indoor temp feel, humidity]
- [Outdoor conditions]

Ambient Elements:
- Sound: [Quiet/Lively/Urban/Natural]
- Smell: [Fresh/Cooking/Clean/Earthy]
- Air quality: [Crisp/Stuffy/Fresh]

Textures:
- Hard surfaces: [Reflective/Matte]
- Soft surfaces: [Plush/Smooth]
- Mixed: [Contrasting materials]
```

## Prompt Templates

### Establishing Shot Prompt
```
Wide establishing shot of [location type].
[Architectural style] with [key features].
[Time of day] lighting, [lighting quality].
[Atmosphere description].
[Cinematic style descriptor].
Quality: [8K/Commercial/Photorealistic]
```

### Interior Scene Prompt
```
Interior of [room type] in [building style].
[Walls/floor/ceiling materials and colors].
[Furniture layout description].
[Lighting description].
[Mood/atmosphere].
Camera: [wide/medium shot].
Quality: [Photorealistic/Commercial]
```

### Exterior Scene Prompt
```
Exterior view of [building/structure].
[Architectural style] with [materials].
[Surrounding environment].
[Time of day] with [lighting quality].
[Weather/atmosphere conditions].
Quality: [8K/Cinematic]
```

## Usage with Brandly CLI

### Generate Location Reference
```bash
brandly image --prompt "Establishing shot: [location description]" \
  --style-preset cinematic \
  --size 4K \
  --ratio 16:9
```

### Use Location in Video
```bash
brandly video <project_id> \
  --prompt "[Scene action] in [location description]" \
  --reference-images "https://example.com/location-ref.png" \
  --wait
```

### Multi-Shot Location Consistency
```bash
# Generate reference
brandly image --prompt "Wide shot of modern living room,
                        white walls, oak floors, large windows" \
  --style-preset commercial --size 4K

# Use reference for all shots
brandly video <project_id> --prompt "Person sitting on sofa" \
  --reference-images "https://example.com/location-ref.png"
```

## Quality Checklist

Before using a location sheet:

- [ ] Spatial layout clearly defined
- [ ] Architectural details specified
- [ ] Color palette established
- [ ] Lighting conditions documented
- [ ] Atmospheric qualities noted
- [ ] Reference images generated
- [ ] Consistency rules established

## Tips for AI Consistency

1. **Reference Images**: Always generate location refs first
2. **Maintain Key Features**: Document what must stay constant
3. **Lighting Consistency**: Match time of day across shots
4. **Color Harmony**: Keep palette consistent
5. **Scale Reference**: Include size cues in prompts

### Generate Location Reference (Recommended First Step)

For any location-heavy video or multi-asset campaign, generate a **location
reference** first via `brandly reference`. The reference is a GOLD-grade
image that locks the environment across all subsequent `brandly video` calls.

Location references are rendered as a **16:9 full-frame** single image —
ONE wide establishing shot filling the entire canvas, with no grid, no
split panels, and no insets. This gives `brandly video` the complete
spatial context to lock onto for environment continuity across shots.

```bash
brandly reference <project_id> \
  --subject-type location \
  --subject "Modern loft apartment, white marble, city skyline, golden hour" \
  --style-preset cinematic \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/<project_id>/images/<category>/`
with the `loc_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

