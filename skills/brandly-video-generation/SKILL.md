---
name: brandly-video-generation
description: >
  Generate AI video content using the brandly-cli toolchain with professional prompt engineering.
  Use when the user wants to create videos from prompts, generate cinematic sequences,
  maintain character consistency across shots, use reference images for identity locking,
  or build video ads/commercials.
  Triggers on "generate video", "create video ad", "AI video generation",
  "character consistency", "reference image video", "cinematic prompt",
  "shot list", "brandly video", "make a commercial", "video campaign".
  NOT for video editing (use dpf-senior-editor),
  NOT for 3D animation (use dpf-blender-engineer),
  NOT for motion graphics (use hyperframes-animation).
---

# Brandly CLI Video & Image Generation

This skill covers professional video and image generation using **Agnes AI** through the `brandly-cli` toolset. It emphasizes **character consistency**, **cinematic prompting**, and **reference image anchoring** for production-quality output.

## Pipeline & Folder Structure

Everything lives under `.brandly/<project_id>/` (single layout, no legacy `refs/` tree, no `.brandly/projects/`):

```
.brandly/<project_id>/
    docs/plan/            generation plans + production_plan.md (source of truth)
    docs/bible/  docs/storyboard/  docs/tmp/   (bibles, shot lists, gen/fail docs)
    images/prop/ location/ character/ vehicle/ mecha/ animal/ plant/ keyframe/ general/
    videos/scenes/ insert/ transition/ general/
    audio/soundtrack/ sfx/ foley/ voiceover/ general/
    3d-spatial/cameras/ keyframes/ depthmaps/ general/
    project.json  cost.json  export/
```

Key rules:

- **All reference images live in `images/<category>/`** — never a separate refs folder.
  Objects → `images/prop/` (`prop_*.png`), characters → `images/character/`
  (`char_*.png`), locations → `images/location/` (`loc_*.png`).
- **Keyframe mode**: `--first-frame`/`--last-frame` local files are archived into
  `images/keyframe/` as `start_frame_<name>.png` / `end_frame_<name>.png`.
- **`docs/plan/production_plan.md` is the single source of truth** for where each
  generation plan came from: every plan registers with its source command
  (`brandly reference` / `brandly image` / `brandly video` / `brandly produce` /
  `brandly job-resume`) and its status (PENDING → COMPLETED / FAILED).
- **Shot-by-shot production**: for multi-shot films, write a shot-list JSON
  (`[{name, prompt, duration, style, references}, …]`) and run
  `brandly produce <project_id> --shots shots.json` — it registers ALL shots
  on the production plan first, then generates **one shot at a time** with a
  60s wait between requests (Agnes: 1 request/minute). Never batch or loop
  `brandly video` calls — that bypasses the plan and violates the rate limit.
- **Smaller reference payloads**: large local images (PNG plates, multi-MB
  files) are auto-converted to webp/jpeg before upload (JPEG for opaque,
  WebP for alpha) to keep requests under the create timeout. Disable with
  `BRANDLY_IMAGE_CONVERT=off`. Scope what gets injected with
  `brandly video --no-auto-refs` or `--auto-ref-category <name>`.
- **Plan reuse**: re-running with an unchanged config REUSES the existing plan
  (e.g. retry after a failure). A new plan file is created only when something
  in the config (prompt, model, style, mode, …) changes.
- **Human-in-the-loop gates**: `brandly reference`, `brandly video` (after the
  video is downloaded), and `brandly gate` ask up to 3 confirmation questions
  before continuing, to make sure the result matches expectations. Rejecting
  writes a review note to `docs/tmp/review_<stage>_<ts>.md`. In non-interactive
  (piped/EOF) runs the defaults auto-approve.

## Quick Start

```bash
# Initialize project first
brandly init --name "Campaign" --idea "description" --style cinematic --shots 4 --budget 500

# Generate a cinematic prompt
brandly prompt -s "Product name" -a "what happens" -e "where" -n 4 --style cinematic -c "character description"

# Generate the primary reference image first (saves to images/<category>/,
# auto-injected into later video calls)
brandly reference <project_id> --subject-type object \
  --subject "Nike Air Max 1, white colorway, visible Air unit" --style-preset commercial

# Generate video (Agnes AI — polls + downloads to videos/scenes/ by default)
brandly video <project_id> -p "your prompt" --style cinematic \
  --reference-images "url1"
# Keyframe mode (auto-detected when frames are provided):
brandly video <project_id> -p "..." --first-frame start.png --last-frame end.png

# Generate image (Agnes AI — no project needed)
brandly image -p "description" --style-preset photorealistic --size 2K

# A job that timed out? Poll + download later:
brandly job-resume <video_id> --project-id <project_id>
```

