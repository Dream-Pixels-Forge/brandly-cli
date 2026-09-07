---
name: brandly-animal-sheet
description: >
  Create comprehensive animal and insect reference sheets for AI video/image generation.
  Use when designing wildlife, pets, or creatures for campaigns.
  Triggers on "animal sheet", "creature design", "animal reference",
  "wildlife prompt", "insect design", "animal reference image",
  "pet photography", "wildlife documentary style".
  NOT for paleontology (use fossil specialist),
  NOT for taxidermy consultation (use wildlife photographer).
---

# Brandly Animal Sheet

Create comprehensive animal reference sheets that ensure **consistent species appearance** across all AI-generated content. Essential for wildlife documentaries, pet products, and creature design.

## When to Use

- Wildlife and nature campaigns
- Pet product advertising
- Creature design for fantasy/sci-fi
- Educational content
- Nature documentary styling

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up species accuracy | `references/species-guide.md` |
| See habitat contexts | `references/habitats.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Animal Sheet Structure

### 1. Basic Identification
```
Species: [Scientific and common name]
Type: [Mammal/Bird/Reptile/Amphibian/Fish/Insect]
Size: [Small/Medium/Large/XL]
Weight Range: [Approximate weight]
Lifespan: [Average lifespan]
```

### 2. Physical Characteristics
```
Body Shape:
- Overall build: [Streamlined/Round/Tall/Compact]
- Body proportions: [Head/body/limb ratios]
- Tail: [Length, thickness, appearance]

Head Features:
- Shape: [Round/Oval/Long/Square]
- Ears: [Size, shape, position]
- Eyes: [Size, shape, color, placement]
- Nose/Muzzle: [Shape, length, color]
- Mouth: [Lips, teeth visibility]

Limbs:
- Legs: [Length, muscle definition]
- Paws/Feet: [Size, pads, claws]
- Wings: [Size, shape, feather pattern] - if applicable
- Fins: [Size, shape, transparency] - if applicable
```

### 3. Coat/Fur/Feathers/Scales
```
Texture:
- Fur type: [Silky/Coarse/Wiry/Curly]
- Feather type: [Smooth/Fluffy/Technical]
- Scale type: [Smooth/Rough/Iridescent]

Color Pattern:
- Base color: [Primary coat color]
- Markings: [Stripes/Spots/Blazes/Tatches]
- Accent colors: [Ear tips, tail tip, paws]
- Underparts: [Belly, chest color]

Seasonal Variations:
- Summer coat: [Thinner, lighter]
- Winter coat: [Thicker, darker]
```

### 4. Distinguishing Features
```
Unique Markings:
- [Specific patterns that identify species]
- [Individual variations]

Special Features:
- Horns/Antlers: [Size, shape, branches]
- Tusks: [Size, curve, material]
- Crests/Manes: [Size, style]
- Bioluminescence: [Location, color] - if applicable

Size Comparisons:
- Relative to common objects
- Human height comparison
```

### 5. Behavior & Movement
```
Default Posture:
- Standing: [Tail position, ear position]
- Sitting: [Paw placement, tail curl]
- Walking: [Gait style, head position]

Movement Style:
- Walk: [Stride, speed, grace]
- Run: [Body extension, tail position]
- Special movements: [Flying/Swimming/Climbing]

Behavioral Notes:
- Typical expressions
- Alert vs. relaxed states
- Social behaviors
```

### 6. Habitat & Context
```
Natural Environment:
- Habitat type: [Forest/Desert/Ocean/Arctic/etc.]
- Climate: [Temperature, humidity]
- Terrain: [Mountains/Plains/Water/Urban]

Contextual Elements:
- Typical props: [Nests, burrows, dens]
- Surrounding flora: [Plants, trees]
- Weather conditions: [Common in habitat]
```

## Prompt Templates

### Wildlife Portrait Prompt
```
Wildlife portrait of [species].
[Body description] with [color pattern].
Natural habitat background: [environment].
[Time of day] lighting, [lighting quality].
Wild, natural behavior pose.
Quality: [8K/National Geographic style/Photorealistic]
```

### Pet Product Prompt
```
[Pet type] in [setting] with [product].
[Clean, healthy appearance description].
[Playful/calm expression].
[Studio/natural lighting].
Commercial quality, [style descriptor].
```

### Creature Design Prompt
```
Fantasy creature design.
Hybrid of [species A] and [species B].
[Mystical/magical elements].
[Epic/fantasy art style].
Detailed anatomy, [lighting style].
Quality: [Concept art/Photorealistic]
```

## Usage with Brandly CLI

### Generate Animal Reference
```bash
brandly image --prompt "Portrait of [species], [detailed description]" \
  --style-preset photorealistic \
  --size 4K
```

### Animal in Scene
```bash
brandly video <project_id> \
  --prompt "[Species] walking through [environment]" \
  --reference-images "https://example.com/animal-ref.png" \
  --wait
```

### Multi-Angle Animal Series
```bash
# Profile view
brandly image --prompt "Side profile of [animal], showing full body"

# Front view
brandly image --prompt "Front view of [animal], face detail"

# Action shot
brandly image --prompt "[Animal] in motion, dynamic pose"
```

## Quality Checklist

Before using an animal sheet:

- [ ] Species accurately identified
- [ ] Physical characteristics detailed
- [ ] Color patterns documented
- [ ] Behavior notes included
- [ ] Habitat context defined
- [ ] Reference images generated
- [ ] Consistency rules established

## Tips for AI Consistency

1. **Species Accuracy**: Use scientific names for precision
2. **Reference Images**: Always generate first
3. **Habitat Context**: Match environment to species
4. **Behavior Notes**: Include typical poses
5. **Save Variants**: Document seasonal changes

### Generate Animal Reference (Recommended First Step)

For any animal video or multi-asset campaign, generate a **animal reference**
first via `brandly reference`. The reference is a GOLD-grade image that
locks the animal appearance across all subsequent `brandly video` calls.

Animal references are rendered as a **16:9 multi-view grid** — all
views in ONE image, split into three columns. This gives `brandly video`
multiple angles to lock onto for consistency across shots.

```bash
brandly reference <project_id> \
  --subject-type animal \
  --subject "Adult golden retriever, warm coat, alert expression" \
  --style-preset photorealistic \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/projects/<id>/artifacts/images/`
with the `reference_animal_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

