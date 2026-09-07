---
name: brandly-production-bible
description: >
  Create the central project document that governs all visual and narrative
  decisions for a brandly-cli campaign. Use when starting a new project,
  onboarding a team, or as the single source of truth for a campaign.
  Triggers on "production bible", "project bible", "brand guidelines",
  "campaign bible", "style guide", "visual standards", "project document",
  "creative brief", "campaign documentation".
  NOT for individual asset sheets (use the specific sheet skills),
  NOT for shot planning (use brandly-storyboard).
---

# Brandly Production Bible

The production bible is the **single source of truth** for a campaign. It lives at the project root and contains every decision, reference, and rule that keeps the entire production consistent — characters, locations, products, lighting, color, audio, and editing standards.

## When to Use

- Starting any new campaign (create one per project)
- Onboarding a new team member or agent
- Handing off between production phases
- Ensuring cross-agent consistency in multi-agent pipelines
- Archiving decisions for future re-use

---

## Routing Table

| Want to... | Read |
|------------|------|
| Fill out the template | `references/bible-template.md` |
| See a completed example | `references/example-bible.md` |
| Understand asset relationships | `references/asset-map.md` |

---

## Bible Structure

### Section 1: Project Overview

```markdown
## 1. Project Overview

**Project Name:**  
**Campaign Goal:**  
**Target Audience:**  
**Platform(s):**  
**Total Budget (credits):**  
**Target Duration:**  
**Deadline:**  
**Style Preset (image `--style-preset`):** photorealistic / editorial / cinematic / commercial / documentary
**Video Style (`--style`):** cinematic / ugc / montage / multi_shot / continuous / unboxing / lifestyle
```

### Section 2: Creative Direction

```markdown
## 2. Creative Direction

### Mood
[3–5 words that capture the feeling: e.g., "warm, aspirational, clean"]

### Visual Tone
- Color direction: [e.g., warm neutrals with blue accents]
- Texture direction: [e.g., natural materials, soft focus, minimal grain]
- Light direction: [e.g., golden hour, soft studio, neon noir]

### Audio Direction
- Music style: [e.g., ambient electronic, orchestral swell, lo-fi beats]
- Voiceover: [yes/no, tone if yes]
- SFX style: [e.g., subtle, cinematic, realistic]
```

### Section 3: Brand Standards

```markdown
## 3. Brand Standards

### Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Primary | #HEX | Main branding |
| Secondary | #HEX | Accents |
| Neutral | #HEX | Backgrounds |
| Accent | #HEX | CTA, highlights |

### Typography
- Primary font: [name, usage]
- Secondary font: [name, usage]

### Logo Usage
- Placement: [where it appears, when]
- Size rules: [minimum size, safe area]
- Variants: [full color, white, inverse]
```

### Section 4: Character References

```markdown
## 4. Characters

### Character 1: [Name]
- Sheet file: `assets/character-sheets/[name].png`
- Key anchor traits: [3–5 features that never change]
- Wardrobe variants: [list if multiple outfits]
- Consistency rule: [what must stay identical across shots]

### Character 2: [Name]
...
```

### Section 5: Location References

```markdown
## 5. Locations

### Location 1: [Name]
- Sheet file: `assets/location-sheets/[name].png`
- Time of day: [golden hour/midday/blue hour/night]
- Key features: [elements that define this location]
- Consistency rule: [what must stay identical]
```

### Section 6: Object/Product References

```markdown
## 6. Products / Objects

### Product: [Name]
- Sheet file: `assets/object-sheets/[name].png`
- Hero angles: [front 3/4, side, detail]
- Colors/variations: [list]
- Logo placement: [exact position on product]
```

### Section 7: Shot Plan

```markdown
## 7. Shot Plan

[Link to brandly-storyboard output or embed abbreviated version]

| Shot # | Type | Duration | Prompt Summary | Assets Used | Status |
|--------|------|----------|----------------|-------------|--------|
| 1 | EST | 4s | City dawn, product reveal | location, product | ✅ |
| 2 | TRACK | 3s | Hand reaches for product | character, location, product | ⏳ |
```

### Section 8: Audio Plan

```markdown
## 8. Audio Plan

### Music
- Source: [generated/stock/licensed]
- Temp track URL: [if applicable]
- BPM: [tempo]
- Mood: [description]

### Voiceover
- Script: [full script]
- Voice type: [gender, age, tone]
- Timestamps: [when each line plays]

### SFX
- [List key sound effects with timestamps]
```

### Section 9: Editing Plan

```markdown
## 9. Editing Plan

### Final Cut Structure
[How shots will be assembled, transitions, timing]

### Transition Style
- [e.g., hard cuts, cross-dissolve, match cuts]

### Color Grade
- [Description of final grade look]

### Output Specs
- Format: [MP4/H.264/H.265]
- Resolution: [1080p/4K]
- Aspect ratio: [16:9/9:16/1:1]
- Frame rate: [24/30/60 fps]
```

### Section 10: Asset Inventory

```markdown
## 10. Asset Inventory

| Asset | Path | Generated | Last Updated |
|-------|------|-----------|--------------|
| Character 1 ref | assets/characters/... | date | date |
| Product ref | assets/products/... | date | date |
| Location ref | assets/locations/... | date | date |
| Shot 1 video | assets/videos/shot_01.mp4 | date | date |
| Shot 2 video | assets/videos/shot_02.mp4 | date | date |
```

---

## CLI Commands to Build the Bible

```bash
# Initialize a new project (creates bible skeleton)
brandly init --name "Campaign Name" --idea "Brief description" --style cinematic --shots 5 --budget 500

# Generate each asset sheet and update bible
brandly image --prompt "Character sheet: [description]" --style-preset photorealistic --size 4K
# → Record output URL in Section 4

brandly image --prompt "Location reference: [description]" --style-preset cinematic --size 4K
# → Record output URL in Section 5

# Generate storyboard, record in Section 7
brandly prompt -s "..." -a "..." -e "..." -n 5 --style cinematic

# Generate each shot, record in Section 10
brandly video <project_id> --prompt "SHOT 1..." --wait
```

---

## Maintenance Rules

1. **Update as you go** — fill in sections as assets are generated
2. **Never edit without recording** — when a shot changes, update the table in Section 7
3. **One source of truth** — the bible overrides any ad-hoc notes or conversations
4. **Version tag** — add a version number at the top, increment on changes
5. **Share with team** — this document travels with the project at every handoff

---

## Quality Checklist

Before starting generation:

- [ ] All sections filled (even if placeholder)
- [ ] Style preset chosen and documented
- [ ] Color palette defined with hex codes
- [ ] All character/object/location sheets planned
- [ ] Shot plan drafted in Section 7
- [ ] Audio direction noted in Section 8
- [ ] Output specs defined in Section 9
- [ ] Asset inventory table created (Section 10)
