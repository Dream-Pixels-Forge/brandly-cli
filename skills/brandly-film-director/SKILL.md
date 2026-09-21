---
name: brandly-film-director
description: >
  Direct AI video like a film director — turn ideas, scripts, screenplays and
  concepts into production-grade, shot-by-shot prompts: camera direction,
  lighting design, visual style, shot planning, storyboarding, multi-shot
  prompt chaining, character consistency, aspect-ratio selection. Written for
  the brandly-cli pipeline (Agnes AI via `brandly video` / `brandly produce`);
  the prompt craft transfers to Veo, Kling, Sora and friends. Trigger for
  commercials, product videos, music/title videos, film scenes, social
  content, AI video generation. Use when the user has any video-creation or
  film-direction task. Every frame is directed — not generated. NOT for CLI
  execution mechanics (brandly-video-generation owns `brandly video` /
  `brandly produce`), video editing, 3D modeling, or programmatic video.
---

# Brandly Film Director — AI Video Prompt Engineering & Direction

Transform ideas into production-grade AI video prompts. This skill is the **director's lens** —
turning creative vision into precise, model-optimized instructions that AI video models can
execute with fidelity.

> "AI video is not about typing 'make a cool video.' It's about directing — shot by shot,
> light by light, motion by motion — with the same intentionality as a film director on set."

> **Pipeline note:** Pair with `brandly-video-generation` for CLI execution, `brandly-storyboard`
> for shot lists, `brandly-camera` for camera language, and `brandly-consistency` for asset locking.

**Complementary Skills:**

- **brandly-video-generation** → CLI execution with `brandly video` / `brandly produce`
- **brandly-storyboard** → shot lists the resumable produce runner consumes
- **brandly-camera** → camera language for shot grammar
- **brandly-consistency** → character and asset locking across shots

## Film Direction Process (8-Step Workflow)

This skill provides **8 steps for directing AI video**:

### Step 1: Classify Content Type

```
Determine: Cinematic/Film, Marketing, Music Video, Title Sequence, Animation, Product Demo, Social Media, Documentary
```

### Step 2: Select Target Model

| Model                | Best For               | Consider          |
| -------------------- | ---------------------- | ----------------- |
| **Veo 3.1**          | Highest quality, audio | Native dialogue   |
| **Seedance 1.5 Pro** | First-frame control    | Audio-visual sync |
| **Wan 2.5**          | Image-to-video         | Open-source       |
| **Runway Gen-4**     | Cinematic camera       | Camera control    |
| **Kling 3.0**        | Realistic motion       | Long duration     |
| **Sora 2**           | Physical accuracy      | Complex scenes    |

### Step 3: Apply 8-Layer Prompt Framework

```
1. SUBJECT     — Who/what is the focus?
2. EMOTION     — What feeling should evoke?
3. OPTICS      — Lens, depth of field, FOV
4. MOTION      — How does subject/camera move?
5. LIGHTING   — Atmosphere, mood, direction
6. STYLE      — Genre, era, aesthetic
7. AUDIO      — Dialogue, SFX, music
8. CONTINUITY — What came before/after?
```

### Step 4: Build the Prompt

Use strong subject specifications:

```
Weak:     "A person walking"
Strong:   "A woman in her 30s, wearing a red trench coat,
           walking purposefully down a rain-slicked Tokyo alley"
```

### Step 5: Optimize for Model

Apply model-specific formatting:

- Veo: Use LTX Studio style prompts
- Seedance: First-frame image specification
- Wan: Image-to-video with reference

### Step 6: Plan Multi-Shot Continuity

For sequences, document:

- Character consistency across shots
- Lighting continuity
- Camera movement flow
- transitions between shots

### Step 7: Generate Test Clips

```
Before full production:
1. Generate single test clip per shot
2. Review subject expression, motion quality
3. Verify lighting consistency
4. Check continuity with reference frames
```

### Step 8: Review & Iterate

Check each output:

- [ ] Subject matches specification?
- [ ] Motion feels natural?
- [ ] Lighting consistent?
- [ ] Continuity maintained?
- [ ] Audio syncs (if applicable)?

---

## How This Skill Fits the Creative Pipeline

When building AI video content, this skill coordinates with:

```
User request: "Create an AI video for X"
         │
         ▼
1. dpf-film-director (THIS skill)
   → Script-to-prompt conversion
   → Shot planning and storyboarding
   → Model selection and prompt optimization
   → Camera, lighting, style direction
   → Continuity and consistency workflows
         │
         ▼
2. dpf-cinematic-scrolly (if web-based)
   → How video integrates into scroll narrative
   → Moviescroller and Show-and-Play patterns
         │
         ▼
3. dpf-title-seq-master (if title/opening sequence)
   → Title typography and composition
   → After Effects animation pipeline
         │
         ▼
4. dpf-movematics (if UI motion is involved)
   → Motion taxonomy for any interface elements
   → Animation performance considerations
         │
         ▼
5. brandly video / brandly produce (CLI execution)
   → CLI execution of optimized prompts
   → Model selection and parameter tuning
         │
         ▼
Final output: production-ready AI video prompts, shot by shot
```

**Boundary rule:** This skill owns the **creative direction layer** — what the video looks like,
how it moves, what it feels like. It does NOT own the CLI execution mechanics (brandly-video-generation)
or the editing/assembly layer (`brandly stitch` / `brandly export`).

---

## How to Use This Skill (Read This First)

### Step 1: Classify the Content Type

| Content Type             | Primary Consideration                    | Read This Section             |
| ------------------------ | ---------------------------------------- | ----------------------------- |
| **Cinematic/Film**       | Mood, narrative, visual language         | Script-to-Prompt Conversion   |
| **Marketing/Commercial** | Product focus, brand consistency, CTA    | Commercial Prompt Patterns    |
| **Music Video**          | Rhythm, visual metaphor, performance     | Music Video Patterns          |
| **Title Sequence**       | Typography, atmosphere, skip-proof       | Title Sequence Patterns       |
| **Animation/Abstract**   | Style, motion, conceptual                | Abstract & Animation Patterns |
| **Product Demo**         | Clarity, feature focus, clean background | Product Demo Patterns         |
| **Social Media**         | Hook in 3 seconds, vertical format       | Social Media Patterns         |
| **Documentary**          | Authenticity, interviews, b-roll         | Documentary Patterns          |

### Step 2: Select the Target Model

Different models have different strengths. Match the content to the model:

