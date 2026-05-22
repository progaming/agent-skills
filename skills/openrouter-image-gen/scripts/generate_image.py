#!/usr/bin/env python3
"""
OpenRouter Image Generator

Generates images via the OpenRouter API using vision-capable models.
Supports models like Google Gemini Flash Image Preview, FLUX, etc.

Usage:
    python generate_image.py --model "google/gemini-3.1-flash-image-preview" \
                             --prompt "a cute cat on a windowsill" \
                             --output ./cat.png

Environment:
    OPENROUTER_API_KEY - Required. Your OpenRouter API key.
    Can be set via a .env file in the current working directory.
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _load_env_file(path: str = ".env") -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate images using OpenRouter API vision models."
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model ID on OpenRouter (e.g., google/gemini-3.1-flash-image-preview)",
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Text prompt describing the image to generate.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path for the generated image. Extension sets format.",
    )
    parser.add_argument(
        "--reference",
        default=None,
        help="Path to a reference image to send alongside the prompt.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENROUTER_API_KEY", ""),
        help="OpenRouter API key. Defaults to OPENROUTER_API_KEY env var.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds (default: 120).",
    )
    return parser.parse_args()


def _encode_image_to_data_url(path: str) -> str:
    """Read an image file and return a base64 data URL."""
    img_path = Path(path)
    if not img_path.exists():
        raise FileNotFoundError(f"Reference image not found: {path}")
    ext = img_path.suffix.lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        ext = "png"
    b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"


def call_openrouter(api_key: str, model: str, prompt: str, timeout: int, reference_path: str | None = None) -> dict:
    """Send chat completion request to OpenRouter and return parsed JSON."""
    if reference_path:
        content = [
            {"type": "image_url", "image_url": {"url": _encode_image_to_data_url(reference_path)}},
            {"type": "text", "text": prompt},
        ]
    else:
        content = prompt

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    req = Request(
        OPENROUTER_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"OpenRouter API error {e.code}: {body}") from e


def extract_images(response: dict) -> list[bytes]:
    """Extract image bytes from OpenRouter chat completion response.

    Returns a list of image byte strings. Supports multiple response formats:
    - choices[0].message.images (Gemini-style)
    - choices[0].message.content with base64 data URLs
    """
    images = []
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})

    # Format 1: Gemini-style `images` array on message
    raw_images = message.get("images")
    if raw_images:
        for img in raw_images:
            if isinstance(img, dict):
                img_url_obj = img.get("image_url", img)
                if isinstance(img_url_obj, dict):
                    url = img_url_obj.get("url", "")
                else:
                    url = str(img_url_obj)
            elif isinstance(img, str):
                url = img
            else:
                continue

            b64_data = _strip_data_url(url)
            if b64_data:
                images.append(base64.b64decode(b64_data))
        return images

    # Format 2: Content is a data URL string
    content = message.get("content")
    if isinstance(content, str):
        b64_data = _strip_data_url(content)
        if b64_data:
            images.append(base64.b64decode(b64_data))

    # Format 3: Content is an array of parts (OpenAI-style)
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url", "")
                b64_data = _strip_data_url(url)
                if b64_data:
                    images.append(base64.b64decode(b64_data))

    return images


def _strip_data_url(url: str) -> str | None:
    """Remove data:image/...;base64, prefix and return raw base64, or None."""
    if not url:
        return None
    match = re.match(r"^data:image/[^;]+;base64,(.+)", url)
    if match:
        return match.group(1)
    # If it's already base64 without prefix, return as-is
    if re.match(r"^[A-Za-z0-9+/=]+$", url):
        return url
    return None


def save_image(data: bytes, path: str) -> Path:
    """Write image bytes to disk."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return out_path


def main():
    _load_env_file()

    args = parse_args()

    if not args.api_key:
        print("Error: OPENROUTER_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating image with model: {args.model}")
    if args.reference:
        print(f"Reference image: {args.reference}")
    print(f"Prompt: {args.prompt}")

    try:
        response = call_openrouter(
            api_key=args.api_key,
            model=args.model,
            prompt=args.prompt,
            timeout=args.timeout,
            reference_path=args.reference,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    images = extract_images(response)

    if not images:
        print("Error: No images found in response.", file=sys.stderr)
        print("Raw response:", file=sys.stderr)
        print(json.dumps(response, indent=2)[:2000], file=sys.stderr)
        sys.exit(1)

    out_path = save_image(images[0], args.output)
    print(f"Saved image ({len(images[0])} bytes) to: {out_path}")

    if len(images) > 1:
        base = out_path.stem
        suffix = out_path.suffix
        parent = out_path.parent
        for i, img_data in enumerate(images[1:], start=1):
            extra_path = parent / f"{base}_{i}{suffix}"
            extra_path.write_bytes(img_data)
            print(f"Saved additional image to: {extra_path}")


if __name__ == "__main__":
    main()