---

## Routing Table

| Want to... | Read |
|------------|------|
| Look up video styles | `references/video-styles.md` |
| See camera control syntax | `references/camera-control.md` |
| Reference lighting presets | `references/lighting-presets.md` |
| Learn character consistency | `references/character-consistency.md` |
| Troubleshoot issues | `references/troubleshooting.md` |
| **Plan shots before generating** | → `../brandly-storyboard/SKILL.md` |
| **Build the project bible** | → `../brandly-production-bible/SKILL.md` |
| **Lock visual consistency** | → `../brandly-consistency/SKILL.md` |
| **Create character refs** | → `../brandly-character-sheet/SKILL.md` |
| **Create location refs** | → `../brandly-location-sheet/SKILL.md` |
| **Create product refs** | → `../brandly-object-sheet/SKILL.md` |
| **Create vehicle refs** | → `../brandly-vehicle-sheet/SKILL.md` |
| **Create mecha refs** | → `../brandly-mecha-sheet/SKILL.md` |
| **Create animal refs** | → `../brandly-animal-sheet/SKILL.md` |
| **Create plant refs** | → `../brandly-plant-sheet/SKILL.md` |

---

## Core Workflow

### Step 1: Project Initialization
```bash
brandly init --name "Product Campaign" --idea "Brief description" --style cinematic --budget 500 --shots 5
```

### Step 2: Generate Cinematic Prompt
Use `brandly prompt` to create professional shot lists:
```bash
brandly prompt \
  -s "A woman in a red dress holding a perfume bottle" \
  -a "walks gracefully through a sunlit garden" \
  -e "elegant French garden with blooming roses" \
  -n 4 \
  --style cinematic \
  -c "elegant woman, mid-20s, long blonde hair in loose waves, wearing a flowing red silk dress, delicate jewelry"
```

### Step 3: Generate Video
```bash
brandly video <project_id> \
  -p "generated prompt from step 2" \
  --style cinematic \
  --character "elegant woman, mid-20s, long blonde hair" \
  --reference-images "https://example.com/reference.jpg"
```

By default `brandly video` **waits for the job and downloads the MP4** to
`videos/scenes/`, then runs the human review gate. Use `--no-wait` to create
the task and exit; poll + download later with
`brandly job-resume <video_id> --project-id <project_id>` (job-resume also
marks the plan COMPLETED in the production plan).

### Video Modes

`--mode` defaults to `auto`, which resolves to the first applicable mode:

| Mode | When it applies | Behavior |
|------|----------------|----------|
| `keyframe` | `--first-frame` and/or `--last-frame` provided | Frames the video between the given start/end frames; local frame files are archived to `images/keyframe/` (`start_frame_*` / `end_frame_*`) |
| `reference` | Reference images provided (auto-injected primary reference or `--reference-images`) | Image-to-video generation anchored on the references |
| `text` | Nothing else provided | Pure text-to-video generation |

Pass `--mode text` explicitly to force text mode even when references exist.
A chosen mode missing its required inputs degrades to text mode with a
warning (e.g. `--mode keyframe` without frames). The resolved mode is
printed and recorded in the generation plan.

### Step 4: Generate Images
```bash
brandly image \
  -p "product hero shot" \
  --style-preset commercial \
  --size 2K \
  --ratio 16:9
```

## Video Styles

| Style | Use Case | Credit Cost | Description |
|-------|----------|-------------|-------------|
| `cinematic` | Storytelling, narratives | 250 | Golden hour lighting, emotional |
| `ugc` | Social media content | 150 | Natural window, authentic |
| `montage` | Fast-paced sequences | 200 | Quick cuts, dynamic |
| `multi_shot` | Multi-angle campaigns | 300 | Character consistency focus |
| `continuous` | Single take | 200 | Flowing, uninterrupted |
| `unboxing` | Product reveals | 180 | Focus on unpacking experience |
| `lifestyle` | Aspirational content | 170 | Warm, relatable everyday |
| `collage_motion_graphic` | Animated graphics | 350 | Motion design, text animations |
| `brand_short_video` | Brand spots | 280 | Short-form brand content |
| `explainer_video` | How-to, tutorials | 400 | Educational, clear messaging |