| Model                  | Best For                                 | Read This                     |
| ---------------------- | ---------------------------------------- | ----------------------------- |
| **Google Veo 3.1/3**   | Highest quality, native audio, dialogue  | Model Reference: Veo          |
| **Seedance 1.5 Pro**   | First-frame control, audio-visual sync   | Model Reference: Seedance     |
| **Wan 2.5/2.6**        | Image-to-video, flexibility, open-source | Model Reference: Wan          |
| **Runway Gen-3/4.5**   | Cinematic quality, camera control        | Model Reference: Runway       |
| **Kling 2.6/3.0**      | Realistic motion, longer duration        | Model Reference: Kling        |
| **Sora 2**             | Physical accuracy, complex scenes        | Model Reference: Sora         |
| **Pika**               | Stylized, anime, artistic                | Model Reference: Pika         |
| **Grok Imagine Video** | Fast generation, configurable duration   | Model Reference: Grok         |
| **OmniHuman**          | Multi-character avatars, lipsync         | Model Reference: OmniHuman    |
| **Fabric**             | Single-character lipsync                 | Model Reference: Fabric       |
| **HunyuanVideo**       | Foley sound, video utilities             | Model Reference: HunyuanVideo |

### Step 3: Apply the 8-Layer Prompt Framework

Every production-grade AI video prompt should address these layers:

```
┌─────────────────────────────────────────────┐
│ 1. SUBJECT     — Who/what is the focus?      │
│ 2. EMOTION     — What feeling should evoke?   │
│ 3. OPTICS      — Lens, depth of field, FOV   │
│ 4. MOTION      — How does subject/camera move?│
│ 5. LIGHTING    — Atmosphere, mood, direction  │
│ 6. STYLE       — Genre, era, aesthetic        │
│ 7. AUDIO       — Dialogue, SFX, music (if model│
│                 supports it)                  │
│ 8. CONTINUITY  — What came before/after?      │
└─────────────────────────────────────────────┘
```

### Step 4: Build the Prompt

Use the prompt templates in this skill. Apply model-specific optimization. Chain prompts
for multi-shot sequences. Verify continuity across shots.

---

## Why This Matters

AI video generation has crossed the threshold from novelty to production tool. But the
difference between a generic AI clip and a cinematic masterpiece is **direction** — the
same difference between a snapshot and a photograph.

### The Stakes

- **Prompt precision determines output quality** — vague prompts produce generic results
- **Model selection matters** — each model has unique strengths and quirks
- **Continuity is the hardest problem** — consistent characters, lighting, style across shots
- **Audio integration changes everything** — models with native audio (Veo 3.1, Seedance 1.5 Pro)
  unlock entirely new creative possibilities
- **The director's eye is irreplaceable** — AI generates; the director curates, sequences, and intends

---

## The 8-Layer Prompt Control Framework

### Layer 1: SUBJECT — Who/What Is the Focus?

Be specific. AI models respond to concrete nouns, not abstract concepts.

| Weak               | Strong                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------- |
| "A person walking" | "A woman in her 30s, wearing a red trench coat, walking purposefully down a rain-slicked Tokyo alley"          |
| "A car"            | "A matte black 1967 Ford Mustang Shelby GT500, slight rust on the fender, parked under flickering streetlight" |
| "A building"       | "An art deco skyscraper, gold trim catching sunset light, pigeons circling the spire"                          |

**Subject specification checklist:**

- [ ] Age, gender, ethnicity (if human)
- [ ] Clothing, accessories, distinctive features
- [ ] Posture, expression, body language
- [ ] Objects, props, vehicles (if applicable)
- [ ] Quantity (single subject, pair, crowd)

### Layer 2: EMOTION — What Feeling Should It Evoke?

Lighting, color, and composition all serve emotion. Name the emotion explicitly.

| Emotion        | Visual Cues                                                               |
| -------------- | ------------------------------------------------------------------------- |
| **Tension**    | Low-key lighting, tight framing, shallow depth of field, cool tones       |
| **Joy**        | High-key lighting, wide framing, warm tones, dynamic movement             |
| **Melancholy** | Soft diffused light, desaturated colors, slow movement, negative space    |
| **Wonder**     | Wide-angle lens, golden hour light, upward camera angle, lens flare       |
| **Fear**       | Dutch angle, harsh shadows, claustrophobic framing, flickering light      |
| **Serenity**   | Soft morning light, gentle movement, pastel palette, balanced composition |

### Layer 3: OPTICS — Lens, Depth of Field, Field of View

Camera optics fundamentally shape how the viewer perceives the scene.

| Lens                | Focal Length | Effect                                       | When to Use                                   |
| ------------------- | ------------ | -------------------------------------------- | --------------------------------------------- |
| **Ultra-wide**      | 14-24mm      | Exaggerated perspective, distortion at edges | Epic landscapes, architecture, disorientation |
| **Wide**            | 24-35mm      | Natural wide view, slight distortion         | Establishing shots, environmental context     |
| **Standard**        | 50mm         | Human eye perspective, natural               | Dialogue, everyday scenes, documentary        |
| **Short telephoto** | 85mm         | Flattering compression, mild background blur | Portraits, medium shots, interviews           |
| **Telephoto**       | 135-200mm    | Strong compression, shallow depth of field   | Isolation, surveillance feel, detail shots    |
| **Super telephoto** | 300mm+       | Extreme compression, very shallow DOF        | Wildlife, sports, abstracting background      |

**Depth of field specification:**

- `shallow depth of field` — subject sharp, background blurred (bokeh)
- `deep focus` — everything from foreground to background sharp
- `rack focus` — focus shifts from one subject to another during shot

### Layer 4: MOTION — How Does Subject and Camera Move?

Motion is the soul of video. Specify both camera movement and subject movement.

**Camera movements:**

| Movement           | Prompt Syntax                                       | Effect                             |
| ------------------ | --------------------------------------------------- | ---------------------------------- |
| **Pan**            | `camera pans right/left`                            | Horizontal rotation, reveals space |
| **Tilt**           | `camera tilts up/down`                              | Vertical rotation, reveals height  |
| **Dolly/Tracking** | `camera tracks forward/backward alongside subject`  | Moves through space with subject   |
| **Push in**        | `camera slowly pushes in on subject's face`         | Intimacy, tension building         |
| **Pull back**      | `camera pulls back to reveal the full scene`        | Context reveal, isolation          |
| **Crane up**       | `camera cranes upward from ground level`            | Epic reveal, scale                 |
| **Handheld**       | `handheld camera, slight natural shake`             | Realism, urgency, documentary      |
| **Steadicam**      | `smooth steadicam follows subject through corridor` | Fluid, floating, immersive         |
| **Orbit/Arc**      | `camera orbits around subject 180 degrees`          | Dynamism, 3D awareness             |
| **Zoom**           | `slow zoom in` or `crash zoom`                      | Attention direction, emphasis      |
| **Static**         | `locked-off camera, no movement`                    | Observation, stillness, tension    |

