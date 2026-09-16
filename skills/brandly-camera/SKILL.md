---
name: brandly-camera
description: >
  Hollywood camera language, framing, angles, composition, movement, and
  lighting rules for AI video generation via brandly-cli.
  Use when writing shot direction briefs, planning camera language for
  brandly video generation, choosing lens/framing/movement, or applying
  professional lighting schemes (broadcast side, shadow side, Rembrandt,
  butterfly, split) to AI-generated shots.
  Triggers on "camera language", "shot list", "framing", "camera angle",
  "composition rule", "camera movement", "lighting for a shot",
  "broadcast side", "shadow side", "Rembrandt lighting", "180-degree rule",
  "shot direction", "cinematography prompt", "camera placement".
  NOT for reference image sheets (use brandly-character-sheet /
  brandly-object-sheet), NOT for general video editing (use dpf-senior-editor),
  NOT for 3D camera placement in Blender (use dpf-blender-engineer).
---

# Brandly Camera — Hollywood Camera Language & Lighting

Use this skill to write **production-grade shot direction** for every
`brandly video` and `brandly prompt` call.  Each shot you describe should
read like a cinematographer's brief: exact framing, motivated movement,
a named lighting pattern, and a composition rule that guides the eye.

The goal is to make AI-generated shots look **intentionally directed**,
not randomly framed and generically lit.

---

## When to Use

- Before running `brandly video` or `brandly prompt` for any shot
- When writing a shot-by-shot camera brief for a storyboard
- When the user asks "what camera should I use for this scene?"
- When applying specific Hollywood lighting to a shot
- When planning multi-shot consistency (screen direction, lens logic, light continuity)

---

## Quick Reference: The 6 Camera Fields

Every shot must specify all six:

| Field | Example |
|-------|---------|
| **Framing** | medium close-up, ECU, wide |
| **Angle** | eye-level, low 15°, overhead, dutch 20° |
| **Camera Position** | shadow side / broadcast side / key side |
| **Movement** | static, slow push-in, lateral track, crane up |
| **Lighting** | Rembrandt, butterfly, split, broadcast, motivated window |
| **Composition** | rule-of-thirds, negative space, leading line, motif |

If a field is missing, default to: framing = medium, angle = eye-level,
position = shadow side, movement = static, lighting = motivated natural,
composition = rule-of-thirds.

---

## 1. Framing Hierarchy

**Medium / Medium Close-Up is the default.**  It keeps face + body language
+ environment + dramatic space in one frame — the viewer's natural
psychological distance.

| Framing | Abbrev | Use When |
|---------|--------|----------|
| Extreme Close-Up | ECU | Isolate one detail (eye, hand, phone screen, product texture). **Earn it** — it signals "this is the important thing." |
| Close-Up | CU | Emotional state, identity reveal, decisive reaction. |
| Medium Close-Up | MCU | **Default.**  Dialogue, performance, product interaction. |
| Medium Shot | MS | Body language + environment context. |
| Medium Wide / 2-Shot | MW / 2SH | Two characters in relation to each other. |
| Wide / Long Shot | WS / LS | Establish location, isolation, scale. Use only when earned by the scene. |
| Extreme Wide | EWS | Opening/closing establishing, contrast to ECU. |

### Framing Transitions — Dramatic Logic

| Cut | Meaning |
|----|---------|
| Wide → Medium | Audience enters the character's world |
| Medium → Close-Up | Audience enters the character's emotional state |
| Close-Up → ECU | A detail is being discovered or revealed |
| ECU → Wide | Detail reconnected to the larger world |
| Any → Static Hold | Emotion lands without camera interference |

**Never cut to a different framing size without narrative reason.**
Framing changes are story events, not variety.

---

## 2. Angles

| Angle | Tilt | Psychological Effect |
|-------|------|---------------------|
| Eye-level | 0° | Neutral, documentary, intimacy |
| Slight low | +5° to +15° | Authority, respect, heroism |
| Low angle | +20° to +45° | Power, intimidation, dominance |
| High angle | −10° to −30° | Vulnerability, overview, context |
| Overhead / Bird's-eye | −60° to −90° | Detachment, fate, pattern |
| Dutch | 15°–45° tilt | Disorientation, tension, unease. **Use sparingly** — it signals "something is wrong." |
| POV | 0°, at eye height | Immersion, identification with character |

**Default: eye-level.**  Deviate only when the angle carries story meaning.

---

## 3. Camera Placement — Hollywood Placement Rules

### The 180° Rule (Broadcast Side)

Draw an imaginary line between two characters (the **axis of action**).
The camera must stay on **one side** of that line for the entire scene.

```
       Character A          Character B
            ─────────────────── axis of action
   BROADCAST SIDE (camera zone)
   
   [CAMERA 1] ────────── [CAM] ──── [CAM 2]
   (all keep A left, B right)
   
   CROSSING THE LINE BREAKS SCREEN DIRECTION
```

