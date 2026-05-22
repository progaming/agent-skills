# Supported Image Generation Models

Reference list of vision-capable models on OpenRouter that support image generation.

## Google Gemini (Recommended)

| Model ID | Description |
|----------|-------------|
| `google/gemini-3.1-flash-image-preview` | Fast, high-quality image generation. Good default choice. |
| `google/gemini-3-pro-image-preview` | Higher quality, slower. Use when detail matters. |
| `google/gemini-2.5-flash-image` | Earlier generation, still capable. |

## FLUX Models

| Model ID | Description |
|----------|-------------|
| `black-forest-labs/flux-schnell` | Fast FLUX variant. |
| `black-forest-labs/flux-dev` | Higher quality FLUX variant. |
| `black-forest-labs/flux-pro` | Best quality FLUX, slower. |

## Other Models

| Model ID | Description |
|----------|-------------|
| `recraft-ai/recraft-v3` | Vector-style and illustration generation. |

## Response Format Notes

Different models return images in slightly different response structures:

1. **Gemini models**: Images in `choices[0].message.images` as objects with `type: "image_url"` and `image_url.url` containing a base64 data URL.
2. **FLUX/Other models**: May return images in `choices[0].message.content` as a base64 data URL string, or as an array of content parts.

The `generate_image.py` script handles all known formats automatically.

## Tips

- Prompt quality directly affects output quality. Be descriptive.
- Gemini Flash Image Preview is the best balance of speed and quality.
- OpenRouter may rotate or update model IDs; verify availability via `/api/v1/models`.
