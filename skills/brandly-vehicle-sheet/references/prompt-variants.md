# Prompt Variations for Vehicle Sheets

Different prompt formats for various vehicle types.

## Basic Prompt Format

```
[Vehicle type] [color] [generation].
[Body style] with [distinctive features].
[Wheel design] with [tire type].
[Setting: studio/garage/road/nature].
[Lighting: studio/natural/dramatic].
Automotive photography style.
Quality: [8K/Commercial/Professional]
```

## By Vehicle Type

### Luxury Sedan
```
Luxury sedan, [color], [generation],
[elegant lines], [premium details],
[sophisticated setting], executive presence,
automotive photography, 8K quality.
```

### Sports Car
```
Sports car, [color], [aggressive stance],
[aerodynamic features], [large wheels],
[dynamic setting], performance oriented,
automotive action photography.
```

### SUV/Adventure
```
SUV, [color], [rugged styling],
[roof rails], [all-terrain tires],
[outdoor setting], adventure ready,
lifestyle automotive photography.
```

### Electric Vehicle
```
Electric vehicle, [color], [aerodynamic design],
[LED lighting], [minimal grille],
[modern setting], sustainable future,
tech-forward automotive photography.
```

### Classic/Vintage
```
Classic car, [color], [period-correct],
[chrome details], [whitewall tires],
[garage/museum setting], restored condition,
heritage automotive photography.
```

### Truck/Pickup
```
Pickup truck, [color], [work-ready],
[cargo bed], [towing package],
[work/recreation setting], utility focused,
commercial automotive photography.
```

## Multi-Angle Series

### Standard Angle Set
```
1. Front 3/4 hero shot
2. Side profile
3. Rear view
4. Interior dashboard
5. Detail close-up (wheel/headlight)
```

### Generated prompts:
```bash
# Front view
brandly image --prompt "[Vehicle] front three-quarter view, dynamic"

# Side view
brandly image --prompt "[Vehicle] side profile, clean background"

# Rear view
brandly image --prompt "[Vehicle] rear view, showing taillights"

# Interior
brandly image --prompt "[Vehicle] interior, dashboard and seats"
```

## Color Variants

Generate for each color option:
```
[Pellet color]: [exact color name]
[Accent color]: [trim, wheels, etc.]
```

Example:
```
- Pearl White: [body color]
- Black accents: [roof, mirrors]
- Silver alloy: [wheels]
```

## Lighting Styles

### Studio
```
Studio lighting, clean background,
product showcase, commercial quality
```

### Natural
```
Natural lighting, outdoor setting,
golden hour, lifestyle feel
```

### Dramatic
```
Dramatic lighting, high contrast,
moody atmosphere, cinematic style
```

### Night
```
Night setting, city lights,
neon reflections, urban atmosphere
```

## Tips

- Use manufacturer color names
- Specify exact model year/generation
- Note wheel design precisely
- Match setting to vehicle class
- Include lighting style for mood
