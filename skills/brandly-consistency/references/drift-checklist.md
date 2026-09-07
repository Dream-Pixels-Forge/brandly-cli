---
name: Drift Diagnosis Checklist
description: Systematic method for identifying and fixing visual drift.
---

# Drift Diagnosis Checklist

Use this checklist whenever you suspect consistency has broken down between shots.

## Step 1: Identify the Drift Type

Check each category. Mark what you observe:

### Character Drift
- [ ] **Eye color changed** — emerald → hazel → blue
- [ ] **Hair color shifted** — dark brown → light brown → blonde
- [ ] **Hair style drifted** — braids → loose → ponytail
- [ ] **Face shape changed** — oval → round → heart
- [ ] **Skin tone shifted** — warm olive → cool tan → pale
- [ ] **Facial features changed** — nose shape, lip fullness, jawline
- [ ] **Body type drifted** — slim → athletic → curvy
- [ ] **Age appeared to shift** — looked younger/older than reference
- [ ] **Outfit changed completely** — different color, style, or garment
- [ ] **Accessories appeared/disappeared** — earrings, glasses, watch

### Location Drift
- [ ] **Wall color changed** — white → cream → beige
- [ ] **Floor material shifted** — wood → tile → carpet
- [ ] **Window orientation changed** — light coming from wrong direction
- [ ] **Furniture appeared/disappeared** — extra chairs, missing table
- [ ] **Decor items changed** — different art, different plants
- [ ] **Time of day shifted** — golden hour → noon → blue hour
- [ ] **Weather changed** — clear → overcast → rainy
- [ ] **Space proportions shifted** — room looks bigger/smaller

### Product Drift
- [ ] **Color changed** — different hue or saturation
- [ ] **Shape distorted** — bottle taller/shorter, different silhouette
- [ ] **Logo/text changed** — wrong placement, wrong font, misspelled
- [ ] **Material appearance shifted** — glass → plastic, matte → glossy
- [ ] **Size relative to scene changed** — product too big/small
- [ ] **Details appeared/disappeared** — cap missing, pump broken
- [ ] **Packaging changed** — box, wrapper, labels different

### Lighting Drift
- [ ] **Key light direction changed** — left → right → behind
- [ ] **Color temperature shifted** — warm → cool or vice versa
- [ ] **Hardness changed** — soft → hard shadows or vice versa
- [ ] **Intensity changed** — bright → dim or vice versa
- [ ] **Number of light sources changed** — single → multiple
- [ ] **Rim/backlight appeared/disappeared**

### Motion/Style Drift
- [ ] **Camera angle inconsistent** — eye level → low angle → high angle
- [ ] **Depth of field changed** — sharp → blurred or vice versa
- [ ] **Film grain intensity varied** — heavy → light
- [ ] **Color grading shifted** — warm grade → cool grade
- [ ] **Motion style changed** — smooth → shaky

## Step 2: Diagnose the Root Cause

For each drift type found, identify WHY:

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Character face changes every shot | No anchor block or reference image | Add GOLD anchor + reference image |
| Product looks different angle-to-angle | Reference image only shows one angle | Generate multi-angle references |
| Lighting shifts between shots | Lighting not in anchor block | Add lighting anchor, specify time of day |
| Background elements appear/disappear | Location anchor too vague | Add specific location features to anchor |
| Style feels inconsistent | No style suffix in prompts | Add consistent style suffix to all prompts |
| Only happens in complex shots | Too many elements competing | Simplify shot, remove non-essential elements |
| Drifts over longer sequences | Model "forgets" early context | Add anchor block to EVERY shot, not just first |

## Step 3: Apply the Fix

### Fix Level 1: Strengthen the Prompt
Add more specific language to the anchor block:

```diff
- character: Maya, woman, brown hair
+ character: Maya — immutable: olive WARM undertone skin, EMERALD GREEN almond eyes,
+   dark CHOCOLATE brown hair in Loose side braid, subtle freckles across nose bridge
```

### Fix Level 2: Add Reference Images
```bash
brandly video <project> --reference-images "maya_face.png,maya_hair.png" --prompt "..."
```

### Fix Level 3: Reduce Shot Complexity
Break complex shots into simpler ones:

```
Before: "Maya walks through the kitchen picking up the perfume bottle and smelling it"
After: 
  Shot A: "Maya walks through kitchen" (character + location)
  Shot B: "Hand reaches for perfume bottle" (product close-up)
  Shot C: "Maya closes eyes, inhales" (emotion close-up)
```

### Fix Level 4: Regenerate References
If all else fails, regenerate the asset reference with more specific prompting:

```bash
brandly image --prompt "Character reference sheet: Maya, front/side/3/4 views,
  olive warm skin, emerald green eyes, dark brown hair in side braid,
  consistent lighting, clean background, professional reference sheet" \
  --style-preset photorealistic --size 4K
```

## Step 4: Verify the Fix

After applying fixes:

1. Generate 2-3 test shots
2. Run the drift checklist again on the outputs
3. If drift persists, escalate to next fix level
4. Once clean, document the working prompt structure in the production bible

## Prevention: The Pre-Flight Checklist

Before starting any generation batch:

- [ ] Anchor blocks written for all GOLD and SILVER assets
- [ ] Reference images generated and URLs saved
- [ ] Style suffix defined and consistent
- [ ] Shot prompts follow three-layer structure
- [ ] Lighting anchor specifies exact time of day
- [ ] Character immutable traits listed
- [ ] Product hero angles documented
- [ ] Total shot count within model coherence limits (max 6s per shot)
