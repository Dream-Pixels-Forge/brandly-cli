---
name: brandly-3d-spatial
description: |
  Generate Blender 3D spatial reference frames for Agnes AI video generation.
  Creates camera composition guides that Agnes uses as spatial anchors.
  Blender frames are SPATIAL REFERENCES — they show WHERE things go, not WHAT they look like.
  Does NOT generate video directly — outputs reference frames for Agnes keyframe mode.
metadata:
  opencode:
    emoji: '🎬'
    requires:
      tools:
        - blender
        - brandly-cli
      skills:
        - brandly-camera
        - brandly-video-generation
      env:
        vars:
          - OPENART_API_KEY
          - AGNES_API_KEY
---

# 3D Spatial — Blender → Agnes Pipeline

## ⚠️ CRITICAL: Spatial References, NOT Visual Targets

**Blender renders are SPATIAL REFERENCES. They tell Agnes WHERE to place things, NOT WHAT they look like.**

| Blender Frame Shows | Agnes Should Generate |
|---------------------|----------------------|
| Camera position & angle | Matching camera perspective |
| Character placeholder location | Real character in that position |
| Ground plane | Actual environment/scene |
| Lighting direction | Consistent lighting |
| Spatial relationships | Compositional accuracy |

**NEVER use Blender renders as visual style references.** They are composition guides only.

## How It Works

Agnes Video 2.5 Flash does NOT support video input. Instead, it uses:
- `first_frame` — Starting composition (keyframe mode)
- `last_frame` — Ending composition (keyframe mode)
- `reference_images` — Up to 5 spatial anchors (reference mode)

**Blender provides the spatial control. Agnes adds the motion.**

## Brandly Folder Structure

```
.brandly/{project}/
├── docs/           # Plans, bibles, storyboards
├── images/         # Reference images by category (prop/, character/, ...)
├── videos/         # Generated videos by category
├── audio/          # Audio files by category
├── 3d-spatial/     # Blender spatial references
│   ├── cameras/    # Camera position/angle frames
│   ├── keyframes/  # First/last frame for animated shots
│   ├── depthmaps/  # Depth map renders from Blender
│   └── general/    # Other spatial references
└── project.json
```

## Workflows

### 1. Static Camera (Shoulder-to-Shoulder)

For locked-off shots with no camera movement:

```
Blender → Single Frame → Agnes keyframe (first_frame only)
```

```bash
# Step 1: Create scene
python playblast_renderer.py --config static.json --output ./.brandly/{project}/3d-spatial/cameras --mode single

# Step 2: Extract reference
python extract_references.py --input ./.brandly/{project}/3d-spatial/cameras --output ./.brandly/{project}/3d-spatial/keyframes --strategy first

# Step 3: Generate video
agnes generate \
  --first-frame ./.brandly/{project}/3d-spatial/keyframes/first_frame.png \
  --prompt "Cinematic shot of character speaking" \
  --model agnes-video-2.5-flash \
  --duration 8
```

### 2. Animated Camera (Dolly, Tracking, Orbital)

For shots with camera movement:

```
Blender → First + Last Frames → Agnes keyframe (first_frame + last_frame)
```

```bash
# Step 1: Create scene with camera animation
python playblast_renderer.py --config animated.json --output ./.brandly/{project}/3d-spatial/cameras --mode first_last

# Step 2: Extract first + last frames
python extract_references.py --input ./.brandly/{project}/3d-spatial/cameras --output ./.brandly/{project}/3d-spatial/keyframes --strategy first_last

# Step 3: Generate video
agnes generate \
  --first-frame ./.brandly/{project}/3d-spatial/keyframes/first_frame.png \
  --last-frame ./.brandly/{project}/3d-spatial/keyframes/last_frame.png \
  --prompt "Slow dolly-in towards character" \
  --model agnes-video-2.5-flash \
  --duration 8
```

### 3. Multi-Reference (Depth/Composition)

For complex compositions with depth cues:

```
Blender → Multiple Reference Frames → Agnes reference mode
```

