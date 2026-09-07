---
name: brandly-mecha-sheet
description: >
  Create comprehensive mecha and robot reference sheets for AI video/image generation.
  Use when designing robots, machines, or mechanical beings for campaigns.
  Triggers on "mecha sheet", "robot design", "machine reference",
  "mechanical design", "cyborg prompt", "robot reference image",
  "industrial design", "sci-fi machine".
  NOT for mechatronics engineering (use mechanical engineer),
  NOT for 3D printing models (use dpf-blender-engineer).
---

# Brandly Mecha Sheet

Create comprehensive mecha reference sheets that ensure **consistent mechanical design** across all AI-generated content. Essential for sci-fi campaigns, tech products, and industrial design.

## When to Use

- Science fiction campaigns
- Technology product showcases
- Industrial design visualization
- Robotics concept art
- Futuristic machinery

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up mecha types | `references/mecha-types.md` |
| See technical diagrams | `references/technical-reference.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Mecha Sheet Structure

### 1. Basic Identification
```
Designation: [Model name/number]
Type: [Robot/Machine/Automaton/Cyborg]
Purpose: [Industrial/Combat/Service/Exploration]
Size Class: [Micro/Small/Medium/Large/Gigantic]
Scale: [Human-sized/Building-sized/Planetary]
```

### 2. Overall Architecture
```
Body Plan:
- Frame: [Bipedal/Quad/Hexapod/Wheeled/Tracked/Flying]
- Proportions: [Head/body/limb ratios]
- Stance: [Upright/Crouched/Hovering]

Structural System:
- Exoskeleton: [Exposed frame vs. enclosed]
- Chassis: [Material type, thickness]
- Joints: [Type, visibility, lubrication]
```

### 3. Materials & Finish
```
Primary Materials:
- Armor: [Metal alloy/ceramic/composite]
- Plating: [Type, finish]
- Wiring: [Exposed/concealed]

Surface Treatment:
- Paint: [Base color, accents]
- Weathering: [Scratches, rust, wear]
- Markings: [Logos, numbers, insignia]
- Panel lines: [Visible seams, maintenance access]
```

### 4. Component Details
```
Head/Sensor Array:
- Visual sensors: [Camera type, placement, color]
- Audio input: [Microphone arrays]
- Communication: [Antennas, transceivers]
- Status indicators: [LEDs, displays]

Limbs/Appendages:
- Arms: [Number, length, grip type]
- Hands/End effectors: [Claws/grippers/tools]
- Legs: [Length, joint types, feet]
- Special attachments: [Weapons/tools/modules]

Core Systems:
- Power source: [Location, type, indicator]
- Processing: [Central unit location]
- Cooling: [Vents, radiators]
```

### 5. Movement & Pose
```
Default Stance:
- Standing: [Balanced posture]
- Resting: [Energy-saving pose]
- Alert: [Ready position]

Movement Capabilities:
- Locomotion: [Walk/run/hover/fly]
- Speed: [Fast/slow/variable]
- Agility: [Precise/clumsy]
- Special movement: [Jump/double/transform]

Pose Reference:
- [List common poses for reference]
```

### 6. Lighting & Effects
```
Status Lights:
- Primary: [Color, location, meaning]
- Secondary: [Indicator lights]
- Emergency: [Alert patterns]

Energy Effects:
- Glow: [Type, color, intensity]
- Heat signature: [Infrared appearance]
- Electrical: [Arcs, sparks]
- Exhaust: [Type, visibility]
```

## Prompt Templates

### Mecha Portrait Prompt
```
[Mecha designation] mechanical unit.
[Body plan] with [materials description].
[Color scheme] with [weathering details].
[Sensor details] visible.
[Lighting effects] active.
Industrial design photography style.
Quality: [8K/Technical illustration/Photorealistic]
```

### Mecha Action Prompt
```
[Mecha] in [pose/action].
[Movement description].
[Environment context].
[Dust/debris effects].
[Cinematic lighting].
Action shot, [style descriptor].
Quality: [8K/Cinematic/Commercial]
```

### Technical Blueprint Prompt
```
Technical blueprint of [mecha designation].
[Wireframe/orthographic views].
[Dimension lines, annotations].
[Material callouts].
Engineering diagram style.
Quality: [Technical illustration/Blueprint]
```

## Usage with Brandly CLI

### Generate Mecha Reference
```bash
brandly image --prompt "[Mecha description], technical design" \
  --style-preset commercial \
  --size 4K
```

### Mecha in Scene
```bash
brandly video <project_id> \
  --prompt "[Mecha] [action] in [environment]" \
  --reference-images "https://example.com/mecha-ref.png" \
  --wait
```

### Multi-View Mecha Series
```bash
# Front view
brandly image --prompt "[Mecha] front view, technical rendering"

# Side view
brandly image --prompt "[Mecha] side profile, showing silhouette"

# Detail view
brandly image --prompt "Close-up of [mecha part], showing details"
```

## Quality Checklist

Before using a mecha sheet:

- [ ] Designation and purpose defined
- [ ] Structural system described
- [ ] Materials and finish specified
- [ ] Component details mapped
- [ ] Movement capabilities noted
- [ ] Lighting effects documented
- [ ] Reference images generated
- [ ] Consistency rules established

## Tips for AI Consistency

1. **Part Naming**: Use consistent terminology
2. **Reference Images**: Generate key angles first
3. **Material Lists**: Document exact finishes
4. **Lighting Rules**: Establish signature effects
5. **Scale References**: Include size comparisons

### Generate Mecha Reference (Recommended First Step)

For any mecha video or multi-asset campaign, generate a **mecha reference**
first via `brandly reference`. The reference is a GOLD-grade image that
locks the mecha appearance across all subsequent `brandly video` calls.

Mecha references are rendered as a **16:9 multi-view grid** — all
views in ONE image, split into three columns. This gives `brandly video`
multiple angles to lock onto for consistency across shots.

```bash
brandly reference <project_id> \
  --subject-type mecha \
  --subject "Bipedal combat mech, 4m tall, weathered titanium armor, glowing cyan optics" \
  --style-preset commercial \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/projects/<id>/artifacts/images/`
with the `reference_mecha_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

