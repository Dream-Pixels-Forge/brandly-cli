---
name: brandly-consistency
description: >
  Maintain absolute visual and narrative consistency across all shots,
  characters, products, and environments in a campaign. Use when
  character drifts, lighting shifts, or you need a systematic approach
  to locking visual identity across an entire production.
  Triggers on "keep consistent", "character drifting", "lock identity",
  "consistency check", "same character", "match the look",
  "preserve visual style", "maintain continuity", "fix drift".
  NOT for generating new assets (use individual sheet skills),
  NOT for editing (use dpf-senior-editor).
---

# Brandly Consistency

Consistency is the hardest problem in AI-generated video. This skill provides the **systematic approach** to locking identity across every shot, every asset, and every generation pass.

## When to Use

- Character appearance changes between shots
- Lighting doesn't match across scenes
- Product looks different in each clip
- Overall visual tone drifts
- Multi-agent team needs shared reference
- Re-generating shots after edits

---

## Routing Table

| Want to... | Read |
|------------|------|
| Learn the anchoring system | `references/anchoring-system.md` |
| See drift diagnosis methods | `references/drift-checklist.md` |
| Reference lock strength by asset type | `references/lock-strength.md` |

---

## The Anchoring System

Every element in your production gets an **anchor strength** and a **re-anchor protocol**:

### Anchor Levels

| Level | Strength | What It Locks | Re-Anchor Method |
|-------|----------|---------------|------------------|
| 🔒 GOLD | Highest | Core character identity, hero product | Reference image + condensed description in every prompt |
| 🔒 SILVER | High | Location, secondary characters | Reference image + lighting notes in every prompt |
| 🔒 BRONZE | Medium | Props, background elements | Reference image every 3rd shot, description in prompts |
| ⚪ PLASTIC | Flexible | Mood, texture, atmosphere | Describe in prompt only, no reference needed |

### What Goes in Each Anchor

```markdown
## CHARACTER ANCHOR (GOLD)
Name: [Name]
Anchor traits: [trait 1, trait 2, trait 3]
Must never change: [list of immutable features]
Can vary: [list of features that may change per scene]
```

```markdown
## LOCATION ANCHOR (SILVER)
Name: [Location]
Key features: [feature 1, feature 2, feature 3]
Lighting time: [consistent time of day]
Mood tag: [one word that defines atmosphere]
```

```markdown
## PRODUCT ANCHOR (GOLD)
Name: [Product]
Hero angles: [angle 1, angle 2, angle 3]
Colors: [exact colors, hex if possible]
Logo: [exact placement and size]
Surface: [material, finish, reflectivity]
```

---

## The Three-Layer Prompt Strategy

Every generation prompt must contain three layers:

```
[LAYER 1: Anchor Block]
--ANCHOR--
character: [condensed name + 3 anchor traits]
location: [location name + key feature]
product: [product name + hero detail]
lighting: [time of day + quality]
--END-ANCHOR--

[LAYER 2: Action/Prompt]
[What is happening in this shot]

[LAYER 3: Style Suffix]
[Cinematic style, quality tags, film stock]
```

### Example

```
--ANCHOR--
character: Maya, mid-20s, olive skin, emerald eyes, braided hair
location: Modern kitchen, white marble, large window
product: Glass perfume bottle, rose gold cap, condensation
lighting: Golden hour, soft side light through window
--END-ANCHOR--

Maya picks up the perfume bottle, bringing it close to her face.
The camera pushes in slowly to a close-up of her eyes closing.

Cinematic, Kodak Vision3 500T, shallow depth of field, 8K quality
```

---

## Drift Detection Checklist

When reviewing generated shots, check:

### Character Drift
- [ ] Eye color matches reference
- [ ] Hair color/texture matches reference
- [ ] Facial structure matches reference
- [ ] Outfit matches planned wardrobe
- [ ] Body type hasn't shifted

