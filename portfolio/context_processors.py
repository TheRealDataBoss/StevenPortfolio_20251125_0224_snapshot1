from .models import Category, SiteSetting

def navigation(request):
    """
    Backwards-compatible navigation context processor.  Does not reference NavItem.
    Returns:
        - nav_categories: Category queryset
        - site_settings: first SiteSetting
    """
    return {
        "nav_categories": Category.objects.all(),
        "site_settings": SiteSetting.objects.first(),
    }
