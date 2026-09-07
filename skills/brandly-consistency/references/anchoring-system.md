---
name: Anchoring System Deep Dive
description: The technical system behind visual consistency locking.
---

# The Anchoring System

The anchoring system is how brandly-cli maintains visual consistency across generations. Understanding it is key to getting reliable results.

## How Anchoring Works

Every generation prompt goes through three layers:

### Layer 1: Anchor Block (Mandatory for GOLD/SILVER assets)

```
--ANCHOR--
character: [condensed name + immutable traits]
location: [name + key feature]
product: [name + defining detail]
lighting: [time + quality]
--END-ANCHOR--
```

The AI model reads this first and uses it as a **context anchor** before processing the action prompt. It primes the model's understanding of what "consistent" means for this campaign.

### Layer 2: Action Prompt (The shot description)

This is your normal shot prompt — what's happening, where, who's doing what.

### Layer 3: Style Suffix (Quality signal)

```
[Cinematic/descriptor], [film stock/emulsion], [quality tag]
```

This sets the render quality and artistic tone consistently.

## Why Anchors Prevent Drift

AI image/video models work probabilistically. Each generation is a fresh roll of the dice. Without anchors:

- The model might interpret "woman with brown hair" as a different shade each time
- "Modern kitchen" could become Scandinavian one shot, industrial the next
- "Perfume bottle" might change shape or color between generations

Anchors reduce the probability space by:

1. **Providing explicit constraints** — "emerald green eyes, NOT blue"
2. **Creating semantic hooks** — the model latches onto repeated phrases
3. **Reinforcing with reference images** — visual confirmation of the text anchor

## Anchor Strength Tiers

### 🔒 GOLD Anchor (Never Compromise)

Used for: Main character identity, hero product appearance

```markdown
--ANCHOR--
character: Maya — immutable: olive warm skin, emerald green eyes, 
           dark brown hair loose braids, freckles on nose bridge
--END-ANCHOR--
```

**Rule:** This anchor block appears in EVERY shot prompt, verbatim.

### 🔒 SILVER Anchor (Strong Consistency)

Used for: Primary location, secondary characters, key props

```markdown
--ANCHOR--
location: Modern bedroom — immutable: floor-to-ceiling windows, 
          white marble nightstand, sheer curtains, city skyline
lighting: Golden hour sunrise, soft diffusion through window
--END-ANCHOR--
```

**Rule:** Appears in every shot using this location. Lighting anchor repeats in every shot.

### 🔒 BRONZE Anchor (Periodic Reinforcement)

Used for: Background props, secondary objects

```markdown
--ANCHOR--
prop: White ceramic coffee mug — appears in shots 2, 5, 7
--END-ANCHOR--
```

**Rule:** Appears in 2 out of 3 shots. Every third shot must include the full anchor block.

### ⚪ Plastic (Describe Only)

Used for: Atmosphere, background extras, mood elements

**Rule:** No anchor block needed. Describe in prompt naturally.

## Reference Image Weight

When combining anchor blocks with reference images:

| Reference Images | Anchor Required | Effective Lock |
|-----------------|-----------------|----------------|
| 0 | Full anchor block | ~60% consistent |
| 1 (same asset type) | Condensed anchor | ~75% consistent |
| 1 (different asset type) | Full anchor block | ~70% consistent |
| 2+ (matching asset types) | Condensed anchor | ~85% consistent |
| 3+ (full coverage) | Minimal anchor | ~90%+ consistent |

## Drift Tolerance by Asset

| Asset Type | Acceptable Drift | Intolerable Drift |
|------------|-----------------|-------------------|
| Character face | ±1 shade of skin tone | Different eye color, different hair |
| Character outfit | Minor style variation | Completely different garment |
| Product color | ±5% saturation shift | Different hue, different material |
| Product shape | Minor proportion shift | Completely different bottle shape |
| Location walls | ±1 paint shade | Different material, different color family |
| Lighting time | ±30 min window | Day vs. night, indoor vs. outdoor |
| Lighting quality | Soft vs. hard variation | Warm vs. cool, directional vs. flat |

## The Re-Anchoring Workflow

When drift is detected:

```
1. IDENTIFY drift source
   ↓
2. Regenerate the affected asset reference
   ↓
3. Strengthen the anchor block (add more specific descriptors)
   ↓
4. Add extra reference images if available
   ↓
5. Reduce shot complexity (fewer elements = more consistency)
   ↓
6. Re-generate and compare
```

## Advanced: Cross-Asset Consistency

When multiple anchored assets appear together:

```markdown
--ANCHOR--
character: Maya — olive skin, emerald eyes, dark braids
location: Modern bedroom — white marble, sheer curtains, golden hour
product: Lumière perfume — clear glass, rose gold cap, amber liquid
lighting: Golden hour sunrise, soft diffusion
--END-ANCHOR--
```

**Key principle:** The lighting anchor must be consistent across all assets in the same shot. If Maya is in golden hour and the product is in studio light, the shot will feel disjointed.

## Using Anchors with the CLI

Anchors are passed via prompt text — there is no dedicated `brandly anchor` command. Use a shell heredoc to build prompts with embedded anchors:

```bash
# Create a prompt file with an embedded anchor block
cat > shots/shot_01.txt << 'EOF'
--ANCHOR--
character: Maya — immutable: olive warm skin, emerald green eyes,
           dark brown hair loose braids, freckles on nose bridge
lighting: Golden hour sunrise, soft diffusion through window
--END-ANCHOR--

Maya walks gracefully toward the camera, holding the Lumière perfume bottle.
She pauses and smiles, bringing the bottle close to her face.
[Cinematic], [Kodak Vision3 500T], [commercial quality]
EOF

# Generate video using the anchored prompt
brandly video <project_id> --prompt "$(cat shots/shot_01.txt)" --style cinematic --wait
```

To generate reference images for anchoring:

```bash
# Generate character reference
brandly image --prompt "Character reference sheet: Maya, front/side/3/4 views,
  olive warm skin, emerald green eyes, dark brown hair in side braid,
  consistent lighting, clean background, professional reference sheet" \
  --style-preset photorealistic --size 4K

# Use the generated image as reference in video
brandly video <project_id> --prompt "$(cat shots/shot_01.txt)" \
  --reference-images ".brandly/projects/<id>/artifacts/images/maya-ref.png" --wait
```
