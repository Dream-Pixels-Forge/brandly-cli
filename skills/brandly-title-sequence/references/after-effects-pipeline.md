# After Effects Title Sequence Pipeline

From Photoshop artboards to animated title sequence — the complete AE workflow.

---

## Project Setup

### New Composition
```
Composition > New Composition
├── Width: 1920 (HD) or 3840 (4K)
├── Height: 1080 (HD) or 2160 (4K)
├── Frame Rate: 24fps (film standard) or 29.97fps (broadcast)
├── Duration: 10-30s for series, 30-90s for film
├── Background Color: Black (or from mood palette)
└── Advanced: 3D Renderer — Cinema 4D (if using 3D elements)
```

### Project Structure
```
📁 01_FOOTAGE (imported media, PSD imports)
📁 02_COMPS (pre-compositions)
│   ├── 01_Typography
│   ├── 02_Background
│   ├── 03_Atmosphere
│   └── 04_FullSequence
📁 03_SOLID (color solids, adjustment layers)
📁 04_AUDIO (music, SFX)
📁 05_OUTPUT (final renders)
```

---

## Importing Photoshop Artboards

### Method 1: Composition Import (Recommended)
```
File > Import > File > [select PSD]
Import Kind: Composition - Retain Layer Sizes
```
- Each PSD layer becomes an AE layer
- Layer names, colors, and hierarchy preserved
- Text layers remain editable as text

### Method 2: Footage Import
```
Import Kind: Footage
```
- Flattened image — use for background/reference only
- Smaller file size
- Cannot animate individual elements

### Method 3: Import Each Artboard Separately
- Import each of the 9 artboards as separate compositions
- Use as keyframes in a storyboard comp
- Helpful for planning the sequence flow

---

## Typography Animation in After Effects

### Text Animators (The Power Tool)

After Effects text layers have built-in animators — no keyframes needed for many effects:

#### Animate > Opacity (Letter-by-Letter)
1. Select text layer
2. Animate > Opacity
3. Range Selector 1 > Based On: Characters
4. Set Start/End keyframes (0% to 100%)
5. Adjust Units: Index for individual letters
6. Randomize Order: ✓ (for Alien-style reveal)

#### Animate > Position (Rise/Fall)
1. Animate > Position
2. Set Y value negative (rises) or positive (falls)
3. Range Selector > Start/End keyframes
4. Add easing for natural motion

#### Animate > Scale (Pop In)
1. Animate > Scale
2. Set from 0% to 100% (pop in) or 150% to 100% (overshoot)
3. Range Selector > Characters
4. Add easing: Easy Ease (F9) or custom curve

#### Animate > Tracking (Letter Spread)
1. Animate > Tracking
2. Set from wide (+200) to normal (0)
3. Creates "letters assembling" effect
4. Works beautifully for epic/sci-fi titles

#### Animate > Blur (Focus Pull)
1. Animate > Blur
2. Set from 50 to 0
3. Add subtle opacity animator (0 to 100) simultaneously
4. Creates dream-to-clarity transition

### Per-Character 3D
```
Text Layer > Advanced > Enable Per-Character 3D
```
- Each letter exists in 3D space
- Rotate, position, scale each letter independently
- Add camera moves for cinematic title reveals
- Requires Cinema 4D renderer

### Range Selector Advanced Settings

| Setting | Effect | Best For |
|---------|--------|----------|
| **Shape: Square** | Hard edges, all-or-nothing | Clean reveals |
| **Shape: Ramp Up/Down** | Gradual transition | Soft, organic |
| **Shape: Smooth** | Smoothest gradient | Premium, refined |
| **Ease High/Low** | Controls entry speed | Timing control |
| **Randomize Order** | Letters appear randomly | Mystery, tension |

---

## Animation Patterns Implementation

### 1. Letter-by-Letter Reveal (The Alien)
```
Text Animator Setup:
├── Animate: Opacity
├── Based On: Characters
├── Units: Index
├── Start: 0% → 100% (over 2-3 seconds)
├── End: 0% (stays)
├── Randomize Order: ✓
├── Ease High: 80
└── Ease Low: 0
```
**Duration:** 2-3s for full title
**Easing:** Smooth, deliberate
**Audio cue:** Each letter gets subtle click or tone

### 2. Mask Wipe (The Bond)
```
Setup:
├── Create shape layer (line, circle, or custom path)
├── Place above text layer
├── Set text Track Matte: Alpha Matte [shape layer]
├── Animate shape: Trim Paths from 0% to 100%
└── Easing: Punch ease (0.34, 1.56, 0.64, 1)
```
**Duration:** 1.5-3s
**Shape options:** Horizontal wipe, radial reveal, custom path following logo

### 3. Blur-to-Focus (The Dream)
```
Setup:
├── Text Animator: Blur (50 → 0)
├── Text Animator: Opacity (0 → 100) — offset by 5 frames
├── Both animators: Range Selector, Smooth shape
├── Start/End: 0% → 100% over 1.5s
└── Easing: Exponential (starts fast, resolves slow)
```

### 4. Scale + Settling (The Impact)
```
Setup:
├── Text Animator: Scale (150% → 100%)
├── Add expression to scale for bounce:
│   amp = 10; freq = 2; decay = 4;
│   n = 0;
│   if (numKeys > 0) {
│     n = nearestKey(time).index;
│     if (key(n).time > time) n--;
│   }
│   if (n > 0) {
│     t = time - key(n).time;
│     amp * Math.sin(freq * t * 2 * Math.PI) / Math.exp(decay * t);
│   }
└── Easing: Easy Ease Out (F9)
```