**Subject movements:**

| Movement              | Prompt Syntax                                                |
| --------------------- | ------------------------------------------------------------ |
| **Walk**              | `walking slowly toward camera`, `walking away into distance` |
| **Run**               | `sprinting`, `running in slow motion`                        |
| **Gesture**           | `raising hand`, `turning head to look at camera`, `pointing` |
| **Expression change** | `expression shifts from neutral to surprised`                |
| **Interaction**       | `picking up object`, `opening door`, `pouring coffee`        |

### Layer 5: LIGHTING — Atmosphere, Mood, Direction

Lighting is emotion made visible.

| Lighting Type   | Prompt Keywords                                           | Mood                           |
| --------------- | --------------------------------------------------------- | ------------------------------ |
| **Golden hour** | `golden hour light, warm amber tones, long shadows`       | Nostalgic, warm, cinematic     |
| **Blue hour**   | `blue hour, cool twilight, city lights beginning to glow` | Melancholic, transitional      |
| **Overcast**    | `soft overcast light, diffused, no harsh shadows`         | Neutral, natural, documentary  |
| **Low-key**     | `low-key lighting, deep shadows, single light source`     | Dramatic, noir, mysterious     |
| **High-key**    | `high-key lighting, bright, minimal shadows`              | Clean, commercial, upbeat      |
| **Backlit**     | `backlit by sunset, rim light, silhouette`                | Ethereal, dramatic, iconic     |
| **Neon**        | `neon signs reflecting on wet pavement, cyan and magenta` | Cyberpunk, urban, energetic    |
| **Practical**   | `lit by practical lamps, warm pool of light`              | Intimate, naturalistic         |
| **Volumetric**  | `volumetric light rays through fog/dust`                  | Atmospheric, otherworldly      |
| **Chiaroscuro** | `chiaroscuro lighting, stark light-dark contrast`         | Classical, dramatic, painterly |
| **Biome**       | `bioluminescent glow, ethereal blue-green light`          | Fantasy, alien, dreamlike      |

### Layer 6: STYLE — Genre, Era, Aesthetic

Style contextualizes everything the model generates.

| Style Category         | Prompt Keywords                                                                              |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| **Film genres**        | `cinematic thriller`, `film noir`, `sci-fi epic`, `romantic comedy`, `horror`, `documentary` |
| **Film stocks**        | `shot on Kodak Vision3 500T`, `16mm film grain`, `35mm anamorphic`, `8mm home movie`         |
| **Eras**               | `1970s aesthetic`, `1980s neon`, `1990s indie film`, `2000s digital`                         |
| **Art movements**      | `impressionist painting come to life`, `surrealist dream sequence`, `pop art aesthetic`      |
| **Photography styles** | `National Geographic photography`, `fashion editorial`, `street photography`                 |
| **Animation styles**   | `Studio Ghibli style`, `Pixar 3D animation`, `watercolor animation`, `stop-motion`           |
| **Digital art**        | `octane render`, `Unreal Engine 5 cinematic`, `vaporwave aesthetic`, `cyberpunk`             |

### Layer 7: AUDIO — Dialogue, SFX, Music

Only applicable for models with audio generation (Veo 3.1, Veo 3, Seedance 1.5 Pro).

| Audio Element | Prompt Syntax                                                        |
| ------------- | -------------------------------------------------------------------- |
| **Dialogue**  | `character says: "We need to leave now." in a calm but urgent voice` |
| **Ambient**   | `ambient sound of rain, distant thunder, occasional car passing`     |
| **SFX**       | `footsteps on gravel, door creaking open, glass breaking`            |
| **Music**     | `slow piano melody building to orchestral crescendo`                 |
| **Silence**   | `complete silence except for breathing`                              |

### Layer 8: CONTINUITY — What Came Before/After?

For multi-shot sequences, continuity is everything.

**Continuity checklist per shot:**

- [ ] Same character appearance (clothing, hair, position)
- [ ] Same lighting direction and quality
- [ ] Same time of day
- [ ] Same location/environment
- [ ] Logical spatial relationship to previous/next shot
- [ ] Consistent color palette
- [ ] Consistent camera style (handheld vs. locked-off)

---

## Script-to-Prompt Conversion Methodology

### The Conversion Pipeline

```
Script/Concept
    │
    ▼
1. BEAT ANALYSIS — Break into emotional beats (3-8 seconds each)
    │
    ▼
2. SHOT LISTING — Assign shot type to each beat
    │
    ▼
3. VISUAL TRANSLATION — Convert beats to visual descriptions
    │
    ▼
4. PROMPT FORMATTING — Apply model-specific structure
    │
    ▼
5. CHAINING — Link shots with continuity references
    │
    ▼
Production-Ready Prompts
```

### Step 1: Beat Analysis

Take any script or concept and break it into **beats** — discrete emotional or narrative moments,
each lasting 3-8 seconds.

**Example script beat:**

```
Original: "Sarah realizes she's been followed. She stops, turns, and sees a figure in the fog."
```

**Beat breakdown:**

- Beat 1: Sarah walking, unaware (3s) — establishes normalcy
- Beat 2: Sarah senses something, slows down (2s) — tension building
- Beat 3: Sarah stops, turns to look (2s) — the moment of realization
- Beat 4: POV shot — figure standing in fog, barely visible (3s) — the reveal

### Step 2: Shot Listing

Assign a specific shot type to each beat:

| Beat | Shot Type       | Camera                         | Purpose                      |
| ---- | --------------- | ------------------------------ | ---------------------------- |
| 1    | Medium tracking | Steadicam, follows from behind | Establish character, setting |
| 2    | Close-up        | Slow push in on face           | Build tension                |
| 3    | Medium close-up | Static, over-the-shoulder      | The turn, the moment         |
| 4    | Wide            | Static, deep focus             | The reveal, the threat       |

### Step 3: Visual Translation

Convert each beat into a full visual description using the 8-layer framework:

**Beat 1 prompt:**

> Medium tracking shot, steadicam follows a woman in her 30s (Sarah) from behind as she walks
> down a cobblestone street at dusk. She wears a charcoal wool coat, leather satchel over shoulder.
> Golden hour fading to blue hour, warm light giving way to cool shadows. Cobblestone street lined
> with old European buildings, fog beginning to gather at ground level. Shot on 35mm film, slight
> film grain, cinematic thriller aesthetic. Ambient sound of distant footsteps and wind.

### Step 4: Prompt Formatting

