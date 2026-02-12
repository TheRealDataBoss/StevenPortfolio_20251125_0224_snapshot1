from django.conf import settings as django_settings

from .models import LayoutProfile, SiteSetting, THEME_CHOICES, resolve_active_profile

_VALID_THEMES = {choice[0] for choice in THEME_CHOICES}
_DEFAULT_THEMES = {"light", ""}


class ThemeTemplateMixin:
    """
    View mixin that selects templates based on theme and template variant.

    Resolution order (example for variant="modern_saas", template="portfolio/home.html"):
      1. portfolio/variants/modern_saas/home.html   — variant override
      2. portfolio/home.html                        — default fallback

    If a dark theme is also active, themed paths are tried before defaults:
      1. portfolio/variants/modern_saas/dark/home.html
      2. portfolio/variants/modern_saas/home.html
      3. portfolio/dark/home.html
      4. portfolio/home.html
    """

    def _get_current_theme(self):
        if not hasattr(self, "_resolved_theme"):
            try:
                obj = SiteSetting.objects.only("theme").first()
                theme = obj.theme if obj else "light"
            except Exception:
                theme = "light"
            if theme not in _VALID_THEMES:
                theme = "light"
            self._resolved_theme = theme
        return self._resolved_theme

    def _get_motion_enabled(self):
        if not hasattr(self, "_resolved_motion"):
            try:
                obj = SiteSetting.objects.only("motion_enabled").first()
                self._resolved_motion = obj.motion_enabled if obj else True
            except Exception:
                self._resolved_motion = True
        return self._resolved_motion

    def _get_layout_category(self):
        """Return the Category for layout profile resolution, or None."""
        obj = getattr(self, 'object', None)
        if obj and hasattr(obj, 'category'):
            return obj.category
        return None

    def _resolve_layout_profile(self):
        """Resolve and cache the active LayoutProfile (with ?profile= override)."""
        if not hasattr(self, "_resolved_profile"):
            category = self._get_layout_category()
            profile = resolve_active_profile(category)

            if django_settings.DEBUG:
                preview_slug = self.request.GET.get("profile")
                if preview_slug:
                    try:
                        profile = LayoutProfile.objects.get(slug=preview_slug)
                    except LayoutProfile.DoesNotExist:
                        pass  # ignore bad slug

            self._resolved_profile = profile
        return self._resolved_profile

    def _get_template_variant(self):
        """Return the active template variant slug (cached)."""
        profile = self._resolve_layout_profile()
        return profile.template_variant if profile else "default"

    def get_template_names(self):
        candidates = super().get_template_names()

        # Theme resolution (dark theme)
        theme = self._get_current_theme()
        if theme not in _DEFAULT_THEMES:
            themed = []
            for tpl in candidates:
                parts = tpl.split("/", 1)
                if len(parts) == 2:
                    themed.append(f"{parts[0]}/{theme}/{parts[1]}")
                else:
                    themed.append(f"{theme}/{tpl}")
            candidates = themed + candidates

        # Variant resolution — prepend variant-specific paths
        variant = self._get_template_variant()
        if variant:
            variant_paths = []
            for tpl in candidates:
                parts = tpl.split("/", 1)
                if len(parts) == 2:
                    variant_paths.append(f"{parts[0]}/variants/{variant}/{parts[1]}")
                else:
                    variant_paths.append(f"variants/{variant}/{tpl}")
            candidates = variant_paths + candidates

        return candidates

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        theme = self._get_current_theme()
        if theme not in _DEFAULT_THEMES:
            ctx["base_template"] = f"portfolio/{theme}/base.html"
        ctx["motion_enabled"] = self._get_motion_enabled()

        # Layout profile / variant (uses cached values from _resolve_layout_profile)
        profile = self._resolve_layout_profile()
        variant = self._get_template_variant()

        ctx["active_profile"] = profile
        ctx["template_variant"] = variant
        ctx["layout_theme_mode"] = profile.theme_mode if profile else ""
        ctx["layout_accent_theme"] = profile.accent_theme if profile else "inherit"

        # Design token overrides for hero/headshot images
        if profile and profile.hero_image:
            ctx["resolved_hero_image"] = profile.hero_image
        if profile and profile.headshot_image:
            ctx["resolved_headshot_image"] = profile.headshot_image

        return ctx
