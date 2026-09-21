---
name: brandly-title-sequence
description:
  Title-sequence and opening-credits design for product videos, commercials and
  brand campaigns produced with brandly-cli. Delivers design specs — typography
  pairing, composition layouts, title storyboards, mood boards and a skip-proof
  memorability analysis — that feed `brandly prompt` / `brandly image` /
  `brandly video` generation of the title cards. Use when designing title
  sequences, opening credits, show intros or episode intros for video made with
  the brandly pipeline. NOT a Photoshop/After Effects execution skill (the
  artboard/AE specs are manual design work outside the CLI); NOT for logo
  design, print, or web hero sections.
---

# Title Sequence

Premium title sequence design — from Photoshop visual prototype through After Effects animation
to final delivery. This skill ensures every title sequence has **storytelling intent, emotional
resonance, and skip-proof memorability**.

> "A truly beautiful and engaging design has the potential to disincentivise skipping entirely."
> — Chris Sharpe, Territory Studio

## Using the Outputs with brandly-cli

This skill produces **design specs**; brandly-cli generates the pixels:

- Title-card **mood boards / concept frames** → generate with
  `brandly image --prompt "..." --style-preset <preset>` (no project needed).
- **Title storyboards** → convert to a shot list and generate the motion takes
  with `brandly produce <project_id> --shots shots.json` (one shot at a time,
  1 request/minute; clips land as `Scene-XX-Shot-X-Y.mp4`).
- Title **typography / composition / After-Effects specs** are manual design
  work outside the CLI — hand them to the human designer with the generated
  concept frames attached.

---

## How to Use This Skill (Read This First)

### Step 1: Read the Relevant Reference Files

This skill has layered reference documents. **Before generating output, read the files that match the user's task:**

| User's Request                                                   | Read These Reference Files                                 |
| ---------------------------------------------------------------- | ---------------------------------------------------------- |
| Typography-focused (fonts, pairings, type animation)             | `references/typography-guide.md`                           |
| Composition-focused (layouts, visual hierarchy, genre matching)  | `references/composition-patterns.md`                       |
| Photoshop workflow (artboard setup, layer organization, export)  | `references/photoshop-workflow.md`                         |
| After Effects animation (text animators, expressions, rendering) | `references/after-effects-pipeline.md`                     |
| Full project (all phases)                                        | Read ALL reference files — they cross-reference each other |

If unsure, read all four. Trends cross-pollinate between domains.

Triggers for: Territory Studio style, Saul Bass inspired, James Bond titles, Saul Bass Psycho,
Man with a Golden Arm, streaming title sequence, skip button design, unskippable titles,
episode-specific title variations, title sequence strategy, title animation, opening sequence
concept, title design for film, title design for TV, title design for streaming, title design
for podcast, title sequence typography, title composition layout, title After Effects animation,
title sequence Photoshop, opening credits design, cinematic title treatment.
Also trigger when: user mentions designing opening or title sequences for any visual media
(film, TV, streaming series, podcast, documentary, indie film, animation); needs typography
pairing specifically for title text (not menus, not logos, not body copy); wants to create
titles that survive the skip button; building episode-specific title variations; designing
titles that build suspense or tease narrative; any project where the opening/title sequence
needs to be memorable enough that audiences choose to watch rather than skip; user asks about
how famous title sequences were designed (Saul Bass, Bond, Alien, Stranger Things, Game of Thrones,
True Detective, Westworld); user mentions Territory Studio approach to titles; user needs
After Effects animation specs for title text; user wants Photoshop artboard system for title
exploration.
Do NOT trigger for: YouTube channel intros (too simple for this skill); logo design or brand
identity (not title sequences); print design like menus, posters, business cards; general
typography questions unrelated to title text; website hero sections or landing pages; general
color palette questions; code debugging or development tasks.
Use PROACTIVELY whenever title sequences, opening credits, or premium title design is mentioned.

### Step 2: Follow the Mandatory Output Structure

**Every output MUST include all six sections below.** This ensures nothing is missed — especially the skip-button test, which is the defining quality gate for title sequences.