Apply the model-specific template (see Model Reference sections below).

### Step 5: Chaining

Link shots using continuity references:

```
Shot 1 → Shot 2: "Same character, same coat, same street, camera moves from behind to front"
Shot 2 → Shot 3: "Continues from close-up pull-back to over-shoulder angle"
Shot 3 → Shot 4: "POV match — what Sarah sees: wide shot of foggy street with distant figure"
```

---

## Prompt Templates by Content Type

### Template 1: Cinematic/Film Scene

```
[Shot type] shot, [camera movement], [subject description with age/clothing/expression].
[Environment description with time of day/weather/atmosphere].
[Lighting: type and direction]. [Optics: lens/focal length/depth of field].
[Style: film genre/era/film stock].
[Audio if supported: ambient sound/dialogue/music].
[Continuity note if part of sequence].

--ar [16:9 for cinematic | 2.39:1 for widescreen | 4:3 for vintage]
--motion [1-10 scale: subtle movement | dynamic movement]
--seed [for reproducibility]
```

**Example:**

> Wide establishing shot, camera cranes upward slowly from ground level to reveal a lone
> astronaut standing on a vast alien plateau. The astronaut wears a weathered white spacesuit
> with orange accent stripes, helmet visor reflecting a twin-sun sunset. The landscape stretches
> endlessly — crystalline formations rising from rust-colored terrain, distant mountains silhouetted
> against a lavender sky. Volumetric light rays pierce through thin atmospheric haze. Shot on
> 70mm IMAX, deep focus, everything sharp from foreground crystals to distant peaks. Sci-fi epic
> aesthetic reminiscent of Denis Villeneuve's visual language. Ambient sound of wind through
> crystalline structures, low atmospheric hum.
>
> --ar 2.39:1 --motion 6

### Template 2: Marketing/Commercial

```
[Shot type], [camera movement] on [product/subject].
[Product details: color/material/finish/key features].
[Background: clean/branded/environmental].
[Lighting: bright/clean/commercial quality].
[Style: commercial/brand aesthetic].
[Action: product being used/demonstrated].
[Text overlay suggestion if applicable].
[CTA visual cue].

--ar [16:9 for YouTube/TV | 9:16 for social | 1:1 for feed]
```

**Example:**

> Close-up push-in on a premium leather watch, camera slowly orbits 90 degrees to reveal the
> watch face. Brushed titanium case, deep navy dial with rose gold hands and markers, genuine
> alligator strap in cognac brown. Shot against a gradient backdrop transitioning from charcoal
> to warm amber, soft product photography lighting with subtle rim light highlighting the case
> edge. A hand enters frame and fastens the clasp — satisfying mechanical click. Clean luxury
> commercial aesthetic, high-end product photography style. Shallow depth of field, background
> beautifully blurred.
>
> --ar 16:9 --motion 4

### Template 3: Music Video

```
[Shot type], [camera movement], [performer/subject].
[Setting/environment with mood].
[Lighting matching song energy].
[Style: visual metaphor/aesthetic direction].
[Movement: performance/abstract/dance].
[Rhythm note: movement synced to beat/tempo].

--ar [16:9 | 9:16 | 2.39:1]
```

**Example:**

> Medium shot, handheld camera follows a dancer moving through an abandoned warehouse. She wears
> a flowing white dress that catches air as she spins, bare feet on concrete. Shafts of light
> pierce through broken roof panels, dust motes dancing in the beams. The movement is fluid and
> emotional — contemporary dance expressing grief and release. Warm light contrasting with cool
> blue shadows in corners. Shot on 35mm, slight film grain, music video aesthetic with raw
> emotional authenticity. Camera breathes with the rhythm of the movement — slight handheld
> shake adding visceral energy.
>
> --ar 16:9 --motion 8

### Template 4: Title Sequence

```
[Shot type], [camera movement], [typography treatment].
[Background: texture/pattern/abstract/environment].
[Letter animation: how text enters/exists].
[Lighting interacting with letterforms].
[Style: genre-appropriate typography aesthetic].
[Audio: music cue/tension building].

--ar [16:9 | 2.39:1]
```

**Example:**

> Static locked-off shot, centered composition. The word "ECHO" materializes letter by letter
> from dissipating smoke — each letter forms from swirling grey mist that coalesces into sharp
> serif typography (Didot Bold, tracking +120). Background is a deep charcoal gradient, almost
> black. Subtle volumetric light from above catches the edges of the letters, creating a faint
> rim glow. The smoke continues to drift lazily around and through the letterforms. Elegant,
> mysterious, prestige TV title aesthetic. Low bass tone resonates as each letter forms.
> Shallow depth of field — only the letters are sharp, smoke in foreground and background
> beautifully blurred.
>
> --ar 2.39:1 --motion 3

### Template 5: Abstract/Art

```
[Shot type], [camera movement or static].
[Abstract subject: forms/colors/textures/motion].
[Color palette].
[Lighting: how light interacts with forms].
[Style: art movement/aesthetic reference].
[Motion quality: fluid/explosive/gradual/pulsing].

--ar [1:1 | 16:9 | 4:5]
```

**Example:**

> Macro close-up, camera slowly pushes in. Iridescent oil on water surface, colors shifting
> between magenta, cyan, gold, and deep purple in organic, ever-changing patterns. The surface
> ripples and flows in slow motion, colors blending and separating like liquid stained glass.
> Top-down lighting creates specular highlights on the oil peaks. Abstract expressionism meets
> fluid dynamics — the aesthetic of a Gerhard Richter painting in motion. Extremely shallow
> depth of field, only a thin band of the surface is in focus at any moment.
>
> --ar 1:1 --motion 5

### Template 6: Product Demo

```
[Shot type], [camera movement].
[Product in use, demonstrating key feature].
[Clean, well-lit environment].
[Style: clean, informative, professional].
[Feature highlight: what makes this product special].

--ar [16:9 | 9:16]
```

**Example:**

> Over-the-shoulder medium shot, camera slowly tracks as a person opens a laptop. The laptop
> has a sleek aluminum body, thin bezels around the display. As the lid opens, the screen
> illuminates with a warm glow on the person's face. The keyboard backlight activates in a
> wave pattern from left to right. Clean, modern workspace with minimal desk, small plant,
> natural light from a window to the left. Product demo aesthetic — clear, focused, aspirational.
>
> --ar 16:9 --motion 3

### Template 7: Social Media (Short-Form)

```
HOOK (first 3 seconds): [Attention-grabbing visual + movement]
BODY (3-15 seconds): [Core message/visual payoff]
CLOSE (last 2 seconds): [CTA/memorable final image]

--ar 9:16 --motion [7-9 for engagement]
```

