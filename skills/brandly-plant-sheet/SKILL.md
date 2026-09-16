---
name: brandly-plant-sheet
description: >
  Create comprehensive plant and nature reference sheets for AI video/image generation.
  Use when designing botanical scenes, gardens, or natural environments.
  Triggers on "plant sheet", "botanical reference", "garden design",
  "nature scene", "flora prompt", "plant reference image",
  "botanical illustration", "garden photography".
  NOT for horticulture consulting (use gardener),
  NOT for plant identification apps (use botanist).
---

# Brandly Plant Sheet

Create comprehensive plant reference sheets that ensure **consistent botanical accuracy** across all AI-generated content. Essential for nature campaigns, garden design, and environmental storytelling.

## When to Use

- Nature and environmental campaigns
- Garden and landscape design
- Botanical product advertising
- Food and agriculture content
- Interior design with plants

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up plant species | `references/plant-species.md` |
| See seasonal changes | `references/seasonal-reference.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Plant Sheet Structure

### 1. Basic Identification
```
Plant Name: [Common and scientific name]
Type: [Tree/Shrub/Flower/Grass/Vine/Fern/Succulent]
Origin: [Native region/habitat]
Growth Habit: [Upright/Spreading/Climbing/Trailing]
Mature Size: [Height x spread]
```

### 2. Stem & Trunk
```
Bark/Texture:
- Color: [Bark color, variations]
- Texture: [Smooth/Rough/Fissured/Peahled]
- Pattern: [Lichen, moss, lenticels]

Structure:
- Trunk shape: [Straight/Curved/Spiral]
- Branching: [Sparse/Dense/Ascending/Drooping]
- Branch angle: [Wide/Narrow/Horizontal]
```

### 3. Leaf Details
```
Leaf Shape:
- Overall: [Ovate/Lanceolate/Palmate/Needle-like]
- Margin: [Smooth/Lobed/Serrated]
- Tip: [Acute/Obtuse/Attenuate]

Leaf Arrangement:
- Pattern: [Opposite/Alternate/Whorled]
- Size: [Length x width]
- Thickness: [Thin/Leathery/Fleshy]

Leaf Color:
- Base: [Green shade, variations]
- Underside: [Lighter/Darker/Purple]
- Seasonal changes: [Spring/Summer/Fall/Winter]
```

### 4. Flower & Fruit
```
Flower Structure:
- Bloom type: [Single/Cluster/Bunch]
- Petal count: [Number, arrangement]
- Petal shape: [Oval/Spatulate/Frilled]
- Size: [Diameter range]

Flower Color:
- Primary: [Base petal color]
- Secondary: [Throat, center color]
- Gradient: [Color transitions]
- Varieties: [Color variants]

Fruit/Berries:
- Type: [Berry/Seed pod/Capsule]
- Color: [Ripe/unripe]
- Size: [Diameter]
- Duration: [Persistence on plant]
```

### 5. Root & Growth System
```
Root Type:
- Taproot/Fibrous/Adventitious
- Spread: [Depth, width]

Growth Pattern:
- Rate: [Fast/Moderate/Slow]
- Season: [Deciduous/Evergreen/Seasonal bloom]
- Dormancy: [Winter/Summer rest period]
```

### 6. Habitat & Care
```
Light Requirements:
- Full sun/Partial shade/Full shade

Soil Preferences:
- Type: [Well-draining/Clay/Sandy]
- pH: [Acidic/Neutral/Alkaline]

Water Needs:
- Frequency: [Daily/Moderate/Drought tolerant]
- Amount: [High/Medium/Low]

Climate:
- Hardiness zone: [Range]
- Temperature preference
- Humidity tolerance
```

## Prompt Templates

### Plant Portrait Prompt
```
Close-up of [plant name].
[Leaf description] with [color details].
[Flower details] in bloom.
[Garden/natural background].
[Lighting style].
Botanical illustration style or photography.
Quality: [8K/Macro/Commercial]
```

### Garden Scene Prompt
```
Lush garden featuring [plant type].
[Mixed planting scheme].
[Season] atmosphere.
[Lighting: dappled sunlight/soft overcast].
Depth of field: [shallow/deep].
Garden photography style.
Quality: [8K/Landscape/Commercial]
```

### Potted Plant Prompt
```
[Potted plant] in [container style].
[Placement: shelf/table/outdoor].
[Indoor/outdoor lighting].
[Decor style context].
Product photography style.
Quality: [8K/Commercial/Minimalist]
```

## Usage with Brandly CLI

### Generate Plant Reference
```bash
brandly image --prompt "[Plant description], botanical photography" \
  --style-preset photorealistic \
  --size 4K
```

### Plant in Scene
```bash
brandly video <project_id> \
  --prompt "[Scene] with [plant type] in background" \
  --reference-images "https://example.com/plant-ref.png" \
  --wait
```

### Seasonal Plant Series
```bash
# Spring bloom
brandly image --prompt "[Plant] in spring bloom, fresh green leaves"

# Summer full growth
brandly image --prompt "[Plant] at peak summer growth"

# Autumn colors
brandly image --prompt "[Plant] with fall foliage colors"

# Winter dormancy
brandly image --prompt "[Plant] in winter, bare branches"
```

## Common Plant Categories

### Indoor Houseplants
```
Focus: Home aesthetics, air purification
Key elements:
- Pot/container style
- Leaf pattern visibility
- Growth stage
- Light requirements
- Care level indication
```

### Garden Flowers
```
Focus: Color, seasonality, pollinators
Key elements:
- Bloom stage
- Color palette
- Garden context
- Pollinator presence
- Seasonal timing
```

### Trees & Shrubs
```
Focus: Structure, shade, year-round interest
Key elements:
- Bark texture
- Branch structure
- Canopy shape
- Seasonal changes
- Scale context
```

### Succulents & Cacti
```
Focus: Form, texture, water storage
Key elements:
- Leaf/fl mesh shape
- Spine/thorn details
- Color variations
- Flower emergence
- Desert context
```

## Quality Checklist

Before using a plant sheet:

- [ ] Scientific name included
- [ ] Growth habit described
- [ ] Leaf details specified
- [ ] Flower/fruit documented
- [ ] Care requirements noted
- [ ] Seasonal variations mapped
- [ ] Reference images generated
- [ ] Consistency rules established

## Tips for AI Consistency

1. **Species Accuracy**: Use scientific names
2. **Growth Stage**: Note current stage
3. **Season Context**: Match to time of year
4. **Lighting**: Specify natural light type
5. **Save References**: Archive by season

### Mandatory Backdrop (all reference-sheet renders)
Every reference board **must** be rendered on a **seamless matte neutral mid-grey studio backdrop** with subtle thin grey divider lines — never a white, colored, busy, or in-scene background. This keeps cutouts clean, identity consistent, and avoids color spill. If a model ignores the backdrop, the quality gate (`brandly gate`) flags `matte_background` and the sheet should be regenerated.

### Generate Plant Reference (Recommended First Step)

For any plant video or multi-asset campaign, generate a **plant reference**
first via `brandly reference`. The reference is a GOLD-grade image that
locks the plant appearance across all subsequent `brandly video` calls.

Plant references are rendered as a **16:9 multi-view grid** — all
views in ONE image, split into three columns. This gives `brandly video`
multiple angles to lock onto for consistency across shots.

```bash
brandly reference <project_id> \
  --subject-type plant \
  --subject "Monstera deliciosa, mature, large fenestrated leaves" \
  --style-preset photorealistic \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/<project_id>/refs/`
with the `plant_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