- Character A **always faces right**, Character B **always faces left**
  (or vice versa) within the scene.
- Crossing the 180° line makes the viewer lose spatial orientation.
- **Exceptions that are allowed:** a motivated camera move that crosses the
  line (e.g., an arc around a single character), a scene with no dialogue
  (free positioning), or a deliberately disorienting effect.

### Shadow Side Placement

**Default for cinematic/dramatic scenes: camera on the shadow side of the
subject.**  The key light illuminates the opposite (broadcast) side; the
camera observes the darker, sculpted side.

- Creates depth between subject and background
- Richer contrast and facial modelling
- Controlled mystery
- The shadow side must still be **readable** — never crush the face to black

```
          KEY LIGHT (45° to subject's left)
               ╱
      ┌───────┴───────┐
      │   SUBJECT     │
      └───────┬───────┘
               │
          CAMERA (on shadow side — right of subject)
```

### Key Side Placement

**Default for broadcast/UGC/explainer content: camera on the key (bright)
side.**  The subject faces the light; the viewer sees the fully lit face.
This is the "safe" commercial look — clean, friendly, no shadow drama.

### Rule of Thumb

| Content Type | Default Placement |
|-------------|------------------|
| Cinematic / drama / thriller | Shadow side |
| Commercial / UGC / product | Key side (bright) |
| Documentary | Motivated natural (follow the light source) |
| Horror / tension | Shadow side + high contrast |
| Romance / warm | Key side or soft Rembrandt |

---

## 4. Hollywood Lighting Patterns

Apply these as the **lighting field** in every shot brief.

### Rembrandt Lighting

Named after the painter Rembrandt van Rijn.  The key light is placed at
~45° to the subject's front, angled slightly above eye level.  It creates:

- A bright "Rembrandt triangle" of light on the shadow-side cheek
- Strong three-dimensional facial modelling
- A single defined shadow wedge under the nose onto the shadow cheek
- High drama, premium, painterly quality

```
  KEY (45° above, 30° to subject's front-right)
   ╱
  │  ┌──┐ ← bright side of face
  │  │▲ │   ▲ = Rembrandt triangle on shadow cheek
  │  └──┘
  SHADE (shadow side — camera is here)
```

**Best for:** hero product reveal, luxury commercial, dramatic portrait.
**Avoid for:** fast-paced action (too high contrast for movement).

### Butterfly (Paramount) Lighting

Key light directly in front and above the subject, casting a small
symmetrical shadow under the nose (shaped like a butterfly).

- Very flattering, symmetrical, soft
- Minimal shadow drama
- The "beauty light" of Hollywood

**Best for:** beauty/UGC, influencer content, product front-and-centre.

### Split Lighting

Key light directly to one side (90°), splitting the face into half-lit
and half-shadow.

- Maximum drama and duality
- Strong graphic impact

**Best for:** noir, antagonist reveal, high-tension confrontation.

### Broadcast / Flat Light

Even, diffused, frontal illumination.  No directional shadow drama.

- Safe, clean, commercial
- Minimises texture (skin looks smooth)
- Fast-paced content, explainer, tutorial

**Best for:** product demo, tutorial, explainer video, UGC.

### Motivated Natural Light

Light comes from a **visible source in the scene**: window, lamp, candle,
screen, streetlight, fire.  The viewer sees *why* the light is where it is.

- Creates depth and atmosphere
- Colour temperature follows the source (warm window vs. cool night)

**Best for:** any scene where a motivated source is more natural than
studio setups — documentary, lifestyle, outdoor, interior with windows.

### Lighting Combination Table

| Scene Type | Lighting | Placement |
|-----------|----------|-----------|
| Luxury product reveal | Rembrandt | Shadow side |
| UGC / influencer | Butterfly + soft fill | Key side |
| Noir / thriller | Split or Rembrandt + hard contrast | Shadow side |
| Tutorial / explainer | Broadcast flat | Key side |
| Lifestyle / home | Motivated natural (window) | Follow source |
| Horror | Rembrandt + extreme shadow ratio | Shadow side |
| Action / fast-paced | Broadcast or motivated hard key | Key side |

---

## 5. Movement Vocabulary

Every movement must be **motivated by one of five forces**:

1. **Human movement** — camera follows, observes, or reacts to the character
2. **Discovery** — camera moves because the character is discovering information
3. **Emotional transformation** — camera becomes more intimate as internal state changes
4. **Revelation of absence** — controlled pull-back or static hold reveals emptiness
5. **Liberation** — movement lightens as the character frees themselves

