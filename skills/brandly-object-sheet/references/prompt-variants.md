# Prompt Variations for Object Sheets

Different prompt formats for various product types.

## Layout Convention (16:9 multi-view grid)

Object reference sheets are rendered as a **single 16:9 image split into a
3-column grid**:

- **Left column**: front three-quarter view
- **Middle column**: pure side profile
- **Right column**: rear three-quarter view

All three views show the same object at the same scale on a single continuous
clean neutral background, with thin white separator lines between the panels.
Always pass `--ratio 16:9` to `brandly reference` so the model produces this
layout. The grid gives `brandly video` three angles to lock onto for object
consistency across shots.

## Basic Prompt Format

```
Professional product photography.
Subject: [Object name]
View: [Front/Side/3/4/Angle]
Background: [Color/material]
Lighting: [Studio/natural/dramatic]
Details: [Visible features to highlight]
Quality: [8K/UHD/Commercial]
Style: [Minimalist/Detailed/Luxury]
```

## By Product Type

### Electronics
```
[Sleek/modern] [device], showing [screen/ports/buttons],
studio lighting, clean background,
technical details visible, product photography.
```

### Beauty/Cosmetics
```
[Luxury/elegant] [product packaging], showing [texture/finish],
soft lighting, [color] background,
beauty product photography, high-end aesthetic.
```

### Fashion/Accessories
```
[Item] showing [material/texture/stitching],
model wearing or flat lay,
natural or studio lighting,
fashion photography style.
```

### Food/Beverage
```
[Fresh/appetizing] [food/drink], showing [steam/texture],
[lifestyle/table] setting,
natural lighting, food photography style.
```

### Home/Lifestyle
```
[Product] in [room context], showing [functionality],
lifestyle photography, warm lighting,
everyday use scenario.
```

## Multi-Shot Series

### Hero Sequence
```
1. Front three-quarter view
2. Side profile
3. Top view
4. Detail close-up (texture/logo)
5. Lifestyle/in-use shot
```

### Color Variants
```
Generate for each color option:
- [Color 1]: [description]
- [Color 2]: [description]
- [Color 3]: [description]
```

## Tips

- Always specify background type
- Include lighting style
- Mention scale context when relevant
- Use quality keywords (8K, UHD, commercial)
- Match style to product category
