from .models import SiteSetting, THEME_CHOICES

_VALID_THEMES = {choice[0] for choice in THEME_CHOICES}
_DEFAULT_THEMES = {"light", ""}


class ThemeTemplateMixin:
    """
    View mixin that selects templates based on the active SiteSetting.theme.

    Resolution order (example for theme="dark", template_name="portfolio/home.html"):
      1. portfolio/dark/home.html   — theme override, used if it exists
      2. portfolio/home.html        — default fallback
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

    def get_template_names(self):
        candidates = super().get_template_names()
        theme = self._get_current_theme()
        if theme in _DEFAULT_THEMES:
            return candidates
        themed = []
        for tpl in candidates:
            parts = tpl.split("/", 1)
            if len(parts) == 2:
                themed.append(f"{parts[0]}/{theme}/{parts[1]}")
            else:
                themed.append(f"{theme}/{tpl}")
        return themed + candidates

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        theme = self._get_current_theme()
        if theme not in _DEFAULT_THEMES:
            ctx["base_template"] = f"portfolio/{theme}/base.html"
        ctx["motion_enabled"] = self._get_motion_enabled()
        return ctx
