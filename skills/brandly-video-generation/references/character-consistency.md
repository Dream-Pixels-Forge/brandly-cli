# Character Consistency Guide

Advanced techniques for maintaining character consistency.

## The Problem

AI video models often drift in character appearance between shots:
- Different face structure
- Hair color/style changes
- Clothing mismatches
- Body type variations
- Age inconsistencies

## Solution Framework

### Step 1: Define Character Completely

Create a detailed character anchor:

```
CHARACTER ANCHOR:
- Name: [Name]
- Age: [Age range]
- Ethnicity: [Specific background]
- Height: [Tall/Medium/Short]
- Build: [Slim/Athletic/Average/Stocky]

Face:
- Shape: [Oval/Round/Square/etc.]
- Skin: [Tone with undertones]
- Eyes: [Color and shape]
- Nose: [Shape]
- Lips: [Full/Thin/Medium]
- Hair: [Color, style, length, texture]

Wardrobe:
- Top: [Type, color, material]
- Bottom: [Type, color, material]
- Shoes: [Type, color]
- Accessories: [Jewelry, glasses, etc.]

Distinctive Features:
- [Scars, freckles, unique traits]
- [Signature items or poses]
```

### Step 2: Generate Reference Images

Create multiple reference angles:

```bash
# Front view
brandly image --prompt "Character reference: [full description], front view, neutral expression"

# Side view
brandly image --prompt "Character reference: [full description], side profile"

# Three-quarter view
brandly image --prompt "Character reference: [full description], three-quarter view"
```

### Step 3: Use Reference Images

Always include reference images in video generation:

```bash
brandly video <project_id> \
  --prompt "[scene description]" \
  --character "[condensed description]" \
  --reference-images "https://example.com/ref1.jpg,https://example.com/ref2.jpg" \
  --wait
```

### Step 4: Add Consistency Anchors

Include consistency rules in prompts:

```
IMPORTANT CONSISTENCY RULES:
- Same face structure: [specific features]
- Same hair: [color, style, length]
- Same outfit: [description]
- Same body type: [description]
- No identity drift between shots
```

## Advanced Techniques

### Technique 1: Full Description Repetition

Include condensed character description in every shot prompt:

```
Shot 1: [Character: woman, 28, black bob hair, red dress] walking in garden...
Shot 2: [Same character] turning to face camera...
Shot 3: [Same character] picking flowers...
```

### Technique 2: Anchor Phrase Method

Create a memorable anchor phrase:

```
ANCHOR: "Sarah, 28, black bob, red silk dress, gold hoops"

Shot 1: Sarah walks through garden...
Shot 2: Sarah turns to camera...
Shot 3: Sarah picks flowers...
```

### Technique 3: Multi-Reference Strategy

Use multiple reference images for different aspects:

```
--reference-images "face.jpg,hair.jpg,outfit.jpg"
```

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Face changes | Insufficient description | Add more specific facial features |
| Hair drifts | Not mentioned in subsequent shots | Include hair in every prompt |
| Outfit mismatch | Variations between shots | Specify exact outfit consistently |
| Age shift | Vague age description | Use specific age range |
| Body type varies | Generic build description | Include specific body details |

## Best Practices Checklist

- [ ] Full character anchor created before generation
- [ ] Reference images generated for key angles
- [ ] Condensed description saved for reuse
- [ ] Consistency rules documented
- [ ] Test with 1 shot before full sequence
- [ ] All shots include character reference
- [ ] Same reference images used throughout

## When to Generate Separately

For critical consistency needs:
1. Generate each shot separately
2. Use same reference images
3. Use same character description
4. Review each shot before proceeding
5. Composite in post-production if needed
