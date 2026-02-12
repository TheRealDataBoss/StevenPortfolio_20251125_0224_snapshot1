from django import template
from django.utils.html import format_html

from portfolio.models import ImageVariant, SiteSetting

register = template.Library()


@register.filter
def split(value, sep=","):
    """Split a string by separator and strip whitespace from each part."""
    if not value:
        return []
    return [item.strip() for item in value.split(sep)]


@register.filter
def endswith(value, suffix):
    """Check if a string ends with a suffix (case-insensitive)."""
    if not value or not suffix:
        return False
    return str(value).lower().endswith(str(suffix).lower())


_HIDDEN_CODE_EXTENSIONS = frozenset({
    '.py', '.ps1', '.sh', '.js', '.ts', '.rb', '.php',
    '.java', '.c', '.cpp', '.cs', '.go', '.rs',
})


@register.filter
def is_hidden_attachment(att):
    """Return True if an attachment is a code file that should be hidden from detail pages."""
    title = getattr(att, 'title', '') or ''
    if title.strip().lower() == 'helper script':
        return True
    f = getattr(att, 'file', None)
    if f and f.name:
        ext = ('.' + f.name.rsplit('.', 1)[-1].lower()) if '.' in f.name else ''
        if ext in _HIDDEN_CODE_EXTENSIONS:
            return True
    return False


_VALID_RATIOS = {"square", "landscape", "wide", "ultrawide", "portrait"}
_VALID_FITS = {"cover", "contain"}


@register.simple_tag
def media_img(image, ratio="", fit="", alt="", extra_class="", rounded=True, shadow=False):
    """
    Render an <img> with aspect-ratio and object-fit utility classes.

    Usage:
        {% load portfolio_tags %}
        {% media_img image ratio="wide" fit="cover" alt="Photo" %}

    When ratio or fit are omitted, falls back to SiteSetting defaults.
    """
    if not image:
        return ""

    # Resolve defaults from SiteSetting when not explicitly provided
    if not ratio or not fit:
        try:
            settings = SiteSetting.objects.only(
                "default_image_ratio", "default_image_fit"
            ).first()
        except Exception:
            settings = None
        if not ratio:
            ratio = getattr(settings, "default_image_ratio", "landscape") or "landscape"
        if not fit:
            fit = getattr(settings, "default_image_fit", "cover") or "cover"

    # Build CSS class list
    classes = ["media-img"]
    if ratio in _VALID_RATIOS:
        classes.append(f"media-img--{ratio}")
    if fit in _VALID_FITS:
        classes.append(f"media-img--{fit}")
    if rounded:
        classes.append("media-img--rounded")
    if shadow:
        classes.append("media-img--shadow")
    if extra_class:
        classes.append(extra_class)

    url = image.url if hasattr(image, "url") else image
    return format_html(
        '<img src="{}" class="{}" alt="{}">',
        url,
        " ".join(classes),
        alt,
    )


# Mapping of ImageVariant names to predefined CSS classes
_VARIANT_CSS = {
    "hero": "img-hero",
    "card": "img-card",
    "square": "img-square",
    "portrait": "img-portrait",
}


@register.inclusion_tag("portfolio/components/_responsive_image.html")
def responsive_image(image=None, variant="", alt="", extra_class="", shape=""):
    """
    Render a responsive image via the _responsive_image.html partial.

    Usage:
        {% responsive_image image=project.image variant="card" alt=project.title %}
        {% responsive_image image=headshot variant="square" shape="circle" %}

    The variant can be:
      - A predefined name: "hero", "card", "square", "portrait"
      - An ImageVariant.name from the database (admin-created)
      - Empty string: uses SiteSetting.default_image_ratio

    The shape can be: "rect", "rounded", "circle" (overrides DB variant shape).
    """
    image_url = ""
    if image and hasattr(image, "url"):
        image_url = image.url
    elif image:
        image_url = str(image)

    classes = []
    inline_styles = []
    effective_shape = shape
    border_radius = ""
    allow_zoom = True

    if variant:
        # Check predefined CSS classes first
        if variant in _VARIANT_CSS:
            classes.append(_VARIANT_CSS[variant])
        else:
            # Look up an admin-created ImageVariant
            try:
                iv = ImageVariant.objects.get(name=variant)
                inline_styles.append(f"aspect-ratio: {iv.css_ratio}")
                inline_styles.append(f"object-fit: {iv.crop_mode}")
                inline_styles.append("width: 100%")
                inline_styles.append("display: block")
                if iv.width:
                    inline_styles.append(f"max-width: {iv.width}px")
                if iv.height:
                    inline_styles.append(f"max-height: {iv.height}px")
                if iv.object_position and iv.object_position != "center center":
                    inline_styles.append(f"object-position: {iv.object_position}")
                if iv.background_color:
                    inline_styles.append(f"background-color: {iv.background_color}")
                # Use DB shape unless param overrides
                if not effective_shape:
                    effective_shape = iv.shape
                border_radius = iv.border_radius
                allow_zoom = iv.allow_zoom
            except ImageVariant.DoesNotExist:
                classes.append("img-card")
    else:
        # Fall back to SiteSetting default
        try:
            settings = SiteSetting.objects.only("default_image_ratio").first()
            ratio = getattr(settings, "default_image_ratio", "landscape") or "landscape"
        except Exception:
            ratio = "landscape"
        classes.append(f"media-img media-img--{ratio} media-img--cover")

    # Shape handling
    if effective_shape == "circle":
        classes.append("img-shape-circle")
    elif effective_shape == "rounded":
        if border_radius:
            inline_styles.append(f"border-radius: {border_radius}")
            inline_styles.append("overflow: hidden")
        else:
            classes.append("img-shape-rounded")
    elif effective_shape == "rect":
        pass  # No rounding
    else:
        # No shape specified — backward-compatible default rounding
        classes.append("media-img--rounded")

    # Hover zoom (respects allow_zoom and requires an actual image)
    if image_url and allow_zoom:
        classes.append("img-hover-scale")

    if extra_class:
        classes.append(extra_class)

    css_style = "; ".join(inline_styles) + (";" if inline_styles else "")

    return {
        "image_url": image_url,
        "css_classes": " ".join(classes),
        "css_style": css_style,
        "alt_text": alt or "",
    }