**Note:** `commercial`, `documentary`, `luxury`, and `action` are **image-only** `--style-preset` values — they are NOT valid as `--style` for `brandly video`. Use `cinematic` for premium looks, `ugc` for authentic feel.

## Camera Control

### Shot Types
- `establishing` — Wide opening, sets location
- `medium` — Standard waist-level framing
- `close_up` — Intimate face/product detail
- `extreme_close_up` — Macro details
- `low_angle` — Heroic, powerful perspective
- `high_angle` — God's eye view
- `tracking` — Camera follows subject movement
- `orbital` — 360-degree orbit around subject
- `static_product` — Clean product showcase
- `pov` — Point-of-view perspective

### Camera Moves
- `[Push in]` — Move toward subject
- `[Pull out]` — Move away from subject
- `[Pan left/right]` — Horizontal rotation
- `[Tilt up/down]` — Vertical rotation
- `[Tracking shot]` — Follow subject
- `[Static shot]` — Locked camera
- `[Orbital]` — Orbit around subject
- `[Crane up/down]` — Vertical rise/lower
- `[Whip pan]` — Fast horizontal swing
- `[Dolly in/out]` — Physical movement closer/farther

## Lighting Presets

| Preset | Description | Tags |
|--------|-------------|------|
| `golden_hour` | Warm late-afternoon sun | amber light, long shadows, sun flare |
| `blue_hour` | Cool twilight | blue ambient, street lamps, soft fill |
| `studio` | Clean commercial | soft key, fill opposite, rim light |
| `neon` | Urban night | cyan/magenta reflections, wet bounce |
| `natural` | Soft daylight | window light, diffused, gentle shadows |
| `dramatic` | High contrast | side lighting, deep shadows, chiaroscuro |
| `product_studio` | Commercial product | clean white background, sharp focus |
| `night` | Practical lights | moonlight blue, street lights, depth |

## Best Practices

### For Character Consistency
1. **Define character once at top** of prompt with full description
2. **Use reference images** whenever possible
3. **Add consistency anchors**: "Same face, hair, outfit in every shot"
4. **Avoid re-describing** the character in each shot — the model will drift
5. **Test with 1 shot first**, then expand to multi-shot

### For Product Videos
1. Use `commercial` style with `product_studio` lighting
2. Include `static_product` camera shots for hero moments
3. Add close-ups for detail (texture, logo, materials)
4. End with lifestyle shot showing product in use

### For Narrative Videos
1. Start with establishing shot
2. Use tracking shots for movement
3. Mix close-ups for emotion
4. End with wide/orbital for impact

## Prompt Templates

### Single Shot (Product)
```
A commercial scene featuring [product].

[Product description — material, color, texture, size].

The camera [camera move], [shot type].

The scene is set in [environment].

Lighting: [lighting tags].

[Style suffix from preset]

Duration: [N] seconds.
```

### Multi-Shot Sequence
```
Master Prompt: [brief summary of entire sequence]

SHOT 1 — [shot type]:
[Subject] [action] in [environment].
The camera [camera movement].
Lighting: [lighting tags].
[Style notes].
Duration: [N]s.

SHOT 2 — [shot type]:
[Subject continues action].
The camera [different angle/movement].
Duration: [N]s.

[Continue for each shot...]
```

## Recommended Workflow Order

For production-quality campaigns, follow this sequence:

```
1. brandly-production-bible   → Define the project, style, assets
2. brandly-storyboard         → Plan every shot before generating
3. Asset sheet skills         → Generate reference images for characters, locations, products
4. brandly-consistency        → Set up anchors and locking rules
5. brandly-video-generation   → Execute the generated shots
```

Skipping steps 1–4 will result in inconsistent, unpredictable output.

As you execute, track everything in `docs/plan/production_plan.md` —
the single source of truth for each plan's origin (`brandly reference`,
`brandly image`, `brandly video`, `brandly job-resume`) and status
(PENDING → COMPLETED / FAILED). Approving the human gates is what flips
statuses to COMPLETED; a rejection leaves the plan PENDING so the next run
reuses it instead of creating a new one.

