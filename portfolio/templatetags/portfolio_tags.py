from django import template
from django.utils.html import format_html

from portfolio.models import SiteSetting

register = template.Library()


@register.filter
def split(value, sep=","):
    """Split a string by separator and strip whitespace from each part."""
    if not value:
        return []
    return [item.strip() for item in value.split(sep)]


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
