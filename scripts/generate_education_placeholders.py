"""
Generate deterministic placeholder images for EducationEntry items with no image.

Usage:
    python scripts/generate_education_placeholders.py

Creates 600x400 gradient PNGs in media/education/images/{slug}_placeholder.png.
Idempotent: never overwrites existing EducationEntry.image or existing files.
"""

import os
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Django bootstrap
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.conf import settings
from django.utils.text import slugify
from portfolio.models import EducationEntry

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 600, 400
OUTPUT_DIR = Path(settings.MEDIA_ROOT) / "education" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PALETTES = [
    ((13, 27, 56), (44, 62, 80)),     # navy -> slate
    ((20, 60, 90), (40, 100, 130)),    # teal-blue
    ((50, 20, 70), (90, 50, 120)),     # purple
    ((15, 50, 40), (40, 90, 70)),      # forest
    ((80, 30, 20), (130, 60, 40)),     # rust
    ((30, 30, 50), (70, 70, 100)),     # steel
]

WINFONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_CANDIDATES = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]


def _load_font(size):
    for name in FONT_CANDIDATES:
        path = WINFONTS / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = _load_font(36)
FONT_SUB = _load_font(20)


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------
def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _gradient(draw, w, h, top, bottom):
    for y in range(h):
        t = y / max(h - 1, 1)
        draw.line([(0, y), (w, y)], fill=(
            _lerp(top[0], bottom[0], t),
            _lerp(top[1], bottom[1], t),
            _lerp(top[2], bottom[2], t),
        ))


def generate_placeholder(institution, slug):
    """Create a placeholder PNG and return its Path. Skips if file exists."""
    filename = f"{slug}_placeholder.png"
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return filepath

    palette_idx = hash(slug) % len(PALETTES)
    top_color, bottom_color = PALETTES[palette_idx]

    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    _gradient(draw, WIDTH, HEIGHT, top_color, bottom_color)

    # Border inset
    draw.rectangle([(16, 16), (WIDTH - 17, HEIGHT - 17)], outline=(255, 255, 255, 50), width=1)

    cx = WIDTH // 2

    # Wrap institution name
    wrapped = textwrap.wrap(institution, width=24)

    # Measure title block
    line_heights = []
    for line in wrapped:
        bbox = FONT_TITLE.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])
    title_block_h = sum(line_heights) + 8 * max(len(wrapped) - 1, 0)

    sub_text = "Education"
    sub_bbox = FONT_SUB.getbbox(sub_text)
    sub_h = sub_bbox[3] - sub_bbox[1]

    total_h = title_block_h + 30 + sub_h
    y = (HEIGHT - total_h) // 2

    # Draw institution name
    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=FONT_TITLE)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, y), line, fill=(255, 255, 255), font=FONT_TITLE)
        y += line_heights[i] + 8

    # Accent line
    y += 6
    draw.line([(cx - 50, y), (cx + 50, y)], fill=(77, 166, 255), width=2)
    y += 14

    # Subtitle
    sw = sub_bbox[2] - sub_bbox[0]
    draw.text((cx - sw // 2, y), sub_text, fill=(180, 200, 220), font=FONT_SUB)

    img.save(filepath, "PNG", optimize=True)
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("GENERATING EDUCATION PLACEHOLDERS")
    print("=" * 60)

    created = 0
    skipped = 0

    for entry in EducationEntry.objects.all():
        if entry.image:
            print(f"  SKIP  {entry.institution}: already has image")
            skipped += 1
            continue

        slug = slugify(entry.institution)
        filepath = generate_placeholder(entry.institution, slug)

        rel_path = f"education/images/{filepath.name}"
        entry.image = rel_path
        entry.save(update_fields=["image"])
        print(f"  SET   {entry.institution}: {rel_path}")
        created += 1

    print()
    print("=" * 60)
    print("EDUCATION PLACEHOLDERS COMPLETE")
    print(f"  Created: {created}   Skipped: {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    main()
