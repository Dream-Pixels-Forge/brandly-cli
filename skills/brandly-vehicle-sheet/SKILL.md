---
name: brandly-vehicle-sheet
description: >
  Create comprehensive vehicle reference sheets for AI video/image generation.
  Use when designing cars, trucks, aircraft, or transportation for campaigns.
  Triggers on "vehicle sheet", "car reference", "transportation design",
  "automotive prompt", "vehicle photography", "car reference image",
  "auto commercial", "vehicle design".
  NOT for automotive engineering (use mechanical engineer),
  NOT for car restoration (use classic car expert).
---

# Brandly Vehicle Sheet

Create comprehensive vehicle reference sheets that ensure **consistent mechanical design** across all AI-generated content. Essential for automotive campaigns, logistics content, and transportation visualization.

## When to Use

- Automotive advertising
- Transportation logistics content
- Vehicle review campaigns
- Mobility product launches
- Travel and tourism visuals

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up vehicle types | `references/vehicle-types.md` |
| See photography angles | `references/shot-angles.md` |
| Reference prompt variations | `references/prompt-variants.md` |

---

## Vehicle Sheet Structure

### 1. Basic Identification
```
Vehicle Name: [Make/Model/Designation]
Type: [Car/Truck/SUV/Van/Aircraft/Boat/Bicycle]
Class: [Economy/Compact/Mid-size/Luxury/Performance]
Year/Generation: [Model year or design era]
Market Segment: [Target audience]
```

### 2. Exterior Dimensions
```
Overall:
- Length: [mm/inches]
- Width: [mm/inches]
- Height: [mm/inches]
- Wheelbase: [measurement]
- Ground clearance: [measurement]

Weight:
- Curb weight: [kg/lbs]
- Payload capacity: [kg/lbs]
- Towing capacity: [kg/lbs] - if applicable
```

### 3. Body & Styling
```
Body Style:
- Configuration: [Sedan/Hatchback/SUV/Truck/Coupe/Convertible]
- Roofline: [Sloping/Boxy/Raked]
- Window line: [Character line, belt line]

Front End:
- Grille: [Size, shape, pattern]
- Headlights: [Shape, technology, placement]
- Bumper: [Style, intakes, fog lights]
- Hood: [Creases, vents, scoop]

Side Profile:
- Character lines: [Sharp/Soft/Complex]
- Wheel arches: [Flared/Subtle/Integrated]
- Door handles: [Flush/Traditional/Hidden]
- Mirrors: [Shape, integration]

Rear End:
- Taillights: [Shape, technology, connection]
- License plate: [Position, integration]
- Exhaust: [Tip style, placement]
- Spoiler: [Integrated/Added]
```

### 4. Materials & Finish
```
Paint:
- Base color: [Exact color name]
- Finish: [Gloss/Matte/Satin/Metallic]
- Accent colors: [Roof, mirrors, trim]
- Two-tone: [If applicable]

Trim & Accents:
- Chrome: [Window trim, grille, exhaust]
- Black: [Roof, pillars, inserts]
- Body-colored: [Bumpers, handles]
- Carbon fiber: [Elements, trim]
```

### 5. Wheels & Tires
```
Wheel Design:
- Size: [Diameter x width]
- Material: [Alloy/Chrome/Black]
- Spoke pattern: [5-spoke/10-spoke/Turbine/etc.]
- Finish: [Polished/Machined/Painted]

Tire Specs:
- Size: [Width/Aspect ratio/Rim]
- Type: [All-season/Performance/Off-road]
- Sidewall: [Low-profile/Standard]
```

### 6. Lighting & Technology
```
Exterior Lights:
- Daytime running lights: [Shape, position]
- Turn signals: [Integrated/Sequential]
- Ambient lighting: [Underglow, ground projection]

Interior Lights:
- Dashboard: [Illumination style]
- Ambient: [Color, zones]
- Display: [Screen size, type]
```

## Prompt Templates

### Vehicle Hero Shot Prompt
```
[Vehicle type] [color] [generation].
[Body style] with [distinctive features].
[Wheel design] with [tire type].
[Setting: studio/garage/road/nature].
[Lighting: studio/natural/dramatic].
Automotive photography style.
Quality: [8K/Commercial/Professional]
```

