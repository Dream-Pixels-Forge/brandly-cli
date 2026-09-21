# Photoshop Workflow for Title Sequences

Step-by-step guide for creating the 9-artboard title sequence system in Photoshop.

---

## Document Setup

### Initial Configuration
```
File > New
├── Width: 1920px (HD) or 3840px (4K — preferred for premium work)
├── Height: 1080px (HD) or 2160px (4K)
├── Resolution: 72ppi (screen) or 150ppi (if frames may be printed)
├── Color Mode: RGB, 8-bit (16-bit if heavy color grading expected)
├── Background: Transparent or Black
├── Color Profile: sRGB IEC61966-2.1 (standard) or Rec. 709 (broadcast)
└── Artboards: ✓ Enabled
```

### Artboard Naming Convention
```
AB_01_MoodTone
AB_02_TypographyA_Primary
AB_03_TypographyB_Supporting
AB_04_CompositionA_CenteredHero
AB_05_CompositionB_OffCenter
AB_06_CompositionC_Environmental
AB_07_ColorLighting
AB_08_SequencePeak
AB_09_FinalTitleCard
```

### Layer Organization
```
📁 01_TITLE (group)
    ├── Title Text (text layer, vector)
    ├── Title Effects (adjustment layers, layer styles)
    └── Title Mask (if masked)
📁 02_SUPPORTING_TEXT (group)
    ├── Subtitle/Credits
    └── Legal/Billing
📁 03_BACKGROUND (group)
    ├── Base Color/Gradient
    ├── Texture
    └── Imagery
📁 04_ATMOSPHERE (group)
    ├── Grain/Noise
    ├── Light Leaks
    ├── Particles
    └── Vignette
📁 05_GUIDES (group)
    ├── Safe Areas (90% TV safe rectangle)
    ├── Center Lines
    └── Grid/Rule of Thirds
```

---

## Artboard-by-Artboard Workflow

### AB_01: Mood & Tone Board

**Setup:**
1. Create artboard: `AB_01_MoodTone`
2. Add 90% safe area guide (View > New Guide)
3. Background: Start with dominant color from your palette

**Workflow:**
1. **Color swatches** — Create 5-7 color swatches as shape layers
   - Primary (dominant mood color)
   - Secondary (complement or analogous)
   - Accent (contrast point — usually for title)
   - Shadow/depth (darkest tone)
   - Highlight (lightest tone)
   - 1-2 surprise colors (unexpected but fitting)

2. **Texture studies** — Add 2-3 texture references
   - Import as Smart Objects (non-destructive)
   - Set blending mode: Overlay, Soft Light, or Multiply
   - Opacity: 10-30% (subtle)

3. **Reference images** — 3-5 images that capture the mood
   - Place as Smart Objects
   - Add frame/border to distinguish as reference
   - Label with what aspect they represent

4. **Lighting study** — Small compositional element showing light direction
   - Gradient overlay on shape
   - Radial gradient for spotlight effect
   - Hard or soft edge (matches mood)

**Deliverable:** A board that communicates the emotional world of the title sequence.

### AB_02: Typography Study A — Primary Title

**Setup:**
1. Create artboard: `AB_02_TypographyA_Primary`
2. Background: Neutral (mid-gray or mood color at 20% opacity)
3. Add center guide and horizontal midline

**Workflow:**
1. **Type the title** — Use actual show/film name
2. **Create 4-6 variations:**
   - Variation 1: Font A, Bold/Black, centered
   - Variation 2: Font B, weight variation, tracking study
   - Variation 3: Font C, custom kerning, maybe stacked
   - Variation 4: Font A with effects (stroke, shadow, gradient fill)
   - Variation 5: Hand-lettered or custom-modified version
   - Variation 6: Wildcard — unexpected choice

3. **For each variation, test:**
   - Different tracking values (-50 to +200)
   - Different weights (Semibold through Black)
   - All caps vs. title case
   - Stacked (multiple lines) vs. single line

