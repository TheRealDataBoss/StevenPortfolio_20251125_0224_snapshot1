from django.db.models import Prefetch
from .models import Category, NavItem, Resume, SiteSetting

def navigation(request):
    """
    Navigation context processor.
    Returns:
        - nav_items: top-level NavItem queryset with children prefetched
        - nav_categories: Category queryset
        - site_settings: first SiteSetting
    """
    user = request.user

    # Build base queryset for visible items
    def visible_items():
        qs = NavItem.objects.filter(visible=True)
        if not user.is_authenticated:
            qs = qs.filter(login_required=False)
        return qs

    # Prefetch visible children
    children_qs = visible_items().filter(parent__isnull=False).order_by('order')

    # Top-level items with children prefetched
    nav_items = (
        visible_items()
        .filter(parent__isnull=True)
        .prefetch_related(Prefetch('children', queryset=children_qs))
        .order_by('order')
    )

    # Filter by allowed_groups if set
    if user.is_authenticated:
        user_groups = set(user.groups.values_list('pk', flat=True))
        nav_items = [
            item for item in nav_items
            if not item.allowed_groups.exists() or item.allowed_groups.filter(pk__in=user_groups).exists()
        ]
    else:
        nav_items = [item for item in nav_items if not item.allowed_groups.exists()]

    return {
        "nav_items": nav_items,
        "nav_categories": Category.objects.all(),
        "site_settings": SiteSetting.objects.first(),
    }