### Vehicle in Motion Prompt
```
[Vehicle] driving on [road/environment].
[Motion blur effect].
[Dynamic angle]: [low/front/side/rear].
[Dust/water spray effects] if applicable.
Action photography style.
Quality: [8K/Cinematic/Commercial]
```

### Detail Shot Prompt
```
Close-up of [vehicle part].
[Headlight/grille/wheel/interior detail].
[Material texture visible].
[Studio lighting].
Macro automotive photography.
Quality: [8K/Detail/Commercial]
```

## Usage with Brandly CLI

### Generate Vehicle Reference
```bash
brandly image --prompt "[Vehicle description], automotive photography" \
  --style-preset commercial \
  --size 4K
```

### Vehicle in Scene
```bash
brandly video <project_id> \
  --prompt "[Vehicle] [action] in [environment]" \
  --reference-images "https://example.com/vehicle-ref.png" \
  --wait
```

### Multi-Angle Vehicle Series
```bash
# Front 3/4 view
brandly image --prompt "[Vehicle] front three-quarter view, dynamic"

# Side profile
brandly image --prompt "[Vehicle] side profile, clean background"

# Rear view
brandly image --prompt "[Vehicle] rear view, showing taillights"

# Interior
brandly image --prompt "[Vehicle] interior, dashboard and seats"
```

## Common Vehicle Types

### Luxury Sedan
```
Focus: Elegance, comfort, status
Key elements:
- Sleek lines
- Premium materials
- Refined details
- Quiet, composed presence
- Executive styling
```

### Sports Car
```
Focus: Performance, excitement, speed
Key elements:
- Aggressive stance
- Aerodynamic features
- Large wheels
- Low profile
- Dynamic lighting
```

### SUV/Adventure
```
Focus: Capability, space, versatility
Key elements:
- Rugged styling
- Roof rails
- All-terrain tires
- High ground clearance
- Family-friendly
```

### Electric Vehicle
```
Focus: Technology, sustainability, innovation
Key elements:
- Aerodynamic shape
- LED lighting
- Minimal grille
- Tech displays
- Futuristic details
```

## Quality Checklist

Before using a vehicle sheet:

- [ ] Make/model specified
- [ ] Dimensions documented
- [ ] Color exact (with code if possible)
- [ ] Wheel design detailed
- [ ] Lighting elements noted
- [ ] Setting/context defined
- [ ] Reference images generated
- [ ] Consistency rules established

## Tips for AI Consistency

1. **Color Accuracy**: Use manufacturer color names
2. **Reference Images**: Generate key angles first
3. **Setting Consistency**: Match environment to vehicle class
4. **Lighting Rules**: Establish signature lighting style
5. **Save Presets**: Reuse successful prompt structures

### Mandatory Backdrop (all reference-sheet renders)
Every reference board **must** be rendered on a **seamless matte neutral mid-grey studio backdrop** with subtle thin grey divider lines — never a white, colored, busy, or in-scene background. This keeps cutouts clean, identity consistent, and avoids color spill. If a model ignores the backdrop, the quality gate (`brandly gate`) flags `matte_background` and the sheet should be regenerated.

### Generate Vehicle Reference (Recommended First Step)

For any vehicle video or multi-asset campaign, generate a **vehicle reference**
first via `brandly reference`. The reference is a GOLD-grade image that
locks the vehicle appearance across all subsequent `brandly video` calls.

Vehicle references are rendered as a **16:9 multi-view grid** — all
views in ONE image, split into three columns. This gives `brandly video`
multiple angles to lock onto for consistency across shots.

```bash
brandly reference <project_id> \
  --subject-type vehicle \
  --subject "Vintage Porsche 911, silver, clean restoration" \
  --style-preset commercial \
  --size 2K \
  --ratio 16:9
```

The generated reference is saved to `.brandly/<project_id>/images/<category>/`
with the `vehicle_*` prefix and is auto-injected as the first
reference image (strongest influence) in every `brandly video` call.
Pass `--require-reference` to `brandly video` to fail-fast when the
reference is missing.