**Example:**

> [HOOK] Extreme close-up crash zoom: a drop of molten gold hits a dark surface and explodes
> outward in slow motion, golden tendrils spreading like lightning.
>
> [BODY] Camera pulls back to reveal an artisan's hands manipulating the cooling gold, shaping
> it into an intricate ring. Warm workshop lighting, sparks visible in the background. Hands
> are weathered, skilled, moving with practiced precision.
>
> [CLOSE] Final shot: the finished ring held up to camera, catching light. Clean background
> fades to black.
>
> --ar 9:16 --motion 8

---

## Model-Specific Reference Sections

### Google Veo 3.1 / Veo 3

**Strengths:** Highest overall quality, native audio generation (dialogue + SFX + music),
frame interpolation, understands complex multi-element prompts, excellent physics.

**Prompt Structure:**

```
[Scene description in natural language paragraph form — Veo understands prose well]
[Specify audio explicitly: "The character says...", "Sound of...", "Music..."]
[Camera direction naturally integrated into description]
```

**Veo 3.1 Specific Techniques:**

- **Native audio:** Veo 3.1 generates synchronized audio from prompt. Be explicit:
  `The woman whispers "Don't look back." Her footsteps echo on the concrete.`
- **Frame interpolation:** Use `smooth motion` or `fluid movement` for best interpolation
- **Dialogue generation:** Specify voice tone, emotion, language:
  `A man in his 50s says "I've been waiting for this moment" in a gravelly, emotional voice`
- **Duration:** Up to 60 seconds with audio. For longer content, chain prompts.
- **Resolution:** Up to 4K. Specify `4K resolution, cinematic quality` for best output.

**Veo 3.1 Common Pitfalls:**

- ❌ Don't use comma-separated keyword lists — Veo prefers natural language
- ❌ Don't over-specify audio and visual simultaneously in first attempts — test separately
- ✅ Do use descriptive paragraphs with integrated camera, subject, and audio direction
- ✅ Do specify the emotional arc: "the scene builds tension as..."

**Veo 3.1 Prompt Example:**

> A tracking shot follows a jazz pianist in a dimly lit speakeasy. He's a Black man in his 40s,
> wearing a midnight-blue suit, fingers moving fluidly across the piano keys. The room is filled
> with soft amber light from vintage pendant lamps, cigarette smoke curling through the beams.
> Patrons sit at small tables in the background, silhouettes in the haze. The camera slowly
> pushes in as the pianist transitions from a soft melody to an intense crescendo. A soft jazz
> trio plays — piano, upright bass, brushed drums — building in complexity and energy. The
> pianist looks up and smiles slightly as the final chord rings out.
>
> --ar 16:9

### Seedance 1.5 Pro

**Strengths:** First-frame control (upload reference image), synchronized audio-visual generation,
excellent character consistency from reference, multi-shot cut capability.

**Prompt Structure:**

```json
{
  "image_url": "first-frame-reference.jpg",
  "prompt": "[Scene description]",
  "audio_prompt": "[Audio description if needed]",
  "duration": 10
}
```

**Seedance 1.5 Pro Specific Techniques:**

- **First-frame control:** Upload a reference image as the first frame — the model animates
  FROM this image. This is the KEY to character and style consistency.
- **Audio-visual sync:** Separate audio prompt from visual prompt for finer control:
  - Visual prompt: describes what we SEE
  - Audio prompt: describes what we HEAR
- **Multi-shot cuts:** Seedance 1.5 Pro can handle cuts within a single generation.
  Use `then` or `cut to` to indicate transitions:
  `A woman turns to face the camera, then cut to a wide shot of the city skyline`
- **Duration:** Up to 10 seconds per generation. Chain for longer sequences.

**Seedance 1.5 Pro Prompt Example:**

> Visual: A samurai stands at the edge of a cliff at sunset, wind blowing through his dark
> hair and traditional armor. Camera slowly pushes in from a wide shot to a medium close-up.
> The sky transitions from orange to deep purple. Cherry blossom petals drift across the frame.
>
> Audio: Wind howling, distant ocean waves below the cliff, the faint sound of a shakuhachi
> flute melody.
>
> --ar 2.39:1

### Wan 2.5 / Wan 2.6

**Strengths:** Open-source, excellent image-to-video quality, flexible, community support,
good at complex motion.

**Prompt Structure:**

```json
{
  "image_url": "reference-image.jpg",
  "prompt": "[Motion and scene description]"
}
```

**Wan 2.5 Specific Techniques:**

- **Image-to-video focus:** Wan excels at animating still images. Provide a high-quality
  reference image and describe the motion you want.
- **Motion strength:** Implicitly controlled through prompt specificity. More motion keywords =
  more movement: `slow gentle movement` vs `dynamic fast movement`
- **Open-source advantage:** Can be run locally or through various providers. Quality varies
  by implementation.
- **Flexibility:** Less opinionated than closed models — gives you what you ask for, good or bad.
  Precision matters more with Wan.

**Wan 2.5 Prompt Example:**

> The camera slowly pans left across a still life painting that comes alive — flowers bloom
> in fast-motion, fruit ripens and then decays, light shifts across the canvas from morning
> golden to evening blue. The paint texture remains visible, brushstrokes becoming actual
> three-dimensional forms.
>
> --ar 16:9

### Runway Gen-3 / Gen-4.5

**Strengths:** Cinematic quality, excellent camera movement control, photorealistic output,
strong temporal consistency.

**Prompt Structure:**

```
[Camera movement first] + [subject] + [environment] + [lighting] + [style]
```

**Runway Gen-3 Specific Techniques:**

- **Camera-first prompting:** Runway responds best when camera movement is specified FIRST:
  `Camera slowly tracks forward through a crowded marketplace...`
- **Motion brush:** If using Runway's interface, use motion brush to specify which parts
  of the image should move and which should stay static.
- **Temporal consistency:** Runway has strong temporal consistency. Use this for multi-shot
  sequences — characters and environments stay recognizable.
- **Cinematic presets:** Specify film-like qualities: `cinematic, shot on ARRI Alexa,
color graded, anamorphic lens flares`
- **Duration:** Up to 10 seconds. Extend with continuation prompts.

**Runway Gen-3 Prompt Example:**

> Camera slowly tracks forward through a crowded Tokyo fish market at dawn. Vendors in rubber
> aprons arrange glistening fish on ice, steam rising from hot food stalls. Fluorescent lights
> mixed with natural dawn light create a cool-warm color contrast. The camera weaves between
> people, slight handheld feel, documentary realism. Shot on ARRI Alexa, natural color grading,
> slight film grain. The scene feels alive and immediate.
>
> --ar 16:9

