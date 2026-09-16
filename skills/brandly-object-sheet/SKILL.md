---
name: brandly-object-sheet
description: >
  Create comprehensive object reference sheets for AI video/image generation.
  Use when designing products, props, or items for campaigns.
  Triggers on "object sheet", "product reference", "object design",
  "prop sheet", "product prompt", "product photography",
  "product reference image", "object consistency".
  NOT for packaging design (use graphic designer), NOT for 3D modeling (use dpf-blender-engineer).
---

# Brandly Object Sheet

Create comprehensive object reference sheets that ensure **consistent product appearance** across all AI-generated content. Essential for product photography, commercials, and brand campaigns.

## When to Use

- Product photography for campaigns
- Creating consistent product renders
- Designing props for scenes
- Generating product showcases
- Building visual libraries for brands

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up product categories | `references/product-categories.md` |
| See photography setups | `references/photography-setups.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Object Sheet Structure

### 1. Basic Information
```
Object Name: [Product/item name]
Category: [Electronics/Fashion/Food/Home/etc.]
Purpose: [How it's used]
Target Audience: [Who uses it]
Price Point: [Luxury/Mid-range/Budget]
```

### 2. Physical Specifications
```
Dimensions:
- Height: [measurement]
- Width: [measurement]
- Depth: [measurement]
- Weight: [weight]

Materials:
- Primary: [main material]
- Secondary: [accent materials]
- Finish: [matte/glossy/satin/textured]

Colors:
- Primary: [main color]
- Secondary: [accent colors]
- Variants: [available color options]
```

### 3. Visual Details
```
Shape:
- Overall form: [Geometric/Organic/Symmetrical/Asymmetrical]
- Edges: [Sharp/Rounded/Beveled]
- Silhouette: [Distinctive profile]

Surface Details:
- Texture: [Smooth/Rough/Patterned]
- Reflections: [High gloss/Matte/Satin]
- Transparency: [Opaque/Translucent/Transparent]
- Patterns: [Logos/Textures/Graphics]

Components:
- [List all visible parts]
- [Buttons/ports/details]
```

### 4. Branding & Markings
```
Logos:
- Primary logo: [placement, size, style]
- Secondary marks: [certifications, labels]
- Typography: [font style, placement]

Packaging:
- Box design: [colors, materials]
- Labels: [information, barcodes]
- Inserts: [manuals, accessories]
```

### 5. Context & Usage
```
Usage Scenarios:
- [How it's used in daily life]
- [Professional applications]
- [Special use cases]

Environment:
- Indoor/outdoor use
- Display settings
- Storage requirements
```

## Prompt Templates

### Product Photography Prompt
```
Professional product photography.
Subject: [Object name]
View: [Front/Side/3/4/Angle]
Background: [Color/material]
Lighting: [Studio/natural/dramatic]
Details: [Visible features to highlight]
Quality: [8K/UHD/Commercial]
Style: [Minimalist/Detailed/Luxury]
```

### Lifestyle Product Prompt
```
[Lifestyle context] scene featuring [object].
Object positioned: [how it's placed/used]
Interaction: [how person uses it]
Setting: [environment details]
Mood: [atmosphere/emotion]
Lighting: [natural/studio/warm]
Quality: [Photorealistic/Commercial]
```

### Macro Detail Prompt
```
Macro photography of [object].
Focus on: [specific detail]
Depth of field: [shallow/deep]
Lighting: [directional/soft/hard]
Background: [blurred/neutral]
Texture visibility: [high/medium/low]
Quality: [8K/Macro/Commercial]
```

## Usage with Brandly CLI

### Generate Product Image
```bash
brandly image --prompt "Product photography: [detailed description]" \
  --style-preset commercial \
  --size 4K \
  --ratio 1:1
```

### Mandatory Backdrop (all reference-sheet renders)
Every reference board **must** be rendered on a **seamless matte neutral mid-grey studio backdrop** with subtle thin grey divider lines — never a white, colored, busy, or in-scene background. This keeps cutouts clean, identity consistent, and avoids color spill. If a model ignores the backdrop, the quality gate (`brandly gate`) flags `matte_background` and the sheet should be regenerated.

### Generate Object Reference (Recommended First Step)

For any product video or multi-asset campaign, generate an **object
reference** first. The reference is a GOLD-grade image that locks the
product appearance across all subsequent `brandly video` calls.

Object references are rendered as a **16:9 multi-view grid** — all
views (front three-quarter, side profile, rear three-quarter) in ONE
image, split into three columns. This gives `brandly video` three
angles to lock onto for character consistency across shots.

```bash
brandly reference <project_id> \
  --subject-type object \
  --subject "Nike Air Max 1 sneaker, classic white colorway, visible Air cushioning unit, Swoosh logo" \
  --style-preset commercial \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/<project_id>/refs/`
with the `prop_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

### Product Showcase Video
```bash
brandly video <project_id> \
  --prompt "[Object] rotating slowly, studio lighting,
             clean background, premium product showcase" \
  --style cinematic \
  --wait
```

### Multi-Angle Product Series
```bash
# Front view
brandly image --prompt "Product front view, white background, studio lighting"

# Side view
brandly image --prompt "Product side view, showing profile and thickness"

# Detail view
brandly image --prompt "Macro shot of [specific detail], highlighting texture"
```

## Quality Checklist

Before using an object sheet:

- [ ] All dimensions specified
- [ ] Materials clearly defined
- [ ] Colors exact (with hex codes if possible)
- [ ] Branding details documented
- [ ] Usage context established
- [ ] Reference images generated
- [ ] Lighting style matched to campaign

## Tips for AI Consistency

1. **Specify Everything**: AI needs exact details
2. **Use References**: Generate and save product shots
3. **Document Variants**: Note color/style options
4. **Consistent Lighting**: Match lighting across shots
5. **Save Prompts**: Reuse successful prompt structures