```bash
# Step 1: Render multiple camera angles
python playblast_renderer.py --config multi.json --output ./.brandly/{project}/3d-spatial/cameras --mode animation

# Step 2: Extract as references
python extract_references.py --input ./.brandly/{project}/3d-spatial/cameras --output ./.brandly/{project}/3d-spatial/keyframes --strategy all

# Step 3: Generate with references
agnes generate \
  --first-frame ./.brandly/{project}/3d-spatial/keyframes/first_frame.png \
  --reference-images ./.brandly/{project}/3d-spatial/keyframes/reference_001.png ./.brandly/{project}/3d-spatial/keyframes/reference_002.png \
  --prompt "Scene with spatial depth" \
  --model agnes-video-2.5-flash \
  --duration 8
```

## Scene Configuration

### Camera Presets

| Preset | Focal Length | Use Case |
|--------|-------------|----------|
| `establishing` | 24mm | Wide shots, environment |
| `medium` | 50mm | Standard coverage |
| `closeup` | 85mm | Intimate shots |
| `low_angle` | 35mm | Hero shots |
| `high_angle` | 35mm | Establishing scale |
| `over_shoulder` | 85mm | Conversation coverage |

### Camera Movement Keys

| Key | Movement | Description |
|-----|----------|-------------|
| `dolly_in` | Z axis → target | Push towards subject |
| `dolly_out` | Z axis ← target | Pull away from subject |
| `tracking_l_to_r` | X axis → | Lateral movement right |
| `tracking_r_to_l` | X axis ← | Lateral movement left |
| `orbital_cw` | Orbit around Y | Circular movement clockwise |
| `orbital_ccw` | Orbit around Y | Circular movement counterclockwise |
| `crane_up` | Y axis ↑ | Vertical rise |
| `crane_down` | Y axis ↓ | Vertical descent |
| `push_in_zoom` | FOV decrease | Zoom while pushing in |
| `whip_pan_l` | Rapid Y rotation | Fast pan left |
| `whip_pan_r` | Rapid Y rotation | Fast pan right |
| `static_hold` | None | Locked-off shot |

### Example Static Config

```json
{
  "resolution": [1920, 1080],
  "fps": 24,
  "cameras": [
    {
      "name": "Shoulder",
      "position": [1.2, 2.0, 1.6],
      "look_at": [0, 0, 1.2],
      "focal_length": 85
    }
  ],
  "character_position": [0, 0, 0],
  "character_height": 1.8
}
```

### Example Animated Config

```json
{
  "resolution": [1920, 1080],
  "fps": 24,
  "cameras": [
    {
      "name": "Dolly",
      "position": [0, -5, 1.6],
      "look_at": [0, 0, 1.2],
      "focal_length": 50
    }
  ],
  "keyframes": [
    {"frame": 0, "position": [0, -5, 1.6], "look_at": [0, 0, 1.2]},
    {"frame": 48, "position": [0, -2, 1.6], "look_at": [0, 0, 1.2]}
  ],
  "character_position": [0, 0, 0],
  "character_height": 1.8
}
```

## Limitations

- **No video input**: Agnes Flash returns HTTP 400 for `videos` parameter
- **PlayBlast**: Requires OpenGL context, unavailable in `--background` mode
- **Fallback**: Use EEVEE rendering in background mode (slower but works)
- **Max 5 reference images**: Agnes reference mode limit

## Troubleshooting

### PlayBlast Fails in Background Mode

```bash
# PlayBlast requires OpenGL context
# Use EEVEE fallback instead
blender --background --python playblast_renderer.py -- --config scene.json --output ./.brandly/{project}/3d-spatial/cameras
```

### Agnes Returns HTTP 400

```python
# Check if you're passing video input (not supported)
# Use first_frame/last_frame instead
result = await create_video_task(
    prompt="...",
    first_frame="path/to/first_frame.png",  # ✅
    last_frame="path/to/last_frame.png",     # ✅
    # video="path/to/video.mp4",             # ❌ HTTP 400
)
```
