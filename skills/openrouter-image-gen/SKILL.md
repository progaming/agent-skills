---
name: openrouter-image-gen
description: Generate images from text prompts using OpenRouter API vision models. Use when the user asks to create, generate, or draw images, pictures, illustrations, or visual art via AI. Supports Google Gemini Flash Image Preview, FLUX, and other vision-capable models available through OpenRouter. Triggers on requests like "generate an image", "create a picture", "draw a", "make an image of", or any task requiring AI image generation.
---

# OpenRouter Image Generation

Generate images from text prompts via the OpenRouter API.

## Quick Start

Use the bundled script for reliable, repeatable image generation:

```bash
python scripts/generate_image.py \
    --model "google/gemini-3.1-flash-image-preview" \
    --prompt "a serene mountain lake at sunrise" \
    --output ./lake.png
```

Requires `OPENROUTER_API_KEY` environment variable.

## Image-to-Image / Reference Image Support

You can supply a reference image to guide generation or editing. The script sends the image alongside your prompt to the model.

```bash
python scripts/generate_image.py \
    --model "google/gemini-3.1-flash-image-preview" \
    --reference ./original.png \
    --prompt "Brighten this image and make it more vibrant" \
    --output ./brightened.png
```

## Workflow

1. **Select model**: Use `google/gemini-3.1-flash-image-preview` as the default. See [references/models.md](references/models.md) for alternatives.
2. **Refine prompt**: Describe the scene clearly. Include style, lighting, subject, and composition details for best results.
3. **Run script**: Execute `scripts/generate_image.py` with `--model`, `--prompt`, and `--output`.
4. **Deliver result**: Confirm the saved file path to the user.

## Script Parameters

| Flag | Required | Description |
|------|----------|-------------|
| `--model` | Yes | OpenRouter model ID (e.g., `google/gemini-3.1-flash-image-preview`) |
| `--prompt` | Yes | Text description of the desired image |
| `--output` | Yes | Output file path. Extension infers format |
| `--reference` | No | Path to a reference image to send alongside the prompt |
| `--api-key` | No | Defaults to `OPENROUTER_API_KEY` env var |
| `--timeout` | No | Request timeout in seconds (default: 120) |

## API Response Handling

The script automatically handles multiple response formats:

- **Gemini**: Images in `message.images[]` with base64 data URLs
- **FLUX/Others**: Images in `message.content` as base64 strings or data URLs
- **Multi-image**: Saves additional images with `_1`, `_2` suffixes

## Error Handling

- If `OPENROUTER_API_KEY` is missing, the script exits with code 1 and prints an error.
- If the API returns an error, the raw error body is printed.
- If no images are found in the response, the script prints a truncated raw response for debugging.

## References

- **Supported models and tips**: See [references/models.md](references/models.md)