```markdown
## 1. Research & Understanding Brief

[3-5 sentences: narrative premise, key themes, audience, platform constraints, competitive differentiation]

## 2. The 9 Artboards

[Each artboard described with: purpose, visual elements, composition details, design decisions with rationale. Reference specific artboard types from the 9-artboard system.]

## 3. Typography Selection

[Primary font with specific name, weight, size, tracking. Secondary/supporting font. Pairing rationale. Reference the typography guide for genre-appropriate choices.]

## 4. After Effects Animation Specifications

[For each animated composition: duration, entry animation, exit animation, easing curves, layer animation, audio sync points, transition to next. Reference the AE pipeline guide for techniques.]

## 5. Skip-Button Test Analysis

[Mandatory section. Evaluate each unskippable factor: visual beauty, narrative teasing, emotional priming, novelty, episode-specific content. Also evaluate skippable risks: too long, repetitive, generic, poor typography. Include timeline analysis showing what viewer sees at skip-button appearance time (typically 5s for streaming).]

## 6. Cross-References & Next Steps

[Link to relevant DPF skills (dpf-concept-art, dpf-trends, movematics). Suggest next steps: episode variations, color progression, AE production notes.]
```

### Why This Structure Matters

- **Section 5 (Skip-Button Test) is NOT optional.** Every title sequence design lives or dies by whether audiences skip it. If you skip this section, you haven't completed the task.
- **Section 4 (AE Specs) must be specific.** Vague animation notes like "animate the title" are useless. Specify: which animator, which easing curve, which duration, which audio cue.
- **Section 3 (Typography) must name real fonts.** Don't suggest "a clean sans-serif" — name the specific font (e.g., "Space Grotesk Medium, tracking +80").

---

## Why This Matters

Title sequences are one of cinema's oldest and most iconic crafts. James Bond fans eagerly
anticipate their slick title designs. Star Wars' rising text is as memorable as its lightsabers.
But in the streaming era, the **skip button** threatens their existence.

This skill solves that challenge. It produces title sequences so visually compelling, so
emotionally resonant, that audiences _choose_ to watch them.

### The Stakes

- **75% of viewers** judge content quality by its opening design (parallel to Stanford web credibility study)
- **Binge-watching** creates strong incentive to skip intermissions
- **Behavioral data** (skip rate, completion time) drives platform creative decisions
- **AI generative tools** can produce mediocre titles at scale — human artistry is the differentiator

---

## The 9-Artboard Photoshop System

Every title sequence project creates **9 Photoshop artboards**, each serving a distinct purpose
in the design pipeline. This mixed approach ensures comprehensive visual exploration.

### Artboard 1: Mood & Tone Board

**Purpose:** Establish the emotional atmosphere and visual language of the title sequence.

**What to include:**

- Color palette swatches (primary, secondary, accent)
- Texture references and material studies
- Lighting mood (dramatic, ethereal, high-contrast, muted)
- Key visual metaphors (what does the sequence feel like?)
- 3-5 reference images that capture the desired emotion

**Design questions answered:**

- What emotion should the audience feel before the story begins?
- Does this mood match the narrative's tone?
- Is it distinct enough to be memorable?

### Artboard 2: Typography Study A — Primary Title

**Purpose:** Explore the main title typography — the show/film name as hero element.

**What to include:**

- 4-6 font pairings for the primary title
- Scale studies (how large does it dominate the frame?)
- Letterform treatments (kerning, tracking, custom modifications)
- Hierarchy tests (what's the reading order? what's emphasized?)
- Integration with background elements

**Design questions answered:**

- Does the typeface carry the right personality?
- Is it legible at screen size?
- Does it feel premium and intentional?

### Artboard 3: Typography Study B — Supporting Text

**Purpose:** Design secondary text elements — episode titles, credits, taglines, billing blocks.

**What to include:**

- Supporting typeface (complements primary without competing)
- Size hierarchy relative to primary title
- Placement studies (where does secondary text live?)
- Animation-friendly considerations (will this text animate on/off?)

### Artboard 4: Composition Layout A — Centered Hero

