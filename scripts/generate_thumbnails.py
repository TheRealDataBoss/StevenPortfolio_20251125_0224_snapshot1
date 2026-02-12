"""
Generate professional placeholder thumbnails for Projects and Certifications
that have empty image fields.

Usage:
    python scripts/generate_thumbnails.py

Generates 1200x800 PNG images with dark-blue-to-slate gradient backgrounds
and centered white title text. Saves originals under
scripts/seed_assets/generated/ and attaches to Django model instances via
their ImageField. Idempotent — skips any object that already has an image.
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

from django.core.files import File
from portfolio.models import Category, Certification, Project

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1200, 800
OUTPUT_DIR = SCRIPT_DIR / "seed_assets" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Gradient colours (top → bottom): dark navy to cool slate
COLOR_TOP = (13, 27, 56)       # #0d1b38
COLOR_BOTTOM = (44, 62, 80)    # #2c3e50

# Font setup — prefer Segoe UI Bold, fall back through Windows fonts
WINFONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_CANDIDATES = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]


def _load_font(size):
    for name in FONT_CANDIDATES:
        path = WINFONTS / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = _load_font(52)
FONT_SUB = _load_font(28)


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------
def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _gradient(draw, width, height, top, bottom):
    """Draw a vertical linear gradient."""
    for y in range(height):
        t = y / (height - 1)
        r = _lerp(top[0], bottom[0], t)
        g = _lerp(top[1], bottom[1], t)
        b_ = _lerp(top[2], bottom[2], t)
        draw.line([(0, y), (width, y)], fill=(r, g, b_))


def _draw_accent_line(draw, cx, y, length=120):
    """Draw a thin horizontal accent line."""
    draw.line(
        [(cx - length // 2, y), (cx + length // 2, y)],
        fill=(77, 166, 255),  # bright accent blue
        width=3,
    )


def _multiline_center(draw, lines, font, cx, start_y, line_spacing=10):
    """Draw multiple lines of text centered horizontally."""
    y = start_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, y), line, fill=(255, 255, 255), font=font)
        y += th + line_spacing
    return y


def generate_thumbnail(title, subtitle, filename):
    """Create a 1200x800 gradient thumbnail with centered text."""
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return filepath  # already generated

    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Gradient background
    _gradient(draw, WIDTH, HEIGHT, COLOR_TOP, COLOR_BOTTOM)

    # Subtle border inset
    draw.rectangle(
        [(30, 30), (WIDTH - 31, HEIGHT - 31)],
        outline=(255, 255, 255, 40),
        width=1,
    )

    cx = WIDTH // 2

    # Wrap long titles to fit within image width (max ~28 chars per line)
    wrapped = textwrap.wrap(title, width=28)

    # Calculate vertical centering
    # Measure total block height: title lines + accent + subtitle
    title_line_heights = []
    for line in wrapped:
        bbox = FONT_TITLE.getbbox(line)
        title_line_heights.append(bbox[3] - bbox[1])
    title_block = sum(title_line_heights) + 10 * (len(wrapped) - 1)

    sub_bbox = FONT_SUB.getbbox(subtitle)
    sub_h = sub_bbox[3] - sub_bbox[1]

    total_block = title_block + 40 + 3 + 40 + sub_h  # title + gap + accent + gap + sub
    start_y = (HEIGHT - total_block) // 2

    # Draw title lines
    y = _multiline_center(draw, wrapped, FONT_TITLE, cx, start_y)

    # Accent line
    y += 20
    _draw_accent_line(draw, cx, y)
    y += 23

    # Subtitle
    y += 10
    sub_bbox_full = draw.textbbox((0, 0), subtitle, font=FONT_SUB)
    sw = sub_bbox_full[2] - sub_bbox_full[0]
    draw.text(
        (cx - sw // 2, y),
        subtitle,
        fill=(180, 200, 220),
        font=FONT_SUB,
    )

    img.save(filepath, "PNG", optimize=True)
    return filepath


# ---------------------------------------------------------------------------
# Assign to Django objects
# ---------------------------------------------------------------------------
def assign_image(instance, label, image_path):
    """Attach generated image to instance.image if currently empty."""
    if instance.image:
        print(f"  SKIP  {label}: already has image")
        return
    with open(image_path, "rb") as f:
        instance.image.save(image_path.name, File(f), save=True)
    print(f"  SET   {label}: {image_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("GENERATING PLACEHOLDER THUMBNAILS")
    print("=" * 60)

    # Projects
    print("\nProjects:")
    for proj in Project.objects.all():
        slug = proj.slug or proj.title.lower().replace(" ", "-")
        filename = f"project_{slug}.png"
        subtitle = proj.category.name if proj.category else "Project"
        path = generate_thumbnail(proj.title, subtitle, filename)
        assign_image(proj, proj.title, path)

    # Certifications
    print("\nCertifications:")
    for cert in Certification.objects.all():
        safe_name = cert.name.lower().replace(" ", "-").replace(".", "")
        filename = f"cert_{safe_name}.png"
        subtitle = f"Issued by {cert.issuer}" if cert.issuer else "Certification"
        path = generate_thumbnail(cert.name, subtitle, filename)
        assign_image(cert, cert.name, path)

    # Categories
    print("\nCategories:")
    for cat in Category.objects.all():
        safe_name = cat.slug or cat.name.lower().replace(" ", "-")
        filename = f"category_{safe_name}.png"
        subtitle = "Category"
        path = generate_thumbnail(cat.name, subtitle, filename)
        assign_image(cat, cat.name, path)

    print("\n" + "=" * 60)
    print("THUMBNAIL GENERATION COMPLETE")
    print(f"  Output dir: {OUTPUT_DIR}")
    print(f"  Categories processed:      {Category.objects.count()}")
    print(f"  Projects processed:        {Project.objects.count()}")
    print(f"  Certifications processed:  {Certification.objects.count()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