### 5. Assembly from Fragments
```
Setup:
├── Split text into individual characters (right-click > Create > Create Shapes from Text)
├── Scatter characters (Position randomizers)
├── Rotate each character randomly
├── Keyframe all to original position over 2-4s
├── Stagger timing (each letter starts 2-4 frames apart)
└── Easing: Smooth arrival (cubic-bezier)
```

### 6. Environmental Emergence
```
Setup:
├── 3D Camera (Layer > New > Camera)
├── Text layer in 3D space (Enable Per-Character 3D)
├── Background layers at different Z depths
├── Animate camera: slow push-in (Position keyframe)
├── Animate text: subtle rise from below (Position Y keyframe)
├── Atmospheric particles (Particular plugin or CC Particle World)
└── Light layers interacting (Create > Light)
```

---

## After Effects Scripts & Expressions

### Essential Expressions

#### Wiggle (Organic Movement)
```javascript
// Subtle camera drift
wiggle(0.5, 10)

// Particle float
wiggle(1, 5)

// Text hover effect
wiggle(2, 3)
```

#### Loop (Repeating Animation)
```javascript
// Loop position animation
loopOut("cycle")

// Loop with ping-pong (forward then reverse)
loopOut("pingpong")

// Loop with offset
loopOut("offset", 0)
```

#### Time-Based Animation
```javascript
// Continuous rotation
time * 30

// Continuous drift
[time * 10, 0]

// Sine wave motion
Math.sin(time * 2) * 50
```

#### Random (Controlled Chaos)
```javascript
// Random position within bounds
seedRandom(index, true);
[random(-100, 100), random(-50, 50)]

// Random opacity
seedRandom(index, true);
random(30, 100)

// Random delay
seedRandom(index, true);
delay = random(0, 2);
if (time > delay) value else 0
```

### Recommended Scripts/Plugins

| Script/Plugin | Purpose | Cost |
|---------------|---------|------|
| **Motion 4** (Mt. Mograph) | Easing presets, advanced animation | Paid |
| **Ease and Wizz** | Easing expressions | Free |
| **Flow** | Visual easing editor | Paid |
| **Overlord** | Illustrator ↔ AE workflow | Paid |
| **Duik Bassel** | Character rigging | Free |
| **True Comp Duplicator** | Duplicate comps with dependencies | Free/Paid |
| **Explode Shape Layers** | Break shapes for animation | Free |
| **Particular** (Trapcode) | Particle systems | Paid |
| **Element 3D** (Video Copilot) | 3D objects in AE | Paid |
| **Sapphire** (Boris FX) | Effects, transitions, blurs | Paid |

---

## Sequence Assembly

### Storyboard Method
1. **Create master composition** — `SEQ_Master`
2. **Import all 9 artboards** as sub-compositions
3. **Arrange in timeline:**
   ```
   AB_01 (Mood)        0:00 - 0:03
   AB_02-03 (Type)     0:03 - 0:08
   AB_04 (Comp A)      0:08 - 0:12
   AB_05 (Comp B)      0:12 - 0:16
   AB_06 (Comp C)      0:16 - 0:20
   AB_07 (Color)       0:20 - 0:24
   AB_08 (Peak)        0:24 - 0:27
   AB_09 (Final)       0:27 - 0:30
   ```
4. **Add transitions** between each artboard section
5. **Layer in audio** — music, SFX, ambient

### Transition Types
| Transition | Duration | When to Use |
|------------|----------|-------------|
| **Hard cut** | 0 frames | Sudden mood shift, impact |
| **Dissolve** | 12-24 frames | Smooth, dreamy, elegant |
| **Wipe** | 8-16 frames | Directional energy, movement |
| **Fade through black** | 24-48 frames | Chapter break, major shift |
| **Match action** | 0 frames (seamless) | Elements flow between sections |
| **Morph** | 16-32 frames | Transformation, evolution |

---

## Rendering & Delivery

### Review Render (Fast)
```
Render Queue > Output Module
├── Format: H.264
├── Preset: Match Source — High bitrate
├── Quality: High
└── Output: .mp4
```

### Delivery Render (ProRes)
```
Render Queue > Output Module
├── Format: QuickTime
├── Codec: Apple ProRes 422
├── Resolution: 1920×1080 or 3840×2160
├── Frame Rate: 24fps or 29.97fps
├── Audio: 48kHz, 24-bit
└── Output: .mov
```

### Web/Streaming Render
```
Render Queue > Output Module
├── Format: H.264
├── Preset: YouTube 1080p or 4K
├── Bitrate: 20-40 Mbps (1080p), 45-80 Mbps (4K)
├── Audio: AAC, 320kbps
└── Output: .mp4
```

---

## The 5 Review Tests

### 1. Skip Test
Watch the full sequence 5x in a row. After each viewing, ask: "Would I skip this?"
- If yes → identify what's making you want to skip
- Fix that element (usually: too long, repetitive, generic)

### 2. Mute Test
Watch with sound off. Does it still work?
- Title sequences should be visually compelling without audio
- If it feels flat muted → visual design needs strengthening

### 3. Thumbnail Test
Shrink to 320px wide. Can you still read the title?
- If not → increase size, weight, or contrast of title
- This is how most audiences will first encounter it

### 4. Fresh Eyes Test
Show someone unfamiliar. What emotion do they feel?
- If it matches your intended mood → success
- If not → revisit mood board (AB_01) and align

### 5. Platform Test
Watch on actual target device (TV, phone, tablet)
- Colors shift between devices
- Readability changes with screen size
- Audio mix needs vary by playback environment