**Purpose:** Title centered, dominant, with supporting elements radiating outward.

**What to include:**

- Central focal point composition
- Symmetrical or near-symmetrical balance
- Negative space as design element
- Background treatment (gradient, texture, imagery, abstract)

**When to use:** Epic, iconic, statement-making titles (James Bond, Star Wars)

### Artboard 5: Composition Layout B — Off-Center Dynamic

**Purpose:** Asymmetrical composition with title integrated into visual flow.

**What to include:**

- Rule of thirds or golden ratio placement
- Diagonal movement lines leading to title
- Visual weight balanced across frame
- Title as part of larger composition, not isolated

**When to use:** Artistic, mysterious, atmospheric titles (Alien, True Detective)

### Artboard 6: Composition Layout C — Environmental Integration

**Purpose:** Title woven into the scene/world of the content.

**What to include:**

- Title embedded in environment (architecture, nature, abstract space)
- Lighting interacts with letterforms
- Depth and parallax layers visible
- World-building through title treatment

**When to use:** Immersive, world-building titles (Game of Thrones, Westworld)

### Artboard 7: Color & Lighting Study

**Purpose:** Dedicated exploration of color narrative and lighting progression.

**What to include:**

- 3-4 color variations of the same composition
- Lighting progression (how does light change through the sequence?)
- Contrast studies (what pops? what recedes?)
- Color psychology alignment with narrative themes

**Design questions answered:**

- Does color tell part of the story?
- Is there enough contrast for readability?
- Do colors shift meaningfully through the sequence?

### Artboard 8: Sequence Flow Keyframe

**Purpose:** Single frame representing the middle/climax of the title sequence.

**What to include:**

- The most visually striking moment
- Peak complexity before resolution
- Elements in motion (implied through blur, trails, layering)
- The "money shot" — what makes viewers stop scrolling

**Design questions answered:**

- Is there a moment worth not skipping?
- Does this frame capture the sequence's peak energy?
- Would this stop a binge-watcher?

### Artboard 9: Final Title Card

**Purpose:** The resolved, polished final frame — what the audience remembers.

**What to include:**

- Complete composition with all elements
- Final typography (approved, refined, production-ready)
- Color grade locked
- Logo, network, or platform bugs positioned
- The frame that becomes the thumbnail/key art

**Design questions answered:**

- Is this iconic enough to represent the entire production?
- Does it work as a still image (marketing, thumbnails)?
- Would fans recognize it instantly?

---

## Design Pipeline: PS → AE → Final

### Phase 1: Research & Understanding (Before Photoshop)

**Duration:** 1-2 hours | **Output:** Brief document

1. **Understand the narrative** — What story are these titles introducing?
2. **Identify key themes** — What visual metaphors serve the story?
3. **Audience analysis** — Who watches this? What are their expectations?
4. **Platform constraints** — Resolution, aspect ratio, duration, skip-button context
5. **Competitive landscape** — What do similar titles look like? How do we differentiate?

> "The key is storytelling. It's an opportunity to affect the emotions of the audience
> through a unique medium." — Chris Sharpe

### Phase 2: Visual Exploration (Photoshop 9-Artboard System)

**Duration:** 4-8 hours | **Output:** 9 artboards as described above

1. **Start with mood** (Artboard 1) — establish emotion before form
2. **Typography first** (Artboards 2-3) — type is the hero of most title sequences
3. **Composition studies** (Artboards 4-6) — explore three distinct layout approaches
4. **Color narrative** (Artboard 7) — color tells half the story
5. **Sequence peak** (Artboard 8) — design the unskippable moment
6. **Final resolution** (Artboard 9) — the iconic frame

### Phase 3: Animation Specification (After Effects Handoff)

**Duration:** 2-3 hours | **Output:** AE project spec document

For each of the 9 artboards, define:

