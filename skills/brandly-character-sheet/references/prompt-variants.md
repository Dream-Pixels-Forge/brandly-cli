# Prompt Variations for Character Sheets

Different prompt formats for various use cases.

## Layout Convention (16:9 multi-view grid)

Character reference sheets are rendered as a **single 16:9 image split
into a 3-column grid**:

- **Left column**: front view (head and upper torso)
- **Middle column**: pure side profile
- **Right column**: three-quarter view

All three views show the same character at the same scale with consistent
studio lighting from the same direction in every panel, on a clean neutral
background, with thin white separator lines between the panels. Always
pass `--ratio 16:9` to `brandly reference` so the model produces this
layout. The grid gives `brandly video` multiple angles to lock onto for
character identity consistency across shots.

## Basic Prompt Format

```
[Age] [gender] [ethnicity] with [body type] build,
[face shape] face with [skin tone] skin,
[eye color] [eye shape] eyes,
[hair color] [hair texture] hair styled [hair style].
Wearing [outfit description].
[posture/movement note].
[Cinematic style descriptor].
```

## Detailed Prompt Format

```
Professional character reference sheet.
Subject: [Name/Description]
Appearance: [Complete physical description]
Wardrobe: [Complete outfit description]
Pose: [Standing/sitting/active pose]
Expression: [Facial expression]
Lighting: [Studio/natural/cinematic lighting]
Camera: [Lens type, angle]
Style: [Photorealistic/Cinematic/Illustration]
Quality: [8K/UHD/Professional photography]
```

## By Use Case

### Product Model
```
Fashion model, [age], wearing [product/outfit],
studio lighting, commercial photography,
neutral expression, professional pose.
```

### Character Acting
```
[Age] [gender], [ethnicity], with [distinctive features],
[expression], [action], [environment],
cinematic lighting, film grain.
```

### Lifestyle Content
```
[Casual/youthful] [gender], natural lighting,
relaxed pose, authentic expression,
lifestyle photography style.
```

### Luxury/Editorial
```
[Elegant/high-fashion] [gender], minimal background,
dramatic lighting, editorial style,
high-end aesthetic.
```

## Tips

- Replace bracketed placeholders with specific details
- Use exact color names (navy blue, not just blue)
- Include lighting and camera details
- Specify quality keywords (8K, UHD, commercial)
- Add style suffixes appropriate to the project