### Location Drift
- [ ] Wall colors match reference
- [ ] Furniture/layout matches reference
- [ ] Lighting direction matches reference
- [ ] Time of day is consistent

### Product Drift
- [ ] Shape/proportions haven't changed
- [ ] Color is identical
- [ ] Logo/text hasn't shifted or distorted
- [ ] Material finish matches (matte vs glossy)

### Lighting Drift
- [ ] Key light direction is consistent
- [ ] Color temperature matches (warm/cool)
- [ ] Shadow hardness matches
- [ ] Global illumination tone matches

---

## Re-Anchoring Protocol

When drift is detected:

### Step 1: Regenerate Reference Image
```bash
brandly image --prompt "[Asset type] reference: [full description]" \
  --style-preset [matching preset] --size 4K
```
Save the new reference. Update the anchor block.

### Step 2: Strengthen the Prompt
Add stronger anchor language to the prompt:
```
[SAME FACIAL FEATURES AS REFERENCE. IDENTICAL HAIR COLOR AND STYLE.]
[MAINTAIN EXACT PRODUCT APPEARANCE FROM REFERENCE IMAGE.]
```

### Step 3: Lower Expectations
If drift persists after re-anchoring:
- Break the scene into smaller, simpler shots
- Reduce motion in the shot (less movement = more consistency)
- Increase reference image weight (use multiple reference images)
- Accept the variation and document it as a permanent change

---

## Lock Strength by Asset Type

| Asset | Recommended Level | Why |
|-------|-------------------|-----|
| Main character | 🔒 GOLD | Identity is everything |
| Hero product | 🔒 GOLD | Brand recognition depends on it |
| Primary location | 🔒 SILVER | Sets the world |
| Secondary characters | 🔒 SILVER | Need consistency but less critical |
| Key props | 🔒 BRONZE | Visible but not focal |
| Background extras | ⚪ PLASTIC | Audience won't notice drift |
| Atmosphere/mood | ⚪ PLASTIC | Intentional variation is okay |
| Text overlays | ⚪ PLASTIC | Different per shot by design |

---

## Advanced: Multiple Reference Images

When a single reference isn't enough:

```bash
# Combine character + location + product references
brandly video <project_id> \
  --reference-images "character.png,location.png,product.png" \
  --prompt "..." --wait
```

**Order matters** — the first reference image has the strongest influence.

For complex scenes with multiple elements:
```bash
# Character + outfit + environment
brandly video <project_id> \
  --reference-images "face_ref.png,outfit_ref.png,location_ref.png" \
  --prompt "..." --wait
```

---

## CLI Implementation

Use the prompt structure below for every generation. Save the anchor text to a file for reuse:

```bash
# Save anchor block to a file
cat > anchors.txt << 'EOF'
--ANCHOR--
character: Maya — olive skin, emerald eyes, dark braids
product: Lumière perfume — clear glass, rose gold cap
lighting: Golden hour sunrise, soft diffusion
--END-ANCHOR--
EOF

# Prepend anchor to prompt file before each generation
cat anchors.txt prompt_shot_1.txt > anchored_shot_1.txt

# Generate with reference images (auto-loaded from project artifacts)
brandly video <project_id> --prompt "$(cat anchored_shot_1.txt)" --wait
```

**Key point:** The `brandly video` command auto-detects existing artifact images from your project directory and injects them as reference images automatically. No manual URL management needed once assets are generated.

---

## Quality Checklist

Before any generation pass:

- [ ] Anchor blocks written for all GOLD and SILVER assets
- [ ] Reference images generated (auto-detected from project artifacts by `brandly video`)
- [ ] Three-layer prompt structure used
- [ ] Drift checklist reviewed against previous outputs
- [ ] Anchor strength levels assigned to every asset

After each generation pass:

- [ ] Review all outputs against drift checklist
- [ ] Document any drift in production bible
- [ ] Re-anchor if drift exceeds acceptable threshold
- [ ] Update asset inventory with new reference URLs