4. **Annotate each variation:**
   - Font name + weight
   - Size (px or pt equivalent)
   - Tracking value
   - Why this works (or doesn't)

**Layer tip:** Keep each variation as a separate text layer in a group called "Variations."
This makes it easy to toggle visibility and compare.

**Deliverable:** Clear recommendation for primary title typeface with rationale.

### AB_03: Typography Study B — Supporting Text

**Setup:**
1. Create artboard: `AB_03_TypographyB_Supporting`
2. Place approved primary title from AB_02 (linked Smart Object)
3. Background: From AB_01 mood palette

**Workflow:**
1. **Add supporting text elements:**
   - Episode title (if applicable)
   - "Created by / Directed by" credit
   - Main cast names
   - Network/platform bug
   - "Based on..." (if applicable)

2. **Test typeface pairings:**
   - Pairing should complement, not compete
   - Supporting should be 40-60% the visual weight of primary
   - Test 3-4 pairings side by side

3. **Hierarchy map:**
   - Primary title: 100% (largest, heaviest)
   - Episode title: 40-50%
   - Credits: 25-35%
   - Legal: 15-20%

**Deliverable:** Supporting typeface selected, hierarchy established, all text elements placed.

### AB_04: Composition A — Centered Hero

**Setup:**
1. Create artboard: `AB_04_CompositionA_CenteredHero`
2. Background: From AB_01 mood palette
3. Add center guides (vertical + horizontal)

**Workflow:**
1. **Place primary title** — Dead center
2. **Build composition outward:**
   - Title at 100% visual weight
   - Supporting text below, 40-50% size
   - Background treatment (gradient, texture, or imagery)
   - Atmospheric elements (grain, light, particles)

3. **Test variations:**
   - Pure centered (title only on blank)
   - Centered + gradient background
   - Centered + texture
   - Centered + dramatic lighting from above

**Deliverable:** Polished centered hero composition ready for animation handoff.

### AB_05: Composition B — Off-Center Dynamic

**Setup:**
1. Create artboard: `AB_05_CompositionB_OffCenter`
2. Add rule-of-thirds grid guides

**Workflow:**
1. **Place title off-center** — At a thirds intersection or along diagonal
2. **Balance with visual weight:**
   - If title is upper-right, place visual mass lower-left
   - Use imagery, texture, or secondary elements as counterweight

3. **Create diagonal energy:**
   - Implicit or explicit lines leading to title
   - Elements arranged along diagonal axis
   - Avoid horizontal/vertical alignment where possible

4. **Test variations:**
   - Rule of thirds placement
   - Extreme corner placement
   - Split-frame composition

**Deliverable:** Dynamic off-center composition with clear visual flow.

### AB_06: Composition C — Environmental Integration

**Setup:**
1. Create artboard: `AB_06_CompositionC_Environmental`
2. Import environment imagery or create abstract environment

**Workflow:**
1. **Build environment first:**
   - Background scene/world/atmosphere
   - Lighting within the environment
   - Depth layers (foreground, midground, background)

2. **Integrate title:**
   - Title should feel part of the scene
   - Use layer blending modes (Overlay, Screen, Soft Light)
   - Add shadows cast by environmental elements onto title
   - Consider 3D perspective (title receding into scene)

3. **Test variations:**
   - Title embedded in architecture
   - Title within natural environment
   - Title in abstract/impossible space

**Deliverable:** Immersive composition where title and environment are inseparable.

### AB_07: Color & Lighting Study

**Setup:**
1. Create artboard: `AB_07_ColorLighting`
2. Duplicate strongest composition from AB_04-06

**Workflow:**
1. **Create 3-4 color variations:**
   - Variation 1: Primary palette from AB_01
   - Variation 2: Warm shift (more amber, red, gold)
   - Variation 3: Cool shift (more blue, teal, cyan)
   - Variation 4: Unexpected (complementary or triadic)

2. **For each variation:**
   - Use adjustment layers (Hue/Saturation, Color Balance, Gradient Map)
   - Keep non-destructive — toggle to compare
   - Note the mood shift each palette creates

3. **Lighting progression:**
   - How does light change through the sequence?
   - Start dim → build to reveal → resolve (common arc)
   - Or: bright → darken → title emerges from shadow (horror arc)

**Deliverable:** Color palette finalized, lighting progression mapped.

### AB_08: Sequence Peak

**Setup:**
1. Create artboard: `AB_08_SequencePeak`
2. This is the most complex, visually rich frame

**Workflow:**
1. **Identify the peak moment:**
   - Most elements visible simultaneously
   - Maximum visual complexity
   - The "money shot" — what stops the scroller

2. **Build the frame:**
   - All major visual elements present
   - Title may be partially revealed or fully visible
   - Atmospheric effects at peak intensity
   - Lighting at its most dramatic

3. **Check complexity:**
   - Should feel rich, not cluttered
   - Title still readable
   - Eye has a clear path through the frame

**Deliverable:** Single frame that represents the sequence at its most unskippable.

### AB_09: Final Title Card

**Setup:**
1. Create artboard: `AB_09_FinalTitleCard`
2. This is the resolved, iconic final frame

**Workflow:**
1. **Assemble final composition:**
   - Approved title typography (from AB_02)
   - Approved supporting text (from AB_03)
   - Approved composition (from AB_04-06, strongest)
   - Approved color/lighting (from AB_07)
   - Peak atmosphere (informed by AB_08, but resolved)

2. **Polish everything:**
   - Manual kern the title — every pair
   - Color grade the full composition
   - Check at actual size (1920×1080 or 4K)
   - Check at thumbnail size (320px wide)
   - Add platform/network bugs in correct position

3. **Export for review:**
   - PNG for digital review
   - PDF for client presentation
   - PSD archived with all layers intact

**Deliverable:** Production-ready final title card. The frame that becomes the thumbnail.

---

## Photoshop Scripts for Title Sequences

### Built-in Scripts
- **File > Scripts > Image Processor** — Batch export artboards at multiple sizes
- **File > Export > Export As** — Export all artboards as PNG/JPG
- **Layer > Align/Distribute** — Precise positioning for centered compositions

### Useful Actions to Record
1. **Export All Artboards** — Action that exports each artboard at 1x and 0.5x
2. **Add Safe Area Guides** — Action that creates 90% TV safe rectangle on any artboard
3. **Apply Film Grain** — Action that adds standardized grain structure
4. **Create Thumbnail** — Action that resizes, flattens, and saves a 320px-wide version

### Keyboard Shortcuts to Customize
```
Artboard Tool: V (toggle with Move Tool)
Next Artboard: ]
Previous Artboard: [
Export Artboard: Assign to Cmd+Opt+E (Mac) / Ctrl+Alt+E (Win)
```

---

## Export Settings for Handoff

### For After Effects Import
```
File > Export > Export As > PSD
├── ✓ Layers: All layers (not flattened)
├── ✓ Maximize Compatibility
├── Color Profile: Embedded (sRGB or Rec. 709)
└── Bit Depth: Match source (8-bit or 16-bit)
```

### For Client Review
```
File > Export > Export As > PNG
├── Resolution: 1920×1080 (or 4K if applicable)
├── All 9 artboards exported individually
└── Naming: projectname_AB0X_description.png
```

### For Thumbnail/Marketing
```
File > Export > Export As > JPG
├── Width: 1280px (YouTube thumb) or 1920px (hero image)
├── Quality: 80-90%
└── Only AB_09 (Final Title Card)
```