## Step 0: Always Generate a Reference First

Before any video generation, generate a **single primary reference image**
that locks the appearance of the most important asset (product, character,
location). `brandly video` will auto-detect the reference and inject it as
the first reference image (strongest influence), reducing drift dramatically.

```bash
# Object reference (product ad)
brandly reference <project_id> --subject-type object \
  --subject "Nike Air Max 1 sneaker, white colorway, visible Air unit" \
  --style-preset commercial --size 2K --ratio 1:1

# Character reference (cast-led narrative)
brandly reference <project_id> --subject-type character \
  --subject "Maya, 25, dark braids, olive skin, emerald eyes" \
  --style-preset photorealistic --size 2K --ratio 1:1

# Location reference (environment-heavy)
brandly reference <project_id> --subject-type location \
  --subject "Modern loft apartment, white marble, city skyline, golden hour" \
  --style-preset cinematic --size 2K --ratio 16:9
```

After the reference is saved (objects land in `images/prop/` as
`prop_<subject>_<timestamp>.png`), the next `brandly video` call will print:

```
✓ Primary reference: object (prop_nike_air_max_1_2026-09-01T18-20-00.png)
Reference images: 2
```

The reference command ends with a **human review gate**: it asks whether the
result matches expectations before continuing (reject → review note in
`docs/tmp/review_reference_*.md`, exit 1; approve → the plan is marked
COMPLETED in `production_plan.md`). In non-interactive runs the gate
auto-approves.

For high-stakes or multi-shot campaigns, pass `--require-reference` to
make the CLI fail fast if the reference is missing or deleted.

### Why reference first?

Without a reference image, the model is "flying blind" — every shot is
a fresh roll of the dice. The first reference shot establishes a stable
visual identity for the product/character; subsequent shots have a
strong visual reference to lock onto. This typically reduces color/shape
drift by 30-50% in multi-shot campaigns.

---

## Asset Sheet Reference

For consistent generation across all projects, use the companion asset sheet skills:

| Skill | Use For | Key Features |
|-------|---------|--------------|
| **brandly-character-sheet** | Characters, models, people | Physical traits, wardrobe, consistency rules |
| **brandly-object-sheet** | Products, items, props | Dimensions, materials, branding |
| **brandly-location-sheet** | Sets, environments, backgrounds | Layout, lighting, atmosphere |
| **brandly-animal-sheet** | Wildlife, pets, creatures | Species accuracy, behavior, habitat |
| **brandly-mecha-sheet** | Robots, machines, vehicles | Technical details, materials, lighting |
| **brandly-plant-sheet** | Flora, gardens, nature | Species, growth, seasonal changes |
| **brandly-vehicle-sheet** | Cars, trucks, aircraft | Dimensions, styling, wheels |

### When to Use Asset Sheets

1. **Before video generation**: Create reference sheets for key elements
2. **For consistency**: Use sheets as --reference-images source
3. **For reusability**: Save sheets for future campaigns
4. **For teams**: Document standards for production consistency

### Quick Reference Card Generation

```bash
# Create character reference
brandly image --prompt "Character sheet: [detailed description]" \
  --style-preset photorealistic --size 4K

# Create location reference
brandly image --prompt "Location reference: [environment description]" \
  --style-preset cinematic --size 4K

# Create object reference
brandly image --prompt "Product reference: [object description]" \
  --style-preset commercial --size 4K
```

## Integration with Director Agent

The Director agent automatically uses these techniques when generating videos:
1. Calls `brandly prompt` to generate professional prompts
2. Uses `brandly video` with `--character` and `--reference-images`
3. Stores results in project artifacts
4. Tracks costs and progress

## Example: Full Product Campaign

```bash
# 1. Initialize project
brandly init --name "Summer Soda Campaign" --idea "Refreshing soda commercial for summer" --style cinematic --shots 4 --budget 500

# 2. Generate cinematic prompt
brandly prompt \
  -s "A cold can of soda" \
  -a "opens with a refreshing fizz, condensation dripping" \
  -e "sunny beach with crystal clear water" \
  -n 4 --style cinematic \
  -c "young woman, 25, athletic build, suntanned skin, wearing swimsuit and sunglasses"

# 3. Generate video with reference image (Agnes AI)
brandly video <project_id> \
  --prompt "MASTER PROMPT: A cold can of soda opens..." \
  --style cinematic \
  --character "young woman, 25, athletic build" \
  --reference-images "https://example.com/model-ref.jpg" \
  --wait

# 4. Generate hero image (Agnes AI)
brandly image \
  --prompt "Product hero shot of soda can on ice" \
  --style-preset commercial \
  --size 2K

# 5. Export all assets
brandly export <project_id>
```