### Kling 2.6 / Kling 3.0

**Strengths:** Realistic human motion, longer duration output (up to 10s), good physics
simulation, strong at complex multi-character scenes.

**Prompt Structure:**

```
[Subject + action] + [environment] + [camera] + [lighting] + [style]
```

**Kling Specific Techniques:**

- **Human motion excellence:** Kling is particularly good at natural human movement.
  Specify detailed body language: `she walks with a slight limp, favoring her left leg`
- **Multi-character scenes:** Handles multiple subjects well. Be explicit about each:
  `Two people: Person A (description) does X. Person B (description) does Y.`
- **Duration:** Up to 10 seconds. The `--extend` parameter can continue a clip.
- **Physics:** Strong physics simulation. Specify physical interactions:
  `water splashes as she steps in puddle`, `fabric billows in wind`
- **Kling 3.0 omni model:** Handles both realistic and stylized content well.

**Kling Prompt Example:**

> A father and daughter build a sandcastle on the beach. The father (man in his 40s, sun-weathered
> face, wearing a faded blue t-shirt and khaki shorts) carefully shapes the castle tower. The
> daughter (girl, about 6 years old, wearing a yellow sunhat and striped swimsuit) adds shells
> to the walls, her tongue sticking out in concentration. Camera is at child's eye level,
> slowly orbits around them. Warm afternoon sunlight, lens flare, shallow depth of field.
> Gentle waves in background, seagulls calling. Heartwarming family moment, commercial aesthetic.
>
> --ar 16:9

### Sora 2

**Strengths:** Physical accuracy, complex multi-element scenes, understands detailed
prompts, excellent world simulation.

**Prompt Structure:**

```
[Detailed scene description in paragraph form — Sora handles complexity well]
[Physical interactions specified explicitly]
[Environmental details]
```

**Sora 2 Specific Techniques:**

- **Complex scene handling:** Sora excels at scenes with many interacting elements.
  Don't simplify — be detailed.
- **Physical accuracy:** Specify physics: `raindrops splash and create ripples in puddles`,
  `leaves tumble and swirl in the wind`
- **World simulation:** Sora simulates a coherent world. Use this for establishing shots
  and environmental storytelling.
- **Prompt length:** Sora handles long, detailed prompts. Use the extra tokens wisely.
- **Duration:** Extended clips. Plan for 20-60 second generations.

**Sora 2 Prompt Example:**

> A busy Parisian café terrace on a spring afternoon. Patrons sit at small round tables
> under striped awnings — a couple sharing croissants and coffee, a woman reading a newspaper,
> two businessmen in animated discussion. Waiters weave between tables carrying trays. Cobblestone
> street beyond, a cyclist rides past, an elderly man walks a small terrier. Chestnut trees
> line the sidewalk, fresh green leaves dappled with sunlight. The camera is positioned at the
> corner, slowly panning right to reveal more of the street — a florist arranging bouquets,
> a bookstall along the Seine wall. Warm spring light, golden tones, impressionistic atmosphere.
> The sound of clinking cups, distant accordion music, murmured conversations in French.
>
> --ar 16:9

### Pika

**Strengths:** Stylized content, anime, artistic interpretation, creative effects
(lip sync, regional modification, expand canvas).

**Prompt Structure:**

```
[Style specification first] + [subject + action] + [environment] + [camera]
```

**Pika Specific Techniques:**

- **Style-first:** Pika responds well to style specification at the START of the prompt:
  `Anime style, Studio Ghibli inspired, ...`
- **Regional modification:** Can modify specific regions of an existing video.
  Use `--region` to target areas.
- **Lip sync:** Built-in lip sync for characters. Provide audio and the model syncs lips.
- **Canvas expansion:** Can expand the frame beyond the original. Use `--expand` for wider shots.
- **Creative effects:** Pika is the most experimental model — try unusual combinations.

**Pika Prompt Example:**

> Anime style, Studio Ghibli inspired. A young girl with short brown hair and oversized green
> sweater sits on a grassy hill overlooking a small coastal town. The wind blows through her
> hair and the tall grass around her. Fluffy cumulus clouds drift across a vast blue sky.
> In the distance, the ocean shimmers. A small white cat sits beside her, tail swishing.
> Camera is positioned slightly behind and to the side, slowly pushing in. Warm afternoon light,
> soft color palette, the world feels peaceful and slightly magical.
>
> --ar 16:9

### Grok Imagine Video

**Strengths:** Fast generation, configurable duration, xAI ecosystem integration,
good for rapid prototyping.

**Prompt Structure:**

```json
{
  "prompt": "[Scene description]",
  "duration": 5
}
```

**Grok Specific Techniques:**

- **Speed:** Grok is optimized for fast generation. Good for rapid iteration and prototyping.
- **Duration config:** Explicitly set duration: 5s, 10s, etc.
- **Simplicity:** Grok works best with clear, concise prompts. Don't over-engineer.
- **Iterative workflow:** Generate quickly, review, refine prompt, regenerate.

**Grok Prompt Example:**

> A time-lapse of a city skyline from sunset to night. Buildings light up one by one as darkness
> falls. Traffic below becomes streams of red and white light. The sky transitions from orange
> to deep blue to black with stars appearing. Camera is static, wide shot from a high vantage point.
>
> --ar 16:9 --duration 10

### OmniHuman 1.5

**Strengths:** Multi-character avatars, lipsync from audio, realistic human animation.

**Prompt Structure:**

```json
{
  "image_url": "character-portrait.jpg",
  "audio_url": "dialogue-or-narration.mp3"
}
```

**OmniHuman Specific Techniques:**

- **Multi-character:** Can handle multiple characters in one frame with proper setup.
- **Audio-driven:** The primary input is audio — the avatar animates to match speech.
- **Realistic human motion:** Natural head movements, facial expressions, subtle body language.
- **Use case:** Talking heads, presentations, interviews, narrated content.

### Fabric 1.0

**Strengths:** Single-character lipsync, image-to-talking-head, simple pipeline.

**Prompt Structure:**

```json
{
  "image_url": "face-image.jpg",
  "audio_url": "speech-audio.mp3"
}
```

**Fabric Specific Techniques:**

- **Simplicity:** One image + one audio = talking head video.
- **Quality:** Good lip sync accuracy for English and major languages.
- **Use case:** Avatars, presentations, educational content.

### HunyuanVideo (Foley)

**Strengths:** Adding sound effects to silent video, foley generation.

**Prompt Structure:**

```json
{
  "video_url": "silent-video.mp4",
  "prompt": "footsteps on gravel, birds chirping, wind through trees"
}
```