| Spec                   | Description                     | Example                                                        |
| ---------------------- | ------------------------------- | -------------------------------------------------------------- |
| **Duration**           | How long this frame holds       | 1.5s, 3s, 0.8s                                                 |
| **Entry animation**    | How elements enter              | Letter-by-letter reveal, mask wipe, dissolve from texture      |
| **Exit animation**     | How elements leave              | Fade through black, dissolve to next scene, hard cut           |
| **Easing curve**       | Motion personality              | Smooth (cubic-bezier), punch (elastic), dramatic (exponential) |
| **Layer animation**    | What moves independently        | Background parallax, text drift, particle overlay              |
| **Audio sync points**  | Where music/sfx hits            | Bass drop on title reveal, cymbal swell on transition          |
| **Transition to next** | How it flows to following frame | Morph, cut, dissolve, wipe, match action                       |

### Phase 4: After Effects Production

**Duration:** 8-20 hours | **Output:** Animated title sequence

**AE Workflow:**

1. **Import PSD artboards** as layered compositions (File > Import > File > Composition)
2. **Set up composition** — resolution, frame rate (24fps standard, 30fps broadcast), duration
3. **Animate typography** — text animators, range selectors, per-character 3D
4. **Add motion graphics** — shapes, particles, effects, camera moves
5. **Color grade** — Lumetri Color, adjustment layers, LUTs
6. **Sound design** — sync to music, add SFX, mix levels
7. **Render** — ProRes 422 for delivery, H.264 for review

**AE Scripts That Accelerate Work:**

- **Motion 4** (Mt. Mograph) — Advanced easing curves and motion presets
- **Ease and Wizz** — Free easing expressions for natural motion
- **Explode Shape Layers** — Break apart complex shapes for animation
- **True Comp Duplicator** — Duplicate compositions with all dependencies
- **Flow** — Visual easing curve editor
- **Overlord** — Illustrator ↔ AE workflow for vector graphics
- **Duik Bassel** — Character rigging (if titles include figures)

### Phase 5: Review & Refine

**Duration:** 2-4 hours | **Output:** Final approved sequence

1. **Skip test** — Watch it 5x in a row. Would _you_ skip it?
2. **Mute test** — Watch without sound. Does it still work visually?
3. **Thumbnail test** — Shrink to 100px wide. Is the title still readable?
4. **Fresh eyes test** — Show someone unfamiliar. What emotion do they feel?
5. **Platform test** — View on actual target device (TV, phone, tablet)

---

## Typography Selection Guide

**Before diving in:** Read `references/typography-guide.md` for deep font selection by genre,
animation patterns for each typeface category, and licensing guidance. The table below is a
quick reference; the reference file has the full treatment.

### Title Font Categories

| Category               | Personality                      | When to Use                                 | Examples                                  |
| ---------------------- | -------------------------------- | ------------------------------------------- | ----------------------------------------- |
| **Geometric Sans**     | Modern, clean, tech-forward      | Sci-fi, tech thrillers, corporate dramas    | Futura, Montserrat, Avenir Next           |
| **Humanist Sans**      | Warm, approachable, organic      | Human dramas, comedies, documentaries       | Gill Sans, Optima, Frutiger               |
| **Didone Serif**       | Elegant, luxurious, high-fashion | Period dramas, fashion content, prestige TV | Bodoni, Didot, Playfair Display           |
| **Slab Serif**         | Bold, confident, authoritative   | Action, westerns, powerful statements       | Rockwell, Clarendon, Roboto Slab          |
| **Display Serif**      | Ornate, decorative, atmospheric  | Fantasy, horror, gothic narratives          | Cormorant Garamond, Libre Baskerville     |
| **Handwritten/Script** | Personal, intimate, raw          | Indie films, memoirs, emotional content     | Caveat, Pacifico, custom lettering        |
| **Condensed Sans**     | Urgent, intense, compressed      | Thrillers, crime, fast-paced content        | Bebas Neue, Impact, DIN Condensed         |
| **Monospace**          | Digital, coded, system-based     | Tech, hacking, surveillance, AI themes      | JetBrains Mono, Space Mono, IBM Plex Mono |

### Font Pairing Rules for Titles