## Provider Routing

| Command | Provider | Model Default | Notes |
|---------|----------|--------------|-------|
| `brandly image` | Agnes AI | `agnes-image-2.5-flash` | Style presets, 1K/2K/3K/4K output |
| `brandly video` | Agnes AI | `agnes-video-2.5-flash` | Requires project, ref-image anchoring |
| `brandly minimax-image` | MiniMax | `image-01` | Subject reference, seed, up to 2K |
| `brandly minimax-video` | MiniMax | `MiniMax-H3` | First/last frame, ref video/audio, native stereo audio |

**Choose based on your needs:**
- **Character consistency** → `brandly video` (Agnes) with reference images
- **Image generation** → `brandly image` for speed, `brandly minimax-image` for subject reference
- **Reference video + audio** → `brandly minimax-video` (MiniMax H3 supports ref video input)
- **Prototyping** → `brandly video` default (`agnes-video-2.5-flash` — currently free; 720P, 4-12s)
- **Rate limits** → `brandly rate-limits` (Agnes RPM by tier; MiniMax H3 concurrent tasks).
  Agnes video is 1 request/minute — multi-shot films MUST go through
  `brandly produce` (shot-by-shot from the production plan), never parallel calls.
  `brandly batch` (multiple variants of ONE prompt) is also rate-limited: variants
  are submitted one at a time with a 60s wait between requests.

## API Notes

- **Image models** (Agnes): `agnes-image-2.5-flash` (current default — latest gen, same API contract as 2.1, sizes 1K-4K), `agnes-image-2.1-flash` / `agnes-image-2.0-flash` (legacy)
- **Video models** (Agnes): `agnes-video-2.5-flash` (only Agnes video model — 720P, 4-12s, ≤5 ref images, ≤3 ref audios, no ref video; rate-limited to 1 req/min)
- **MiniMax image**: `image-01`, `image-01-live` — subject reference, `--seed` reproducibility, `--style` art settings (live)
- **MiniMax video**: `MiniMax-H3` (ref video/audio, 2K, native synchronized stereo audio via [sound] prompt tag), `MiniMax-H3-Max` (fast, first/last frame only)
- **Negative prompts**: Not supported by Agnes API — use prompt engineering via style presets instead
- **Output formats**: Images as URLs, videos as MP4 with direct download links
- **Size options**: 1K, 2K, 3K, 4K for Agnes images; 720P/1080P/2K for MiniMax images; 480P/768P/2K for MiniMax video

## Provider Rate Limits (v0.3.4+)

Run `brandly rate-limits` for the live table. Headlines:

- **Agnes AI** (free/default key): text 20 RPM; images 1K 20 RPM, 2K 10 RPM, 3K/4K 1 RPM; video free quota ~500s/day. Enterprise keys get ~2× on 1K/2K image RPM.
- **MiniMax**: H3 video is governed by *concurrent tasks* (2 free / 15 paid), not RPM; text tier 20 RPM free / 200 paid.
- **Batch safety**: MiniMax image `n > 1` batches automatically fall back to one-at-a-time generation on 429 or partial results; the `batch` video command continues past failed variants instead of aborting the run.


## Troubleshooting

### Video Takes Too Long
- `brandly video` waits and downloads by default; a timeout does **not**
  abort the job — run `brandly job-resume <video_id> --project-id <id>` to
  poll and download later (this also marks the plan COMPLETED)
- Use `--no-wait` to create the task and exit immediately
- On 429s, check provider limits with `brandly rate-limits` before retrying
- MiniMax H3 is concurrency-limited (2 free / 15 paid parallel tasks), not per-minute RPM

### Character Drifts Between Shots
- Add more detailed character description
- Use reference images
- Include consistency anchors in prompt
- Generate shots separately and composite later

### Low Quality Output
- Use `cinematic` or `commercial` style
- Add specific lighting and camera details
- Include film stock references (Kodak Vision3, Fuji Superia)
- Use `--size 2K` or higher for images