**HunyuanVideo Foley Specific Techniques:**

- **Post-production audio:** Add sound to AI-generated video clips.
- **Specificity matters:** Describe each sound element explicitly.
- **Layering:** Generate foley in passes — first ambient, then SFX, then music.

---

## Character Consistency Workflow

### The Consistency Problem

The hardest challenge in AI video production: keeping characters looking the same across shots.

### Solution 1: Reference Image Pipeline

```
Step 1: Generate or select a definitive character portrait
         │
         ▼
Step 2: Use this portrait as first-frame reference for every shot
         │    (Seedance 1.5 Pro, Wan 2.5, Runway Gen-3 support this)
         ▼
Step 3: In each prompt, reference the character consistently
         │    "The same woman from reference image, wearing the same red coat"
         ▼
Step 4: Verify continuity between shots before proceeding
```

### Solution 2: Visual Anchor System

Define a **visual anchor** — one distinctive element that appears in every shot:

| Anchor Type   | Example                                        |
| ------------- | ---------------------------------------------- |
| **Clothing**  | Same red trench coat in every shot             |
| **Accessory** | Same distinctive necklace, hat, or glasses     |
| **Color**     | Same color palette across all shots            |
| **Prop**      | Same object carried or interacted with         |
| **Physical**  | Same distinctive hairstyle, tattoo, or feature |

### Solution 3: Continuity Prompt Suffix

Append a continuity reference to every shot prompt:

```
[Main prompt]. NOTE: This is the same character described as [brief character descriptor].
Same time of day, same location, same visual style as previous shot.
```

### Solution 4: Seed Consistency

Use the same `--seed` value across related shots to encourage visual consistency:

```
Shot 1: ... --seed 42
Shot 2: ... --seed 42
Shot 3: ... --seed 42
```

Note: Seed consistency works best within the same model and similar prompts.

---

## Aspect Ratio Guide

| Aspect Ratio | Use Case                                  | Platforms                      |
| ------------ | ----------------------------------------- | ------------------------------ |
| **16:9**     | Standard widescreen, cinematic, YouTube   | YouTube, TV, monitors          |
| **2.39:1**   | Cinematic widescreen, epic, anamorphic    | Cinema, premium content        |
| **9:16**     | Vertical, mobile-first                    | TikTok, Reels, Shorts, Stories |
| **1:1**      | Square, balanced composition              | Instagram feed, some social    |
| **4:5**      | Vertical but not full height              | Instagram portrait             |
| **4:3**      | Standard definition, vintage, documentary | Retro aesthetic, documentary   |
| **21:9**     | Ultra-widescreen, panoramic               | IMAX, ultra-wide monitors      |

**Model-specific aspect ratio syntax:**

- Most models: `--ar 16:9` or `--aspect_ratio 16:9`
- Seedance: specified in JSON as `"aspect_ratio": "16:9"`
- Runway: selected in UI or specified in API

---

## Prompt Chaining for Multi-Shot Sequences

### What Is Prompt Chaining?

Prompt chaining is the technique of generating multiple related video clips that form a
coherent sequence. Each clip is a "shot" in the cinematic sense.

### The Chaining Process

```
1. Generate Shot 1 (establishing shot)
         │
         ▼
2. Use last frame of Shot 1 as first-frame reference for Shot 2
         │    (if model supports image-to-video)
         ▼
3. In Shot 2 prompt, reference continuity: "continuing from previous shot..."
         │
         ▼
4. Generate Shot 2 (action/development)
         │
         ▼
5. Repeat for remaining shots
         │
         ▼
6. Edit together in post-production (or use models with multi-shot cuts)
```

### Chain Planning Template

| Shot # | Type         | Duration | Continuity From  | Key Visual         | Audio Cue     |
| ------ | ------------ | -------- | ---------------- | ------------------ | ------------- |
| 1      | Establishing | 5s       | N/A              | Wide scene setting | Ambient intro |
| 2      | Medium       | 4s       | Shot 1 end frame | Character entrance | Music begins  |
| 3      | Close-up     | 3s       | Shot 2 end frame | Emotional reaction | Music builds  |
| 4      | Wide         | 5s       | Shot 3 end frame | Full scene reveal  | Music peaks   |
| 5      | Detail       | 3s       | Shot 4 end frame | Key object/moment  | Resolution    |

### Chaining Best Practices

1. **Plan the full sequence before generating** — know all shots before you start
2. **Generate establishing shot first** — sets the visual language for everything after
3. **Use consistent seeds** across related shots when possible
4. **End each shot with a stable frame** — avoid mid-motion as the cut point
5. **Overlapping action** — end one shot mid-action, begin next continuing that action
6. **Match lighting direction** — note the light direction in Shot 1 and reference it in all subsequent shots
7. **Document your continuity notes** — keep a shot log with character descriptions, lighting, wardrobe

---

## Post-Processing Guidance

### After Generation — The Polish Phase

AI video generation produces raw material. Post-processing turns it into a finished product.

### Workflow

```
Raw AI clips
    │
    ▼
1. SELECTION — Review all generated clips, keep the best takes
    │
    ▼
2. ASSEMBLY — Arrange selected clips in sequence (editing timeline)
    │
    ▼
3. TIMING — Adjust clip durations, add transitions
    │
    ▼
4. COLOR GRADE — Unify color palette across all clips
    │
    ▼
5. AUDIO DESIGN — Add music, SFX, dialogue, foley
    │
    ▼
6. TEXT/GFX — Add titles, lower thirds, graphics
    │
    ▼
7. EXPORT — Final render, platform-specific formatting
```

### Recommended Post-Processing Tools

| Task                  | Tool                                 | Purpose                           |
| --------------------- | ------------------------------------ | --------------------------------- |
| **Video editing**     | DaVinci Resolve (free), Premiere Pro | Assembly, timing, transitions     |
| **Color grading**     | DaVinci Resolve                      | Unify color across AI clips       |
| **Audio design**      | Audacity (free), Adobe Audition      | SFX, music, mixing                |
| **Foley generation**  | HunyuanVideo Foley (AI)              | Add sound effects to silent clips |
| **Upscaling**         | Topaz Video AI, inference.sh Topaz   | Improve resolution                |
| **Motion graphics**   | After Effects                        | Titles, graphics, compositing     |
| **Format conversion** | HandBrake (free), FFmpeg             | Platform-specific export          |

### Quality Checklist Before Delivery