1. **Maximum contrast, minimum conflict** — Pair a distinctive display with a neutral body
2. **Same superfamily preferred** — If a font has multiple weights/styles, use within family
3. **x-height matching** — Supporting text should have similar x-height to primary
4. **Weight hierarchy** — Primary title should be 2-3 weights heavier than supporting
5. **One personality star** — Only one font should have strong character; others support

### Title-Specific Pairings (2026 Verified)

| Primary (Title)                   | Secondary (Supporting)       | Vibe                   |
| --------------------------------- | ---------------------------- | ---------------------- |
| **Playfair Display** (Bold)       | **Source Sans Pro** (Light)  | Prestige drama         |
| **Bebas Neue** (Regular)          | **Montserrat** (Light)       | Modern thriller        |
| **Cormorant Garamond** (Semibold) | **Inter** (Regular)          | Literary, atmospheric  |
| **Space Grotesk** (Medium)        | **JetBrains Mono** (Regular) | Tech, sci-fi           |
| **Oswald** (Bold)                 | **Lato** (Light)             | Bold, assertive        |
| **Abril Fatface** (Regular)       | **Nunito Sans** (Regular)    | Editorial, magazine    |
| **Syne** (Extra Bold)             | **DM Sans** (Regular)        | Contemporary, artistic |

---

## Composition Patterns

**Before diving in:** Read `references/composition-patterns.md` for deep analysis of iconic
title sequences (Bond, Alien, Saul Bass, Territory Studio), the genre-composition matrix,
and the Territory Studio episode-specific pattern. The patterns below are summaries;
the reference file has visual diagrams and detailed execution guidance.

### The Saul Bass Principle

> Simple geometric shapes + bold typography + unexpected arrangement = iconic

Saul Bass's titles for _Man with a Golden Arm_ (1955) and _Psycho_ (1960) remain influential
because they followed one rule: **reduce until only the essential remains, then make that
essential element unforgettable.**

**Apply this:** Start with complexity, then subtract until only the story's core remains.

### The Territory Studio Approach

> Unique content per episode = reason to keep watching

Territory Studio produced different title sequences for every episode of _The Man Who Fell
to Earth_, each referencing that episode's specific content. This gives viewers a reason
_not_ to skip — there's something new every time.

**Apply this:** Design a master template, then create episode-specific variations that tease
that episode's plot points through visual clues.

### The Alien Technique

> Slow reveal + random order = sustained tension

The Alien (1979) title sequence animates letterforms one at a time in random order, keeping
the reveal mysterious until the final transition. It builds atmosphere and primes the
audience for a narrative that builds tension.

**Apply this:** Don't reveal everything at once. Stagger the reveal. Make the audience wait
for it — anticipation is the point.

### The Bond Formula

> Consistent framework + changing visuals = anticipated event

James Bond titles are eagerly anticipated because they maintain a consistent structure
(song, silhouettes, thematic imagery) while varying the content. The framework is reliable;
the content is fresh.

**Apply this:** Create a recognizable title language for your production, then vary the
content within that language each time.

---

## The Skip-Button Test

**This is the defining quality gate.** Every design decision should pass this filter:
**"Would this make me not skip?"**

Read `references/composition-patterns.md` for the "Skip-Button Design Integration" section
and `references/after-effects-pipeline.md` for the 5 review tests.

### What Makes Titles Unskippable

| Factor                       | How to Achieve It                                 |
| ---------------------------- | ------------------------------------------------- |
| **Visual beauty**            | Craft so gorgeous you want to keep watching       |
| **Narrative teasing**        | Hints at plot points without spoiling             |
| **Emotional priming**        | Sets the mood so perfectly it enhances the story  |
| **Novelty**                  | Something you haven't seen before                 |
| **Episode-specific content** | New information or visuals unique to this episode |
| **Musical integration**      | Title and music are inseparable (Bond model)      |
| **Cultural moment**          | Title becomes part of the cultural conversation   |

### What Makes Titles Skippable

