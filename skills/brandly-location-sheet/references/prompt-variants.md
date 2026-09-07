# Prompt Variations for Location Sheets

Different prompt formats for various location types.

## Layout Convention (16:9 full-frame)

Location reference sheets are rendered as a **single 16:9 image filling
the entire canvas** — ONE wide establishing shot with no grid, no split
panels, and no insets. This is the **opposite** of all other brandly sheet
types (object, character, vehicle, animal, plant, mecha) which use a
multi-view grid.

Always pass `--ratio 16:9` to `brandly reference` so the model produces
this full-frame layout. The single wide shot gives `brandly video` the
complete spatial context — architecture, atmosphere, lighting, depth — to
lock onto for environment continuity across shots. No people, no text
overlays, no UI elements.

## Basic Prompt Format

```
[Shot type] of [location type].
[Architectural style] with [key features].
[Time of day] lighting, [lighting quality].
[Atmosphere description].
[Cinematic style descriptor].
Quality: [8K/Commercial/Photorealistic]
```

## By Location Type

### Modern Interior
```
Modern [room type] with [materials],
large [window type], [lighting style],
minimal furniture, [color] palette,
contemporary design photography.
```

### Industrial Space
```
Industrial [space], exposed [materials],
high ceilings, [lighting type],
raw aesthetic, [mood] atmosphere.
```

### Luxury Setting
```
Luxury [interior/exterior], [premium materials],
statement [lighting/furniture],
[elegant] atmosphere, [style] photography.
```

### Natural/Outdoor
```
[Natural setting], [features],
[time of day] lighting, [weather],
landscape photography, [mood].
```

### Studio Setup
```
Studio [setup], seamless [background],
controlled lighting, clean environment,
product photography style.
```

## Shot Types

### Establishing Shot
```
Wide establishing shot of [location],
showing [key features], [lighting],
architectural photography, 8K quality.
```

### Medium Shot
```
Medium shot of [location], showing
[detail/context], [lighting],
interior design photography.
```

### Detail Shot
```
Close-up of [specific element],
showing [texture/material],
macro photography, 8K detail.
```

### Walkthrough
```
Smooth walkthrough of [location],
[room to room], natural flow,
cinematic video style.
```

## Tips

- Always specify time of day
- Include lighting quality
- Mention architectural style
- Note color palette
- Add atmosphere/mood descriptors