- [ ] All clips play smoothly — no stuttering or artifacts
- [ ] Color is consistent across all shots
- [ ] Audio is balanced — music doesn't overpower dialogue/SFX
- [ ] Transitions are intentional — not jarring
- [ ] Text is legible at target resolution
- [ ] Export format matches platform requirements
- [ ] Duration matches brief (within tolerance)
- [ ] No AI artifacts visible (warped faces, impossible physics, etc.)

---

## Common Pitfalls and How to Avoid Them

### Pitfall 1: Vague Prompts

**Problem:** "A cool sci-fi scene" → Generic, uninspired output
**Fix:** Be specific. "A lone astronaut on an alien planet with twin suns, violet sky, crystalline formations"

### Pitfall 2: Over-Specifying

**Problem:** 200-word prompts with every detail micromanaged → Model gets confused, output is garbled
**Fix:** Prioritize the 3 most important elements per prompt. Let the model fill in the rest.

### Pitfall 3: Ignoring Lighting

**Problem:** Beautiful scene description but flat, lifeless lighting
**Fix:** Always specify lighting type and direction. Lighting is 50% of the visual impact.

### Pitfall 4: No Camera Direction

**Problem:** "A man in a room" → Static, boring shot
**Fix:** Always specify camera movement. Even "static locked-off camera" is a direction.

### Pitfall 5: Inconsistent Characters

**Problem:** Character looks different in every shot
**Fix:** Use reference images, visual anchors, and continuity prompt suffixes (see Character Consistency Workflow).

### Pitfall 6: Wrong Model for the Job

**Problem:** Using Pika for photorealistic output or Veo for anime
**Fix:** Match model strengths to content type (see Model Selection table in Step 2).

### Pitfall 7: Ignoring Audio

**Problem:** Beautiful visuals with no sound design (for models that support audio)
**Fix:** Always specify audio elements when using audio-capable models. Sound is half the experience.

### Pitfall 8: No Post-Processing Plan

**Problem:** Raw AI clips delivered as final product
**Fix:** Plan post-processing from the start. Generate clips with editing in mind — consistent framing, cut points, overlap.

---

## Workflow Summary

When creating AI video content:

1. **Classify content type** — Cinematic, commercial, music video, etc.
2. **Select the model** — Match model strengths to content type
3. **Break down script/concept into beats** — 3-8 second emotional moments
4. **Create shot list** — Assign shot type to each beat
5. **Write prompts using 8-layer framework** — Subject, Emotion, Optics, Motion, Lighting, Style, Audio, Continuity
6. **Apply model-specific template** — Use the right structure for the right model
7. **Plan the chain** — How shots connect, continuity notes
8. **Generate and review** — Iterate on weak shots
9. **Post-process** — Edit, color grade, add audio, export
10. **Quality check** — Run through the delivery checklist

---

## Cross-Skill Integration

| When Using                     | Add This For                                                                                                                                                                                                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dpf-continue-action-film`     | **60-category action prompt engineering** for every action type — combat, chase, FPV oner, kaiju, duel, body hardcore, mystical combat, underwater, vehicle pursuit, sniper, parkour, documentary, commercial, sports, and genre action. Model-specific grammar and continuity chains. |
| `dpf-cinematic-scrolly`        | How AI video integrates into scroll narratives (Moviescroller, Show-and-Play)                                                                                                                                                                                                          |
| `dpf-title-seq-master`         | Title sequence typography, composition, After Effects pipeline                                                                                                                                                                                                                         |
| `dpf-movematics`               | Motion taxonomy for any UI elements within the video                                                                                                                                                                                                                                   |
| `dpf-concept-art`              | Visual development, world-building, concept exploration                                                                                                                                                                                                                                |
| `ai-video-generation`          | CLI execution of optimized prompts via inference.sh                                                                                                                                                                                                                                    |
| `after-effects-scripts-master` | Post-processing compositing, VFX, motion graphics                                                                                                                                                                                                                                      |
| `davinci-resolve`              | Color grading, editing, final delivery                                                                                                                                                                                                                                                 |
| `foundry-nuke-master`          | VFX compositing, advanced post-production                                                                                                                                                                                                                                              |

---

## Quick Reference Card

| Question                              | Read This Section                        |
| ------------------------------------- | ---------------------------------------- |
| How do I structure a prompt?          | 8-Layer Prompt Control Framework         |
| How do I convert a script to prompts? | Script-to-Prompt Conversion Methodology  |
| Which model should I use?             | Step 2: Select the Target Model          |
| How do I keep characters consistent?  | Character Consistency Workflow           |
| How do I chain multiple shots?        | Prompt Chaining for Multi-Shot Sequences |
| What aspect ratio?                    | Aspect Ratio Guide                       |
| How do I fix common problems?         | Common Pitfalls and How to Avoid Them    |
| What templates can I use?             | Prompt Templates by Content Type         |
| What about audio?                     | Layer 7: Audio (in 8-Layer Framework)    |
| What about post-processing?           | Post-Processing Guidance                 |

### The 8 Layers (Memorize These)

1. **SUBJECT** — Who/what?
2. **EMOTION** — What feeling?
3. **OPTICS** — What lens?
4. **MOTION** — How does it move?
5. **LIGHTING** — What's the light?
6. **STYLE** — What aesthetic?
7. **AUDIO** — What do we hear?
8. **CONTINUITY** — What connects this to other shots?

### The Golden Rules

- **Every shot is directed** — never let the model decide camera, lighting, or mood
- **Specificity beats verbosity** — precise details matter more than long descriptions
- **Lighting is emotion** — if you don't specify lighting, the model will choose for you
- **Continuity is king** — plan the full sequence before generating the first shot
- **Audio is half the experience** — always specify sound for audio-capable models
- **Test, iterate, refine** — AI video is iterative. Generate, review, adjust, regenerate.

---

## Featured Sources & Influences

- **LTX Studio** — Veo 3.1 prompt guide and best practices
- **TrueFan AI** — AI video prompt engineering masterclass, 8 control layers
- **Genra** — SAECS prompt framework, model-specific strategies
- **Kling AI Blog** — Camera control and movement prompt techniques
- **FAL.ai** — Seedance 1.5 Pro developer guide
- **BytePlus ModelArk** — Seedance 1.5 Pro documentation
- **QuestStudio** — Cinematic prompt formulas for image-to-video
- **Invideo** — Veo 3 prompting guide
- **PromNest** — Seedance 1.5 Pro mastering guide

---

## Next Steps

After applying this skill:

1. Verify each prompt addresses all 8 layers (or intentionally omits specific ones)
2. Check that model-specific formatting is applied correctly
3. Confirm continuity notes are complete for multi-shot sequences
4. Review aspect ratio matches the intended platform
5. Generate test clips before committing to full production run
6. Document what works — build a prompt library for your project
