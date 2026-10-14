---
name: brandly-character-sheet
description: >
  Create comprehensive character reference sheets for AI video/image generation.
  Use when designing characters, models, people for campaigns.
  Triggers on "character sheet", "character design", "character reference",
  "character consistency", "build a character", "character prompt",
  "create a character", "character reference image".
  NOT for costume design (use fashion designer), NOT for 3D character modeling (use dpf-blender-engineer).
---

# Brandly Character Sheet

Create comprehensive character reference sheets that ensure **consistent identity** across all AI-generated content. This skill transforms vague character descriptions into precise, production-ready specifications.

## When to Use

- Building characters for video campaigns
- Creating character consistency across multiple shots
- Generating character reference images
- Defining character appearance for AI video generation
- Establishing visual identity for brands or products

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up common character types | `references/common-types.md` |
| See consistency checklists | `references/consistency-checklist.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Character Sheet Structure

Every character sheet must include:

### 1. Core Identity
```
Name: [Character name or descriptor]
Age Range: [e.g., 25-35 years old]
Gender: [Male/Female/Non-binary/Androgynous]
Ethnicity: [Specific background]
Body Type: [Slim/Athletic/Average/Stocky/Tall/Short]
```

### 2. Physical Appearance
```
Face:
- Face shape: [Oval/Round/Square/Heart/Diamond]
- Skin tone: [Detailed description with undertones]
- Eye color: [Specific shade]
- Eye shape: [Almond/Hooded/Downturned/Upturned]
- Nose: [Shape descriptor]
- Lips: [Full/Thin/Medium]
- Facial hair: [Clean-shaven/Stubble/Beard/Mustache]

Hair:
- Color: [Specific shade]
- Style: [Cut and styling]
- Length: [Short/Medium/Long]
- Texture: [Straight/Wavy/Curly/Kinky]

Distinctive Features:
- Scars, freckles, moles, birthmarks
- Unique eye color or pattern
- Distinctive nose shape
- Other memorable traits
```

### 3. Wardrobe & Style
```
Primary Outfit:
- Top: [Type, color, material]
- Bottom: [Type, color, material]
- Shoes: [Type, color]
- Accessories: [Jewelry, watches, glasses, bags]

Style Aesthetic:
- [Minimalist/Bohemian/Business/Streetwear/Luxury/etc.]
- Color palette: [Primary and secondary colors]
- Materials: [Fabrics, textures]

Signature Pieces:
- [Item that defines the character's look]
```

### 4. Posture & Movement
```
Default Posture:
- Stance: [Relaxed/Tense/Elegant/Confident]
- Weight distribution: [Even/Leaning/Hip-pop]

Movement Style:
- Walk: [Stride length, speed, grace]
- Gestures: [Animated/Subtle/Eliminated]
- Expressions: [Default expression, range]
```

### 5. Lighting & Rendering Notes
```
Recommended Lighting:
- Key light: [Type, position, intensity]
- Fill light: [Type, position]
- Rim light: [For separation]

Rendering Style:
- Camera: [Lens type, focal length]
- Depth of field: [Shallow/Deep]
- Color grade: [Warm/Cool/Neutral]
- Film stock emulation: [Kodak/ Fujifilm/etc.]
```

## Prompt Templates

### Basic Character Prompt
```
[Age] [gender] [ethnicity] with [body type] build,
[face shape] face with [skin tone] skin,
[eye color] [eye shape] eyes,
[hair color] [hair texture] hair styled [hair style].
Wearing [outfit description].
[posture/movement note].
[Cinematic style descriptor].
```

### Detailed Character Prompt
```
Professional character reference sheet.
Subject: [Name/Description]
Appearance: [Complete physical description]
Wardrobe: [Complete outfit description]
Pose: [Standing/sitting/active pose]
Expression: [Facial expression]
Lighting: [Studio/natural/cinematic lighting]
Camera: [Lens type, angle]
Style: [Photorealistic/Cinematic/Illustration]
Quality: [8K/UHD/Professional photography]
```

## Usage with Brandly CLI

### Generate Character Reference Image
```bash
brandly image --prompt "Character reference sheet: [detailed description]" \
  --style-preset photorealistic \
  --size 4K
```

### Mandatory Backdrop (all reference-sheet renders)
Every reference board **must** be rendered on a **seamless matte neutral mid-grey studio backdrop** with subtle thin grey divider lines — never a white, colored, busy, or in-scene background. This keeps cutouts clean, identity consistent, and avoids color spill. If a model ignores the backdrop, the quality gate (`brandly gate`) flags `matte_background` and the sheet should be regenerated.

### Generate Character Reference (Recommended First Step)

For any character video or multi-asset campaign, generate a **character reference**
first via `brandly reference`. The reference is a GOLD-grade image that
locks the character appearance across all subsequent `brandly video` calls.

Character references are rendered as a **16:9 multi-view grid** — all
views in ONE image, split into three columns. This gives `brandly video`
multiple angles to lock onto for consistency across shots.

```bash
brandly reference <project_id> \
  --subject-type character \
  --subject "Maya, 25, dark braids, olive skin, emerald eyes, wearing flowing red dress" \
  --style-preset photorealistic \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/<project_id>/images/<category>/`
with the `char_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

### Use Character in Video Generation
```bash
brandly video <project_id> \
  --prompt "Cinematic scene with [character description]" \
  --character "[condensed character summary]" \
  --reference-images "https://example.com/character-sheet.png" \
  --wait
```

### Create Character Consistency Notes
```
CHARACTER ANCHOR:
- Name: [Name]
- Key traits: [3-5 most important visual features]
- Clothing: [Signature outfit]
- Distinguishers: [What makes them unique]

CONSISTENCY RULES:
- Never change: [features that must stay the same]
- Can vary: [features that can change between scenes]
```

## Quality Checklist

Before using a character sheet:

- [ ] Physical description is specific (no vague terms like "handsome")
- [ ] Wardrobe details are concrete (colors, materials, styles)
- [ ] Distinctive features are documented
- [ ] Posture and movement are defined
- [ ] Lighting recommendations match project style
- [ ] Consistency rules are established
- [ ] Reference image generated and saved

## Tips for AI Consistency

1. **Be Specific**: Use exact color names (not "blue" but "navy blue")
2. **Anchor Key Features**: Identify 3-5 features that MUST stay consistent
3. **Generate Reference**: Always create a reference image first
4. **Use Reference Mode**: Pass character sheet as --reference-images
5. **Document Everything**: Save prompts and settings for reuse