| Factor                                                 | How to Avoid It                                 |
| ------------------------------------------------------ | ----------------------------------------------- |
| **Generic design**                                     | Commit to a distinctive visual direction        |
| **Too long** — over 30s for series                     | Keep it tight; every second must earn its place |
| **Repetitive** — same every episode with no variation  | Add episode-specific visual clues               |
| **No narrative connection** — could belong to any show | Tie visuals directly to story themes            |
| **Poor typography** — bland or illegible type          | Invest in typography as the hero element        |
| **Cheap execution** — looks low-budget or rushed       | Production quality signals content quality      |

---

## AI Integration in Title Design

**Context:** This aligns with the Forge-Brain wiki's consensus from Chris Sharpe (Territory Studio)
and Eduardo Peña (Concept Art series). See `[[concepts/ai-in-creative-workflows.md]]` for the
full four-perspective analysis (Pinto, Peña, Palumbo, Sharpe).

### AI as Efficient Tool ✅

- Generate mood board reference images from text descriptions
- Explore color palette variations rapidly
- Create texture libraries for background treatments
- Speed up early ideation and thumbnail exploration
- Automate repetitive tasks (batch resizing, format conversion)

### AI Should NOT ✅

- Define the creative direction — intent comes from the designer
- Generate the final title sequence — it lacks emotional understanding
- Replace human judgment — taste and craft are irreplaceable
- Remove artistic voice — individuality is what makes titles memorable

> "The human experience and human emotion are what truly dictate the direction of an artist."
> — Chris Sharpe

---

## Cross-Skill Integration

| When Using                     | Add This For                                                      |
| ------------------------------ | ----------------------------------------------------------------- |
| `dpf-concept-art`              | Title sequences as visual storytelling within larger production   |
| `dpf-trends`                   | Current design trends, typography trends, composition patterns    |
| `movematics`                   | Animation principles, motion personality, easing curves           |
| `after-effects-scripts-master` | AE automation, scripting, workflow acceleration                   |
| `cinematic-scrolly`            | Scroll-driven narrative techniques applied to linear sequences    |
| `frontend-design`              | Title sequences as web hero sections (landing pages, promo sites) |
| `prototype-skill`              | Visual development process, research-first approach               |

---

## Quick Reference Card

| Step                           | Question                                   | Tool                                 |
| ------------------------------ | ------------------------------------------ | ------------------------------------ |
| 1. Research                    | What story are we telling?                 | Brief document                       |
| 2. Mood (Artboard 1)           | What emotion should the audience feel?     | Photoshop                            |
| 3. Typography (Artboards 2-3)  | Does the type carry the right personality? | Photoshop                            |
| 4. Composition (Artboards 4-6) | Which layout approach serves the story?    | Photoshop                            |
| 5. Color (Artboard 7)          | Does color tell part of the story?         | Photoshop                            |
| 6. Sequence Peak (Artboard 8)  | Is there a moment worth not skipping?      | Photoshop                            |
| 7. Final Card (Artboard 9)     | Is this iconic enough?                     | Photoshop                            |
| 8. AE Specs                    | How does everything move?                  | Spec document                        |
| 9. Animate                     | Bring it to life                           | After Effects                        |
| 10. Review                     | Would I skip this?                         | Skip test, mute test, thumbnail test |

---

## Featured Sources & Influences

- **Chris Sharpe** — Territory Studio Creative Director; pragmatic AI tool-user; episode-specific titles
- **Territory Studio** — Kingdom of Dreams, The Man Who Fell to Earth; motion-driven narrative titles
- **Saul Bass** — Man with a Golden Arm, Psycho; reductionist iconic design
- **James Bond franchise** — Consistent framework + changing visuals = cultural event
- **Alien (1979)** — Slow reveal, atmospheric tension, random-order letter animation

Source: "Don't Skip It: Designing a Title Sequence in the Age of AI" — Chris Sharpe (Motionographer, 2023)

---

## Next Steps

After applying this skill:

1. Review all 9 artboards against the skip-button test
2. Verify typography choices against the pairing rules
3. Confirm composition follows one of the proven patterns (or intentionally breaks them)
4. Check that AE specs are complete and unambiguous
5. Run all 5 review tests (skip, mute, thumbnail, fresh eyes, platform)
6. Iterate on what fails