| Move | Prompt Tag | Use | Speed |
|------|-----------|-----|-------|
| Static / locked-off | `[static]` | Stillness, absence, truth, waiting | — |
| Slow push-in | `[slow push in]` | Recognition, emotional devastation, ending | Nearly invisible |
| Slow pull-out | `[slow pull out]` | Isolation, freedom, emotional distance | Imperceptible |
| Lateral track | `[lateral track]` | Following through space, walking | Natural pace |
| Controlled handheld | `[handheld]` | Intimate moments, human movement | Organic |
| Crane up / down | `[crane up]` / `[crane down]` | Establishing, reveals of scale | Slow |
| Dolly in / out | `[dolly in]` / `[dolly out]` | Smooth approach / reveal | Moderate |
| Pan left / right | `[pan left]` / `[pan right]` | Reveal, follow across frame | Controlled |
| Tilt up / down | `[tilt up]` / `[tilt down]` | Height reveal, architectural | Slow |
| Whip pan | `[whip pan]` | Fast scene transition | Fast |
| Orbit | `[orbit]` | **Never use by default.**  Decorative spectacle.  Use only for a product reveal the user specifically requested. | — |

**Stillness is the most powerful camera move.**  Do not move the camera
simply because the model can move it.

### Camera Speed Reflects Dramatic State

| State | Speed |
|-------|-------|
| Love / tenderness | Controlled, warm, observant |
| Discovery / dread | Slow, heavy, deliberate |
| Evidence / investigation | Clinical, precise, cataloguing |
| Confrontation / truth | Static — camera is a witness |
| Departure / release | Lightens, movement becomes free |

---

## 6. Composition & Placement

### Core Rules

| Rule | When |
|------|------|
| **Rule of thirds** | Default.  Place subject on a third-line intersection. |
| **Negative space** | Isolation, absence, scale.  Leave one side of frame empty. |
| **Leading lines** | Hallways, streets, table edges — guide the eye to the subject. |
| **Foreground occlusion** | Doorframe, window frame, lamp post — "watching through a gap." |
| **Architectural geometry** | Rooms, corridors, urban grid — frame the subject in structure. |
| **Circular motif** | Lamp, clock face, halo — one recurring shape that anchors the visual language. |
| **Two-shot symmetry** | Centre the frame on the midpoint between two characters. |

### Placement Within the Frame

- **Headroom:** ~1/10 of frame height above the head (eye-level shots).
- **Look room / lead room:** Leave space in the direction the subject is looking or moving.  Don't box them in.
- **Low frame:** For tall subjects, crop at the knees or thighs — don't show feet unless they're part of the story.
- **High frame:** For short subjects (objects on a table), crop at the top of the object.

---

## 7. Depth of Field

- **Physically motivated**, not permanently ultra-shallow.
- Rack focus only when narratively useful (evidence → face, face → evidence).
- Natural motion blur consistent with camera/subject speed.
- Background blur: f/1.4–f/2.8 for portraits/products; f/4–f/8 for environment/context.

---

## 8. Anti-AI Realism Rules

| Category | Rule |
|----------|------|
| Camera physics | No impossible paths, no floating through objects, no weightless movement |
| Human anatomy | Stable proportions across cuts, believable gait, consistent face |
| Image texture | Preserve skin texture, subtle filmic grain, realistic materials |
| Avoid | Waxy skin, hyper-clean CGI, oversharpening, plastic food, repeating textures |

---

## 9. Writing the Shot Brief

When the user asks for camera direction, output each shot in this format:

```
SHOT [N]
Framing:    [medium close-up]
Angle:      [eye-level]
Placement:  [shadow side — camera on the darker side; key from front-left]
Movement:   [static / slow push-in — motivated by [reason]]
Lighting:   [Rembrandt — triangle on left cheek; warm key 40° above eye level]
Composition:[subject on right third; negative space left; doorframe foreground]
DoF:        [f/2.0; background blurred; subject sharp]
Duration:   [3–4s]
Transition: [cut to CU — emotional shift to reaction]
```

Then convert the brief into a `brandly video` prompt:

```bash
brandly video <project_id> \
  --prompt "[medium close-up] eye-level, shadow-side placement,
            Rembrandt lighting with warm key 40° above,
            subject on right third with negative space left,
            doorframe in foreground, [static], 4 seconds,
            85mm lens, cinematic style" \
  --style cinematic \
  --character "character description" \
  --reference-images "ref_url" \
  --wait
```

---

## 10. Continuity & Screen Direction Checklist

Before generating a multi-shot sequence, confirm:

- [ ] 180° line not crossed between shots
- [ ] Characters maintain consistent screen direction (A = left, B = right)
- [ ] Light source position is consistent across the scene
- [ ] Framing transitions follow dramatic logic
- [ ] Lens focal length is consistent unless a motivated reason to change
- [ ] Colour temperature arc is motivated (day → evening → night)

---

## Routing

| Want to... | Read |
|------------|------|
| Quick camera control syntax for brandly prompts | `../brandly-video-generation/references/camera-control.md` |
| Existing lighting preset tags for brandly prompts | `../brandly-video-generation/references/lighting-presets.md` |
| Plan a full shot-by-shot storyboard | `../brandly-storyboard/SKILL.md` |
| Lock visual identity before writing shots | `../brandly-consistency/SKILL.md` |

---

**Version: brandly-camera v1.0**
