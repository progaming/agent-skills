---
name: script-to-scene-images
description: "Turn a script + key visual into per-scene reference images."
version: 1.0.0
author: Hermes Agent
tags: [image-generation, animation, scene, reference, fal, image-to-image]
---

# Script-to-Scene Reference Images

Generate consistent scene-by-scene reference images for animators/artists using a key visual (concept art) and a script describing each scene.

## When to Use

- You have a script with multiple scenes/stages and a single key visual (concept art)
- You need per-scene reference images that match the key visual's style
- The output will be used by artists/animators as visual references

## Inputs Required

1. **Script** — A document describing scenes/stages in sequence. Each scene should have:
   - Scene number and title
   - Visual description (what should be visible)
   - Key elements (characters, objects, environment, mood)

2. **Key Visual** — A concept art image URL that defines the target:
   - Art style
   - Color palette
   - Line quality
   - Level of detail
   - Composition style

## Workflow

### Step 1: Analyze the Key Visual

Load the key visual with `vision_analyze` and extract:
- Art style (flat vector, watercolor, 3D render, anime cel-shaded, etc.)
- Color palette (dominant colors, accent colors)
- Line quality (clean outlines, soft edges, no lines)
- Level of detail (minimalist, moderate, highly detailed)
- Aspect ratio

### Step 2: Parse the Script

Read through the script and identify each distinct scene. For each, extract:
- Scene number and title
- What should be visible in the frame
- Key elements (characters, props, environment, lighting, mood)

### Step 3: Generate Images (Image-to-Image)

For each scene, call `image_generate` with:
- `image_url`: the key visual URL (forces image-to-image mode)
- `aspect_ratio`: match the key visual unless script specifies otherwise
- `prompt`: using the formula below

### Prompt Formula

```
Transform this image into a single scene showing: [SCENE DESCRIPTION].
Keep the exact same [ART STYLE], [COLOR PALETTE], [LINE QUALITY],
and [DETAIL LEVEL] as the original. Remove all other scenes/elements.
Only show [KEY ELEMENTS for this scene]. No text or labels.
```

**Example:**
```
Transform this image into a single scene showing: a bright sun heating
the ocean with wavy white arrows of water vapor rising from the surface.
Keep the exact same flat vector illustration style, blue-green-yellow
color palette, clean outlines, and moderate detail level as the original.
Remove all other scenes/elements. Only show the sun, ocean, and rising
vapor. No text or labels.
```

### Step 4: Batch in Parallel

Generate all scenes in parallel (multiple `image_generate` calls in one response) for efficiency.

### Step 5: Present Results

Output each image with:
- Scene number and title
- One-line description
- The generated image (markdown image syntax)

## Constraints & Pitfalls

- **Style consistency is paramount** — every image must match the key visual's art direction. If a scene description conflicts with the key visual's style, prioritize the key visual's style.
- **Content policy rejections** — if the model rejects a prompt (copyrighted characters, etc.), rephrase without naming the IP. Describe appearance generically instead (e.g., "elegant anime woman with dark indigo-blue hair" instead of "Yelan from Genshin Impact").
- **"Remove all other scenes"** — always include this instruction to prevent the model from cramming multiple stages into one frame.
- **No text/labels** — keep images clean for artist reference unless the scene specifically requires text.
- **Image-to-image, not text-to-image** — always pass `image_url` to ensure the model uses the key visual as a style base.

## Supported Models (FAL)

Models with `edit_endpoint` support image-to-image:
- FLUX 2 Klein 9B (fast, ~1s)
- FLUX 2 Pro (studio quality, ~6s)
- Nano Banana Pro (reasoning depth, ~8s)
- GPT Image 1.5 / GPT Image 2 (best prompt adherence)
- Z-Image Turbo (no edit support — text-to-image only)

Default to **GPT Image 2** for best prompt adherence on scene-specific instructions, or **FLUX 2 Pro** for speed + quality balance.
