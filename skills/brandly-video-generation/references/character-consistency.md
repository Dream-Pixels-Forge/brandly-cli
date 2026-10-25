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

---

## Multi-Character Identity Bleed (issue #51)

### The Problem

When **two or more characters co-appear** in a single shot, Agnes's
image-to-video anchors *every* figure's face to the **dominant**
(first-listed) reference plate. A shot meant to show "Silas alone,
drawing the gun" renders **Elias's** face on Silas. The dominant
character bleeds into every figure in frame.

This is the #1 cause of "the second character looks wrong" in
multi-character scenes.

### The Fix: Dedicated Single-Subject Hero Plates

For each co-appearing character, generate a **clean 1:1 hero portrait**
that shows ONLY that character (no other person in frame, no scene
context). Use that plate — not the multi-character turnaround — as the
reference for shots where that character is the on-screen subject.

```
char_eliasmona.png        <- Elias hero plate (Elias only)
char_silas-hero.png       <- Silas hero plate (Silas only, white/scarred)
char_mariam.png           <- Miriam hero plate (Miriam only)
```

Per-shot reference rules:

| Shot subject | Reference plate(s) to pass |
|---|---|
| Elias alone | `char_eliasmona` |
| Silas alone | `char_silas-hero`  (NOT `char_eliasmona`) |
| Elias + Silas co-appear | BOTH plates, in the order the dominant one goes first |
| Object / location only | `prop_*` / `loc_*` |

### The Gate Check

`brandly video` and `brandly produce` now pass the shot's
co-appearing character names to the quality gate. When 2+ characters
are declared present, the vision prompt asks the model to verify each
figure is rendered with **its own** identity (not the dominant
character's face) and to set `identity_bleed` in the verdict. A
`true` bleed is a **gate failure** — the shot must be regenerated with
a hero plate for the bled character.

In the shot list JSON, declare presence with the `characters` key:

```json
{
  "id": "shot04_silas_close",
  "refs": ["char_silas-hero", "loc_exterior_church_wide"],
  "character": "Silas Vanesky, 62, gaunt WHITE man, scarred jaw, silver Glock — NOT Elias (Elias is Black, in a soutane)",
  "characters": "Silas Vanesky, Elias Mona",
  "prompt": "..."
}
```

The `characters` array drives the gate's `expected_characters` list.
The `character` string is the per-shot identity anchor for the prompt.
The `refs` list is the reference plate set — **use the hero plate for
the on-screen subject, not the multi-character turnaround**.

### Quick Diagnostic

If a generated clip shows the wrong face on a secondary character:

1. Check the reference plates you passed — did you pass a
   multi-character turnaround that includes the dominant face?
2. Regenerate with a dedicated hero plate for that character.
3. If the bleed persists, split the shot into two: a close-up of the
   secondary character (their hero plate only), cut to a wide that
   shows both (both plates, dominant first).
