import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from portfolio.models import NavItem


def upsert_nav(title, defaults=None, parent=None):
    defaults = defaults or {}
    obj, created = NavItem.objects.get_or_create(
        title=title,
        parent=parent,
        defaults=defaults,
    )
    changed = created
    for k, v in defaults.items():
        if getattr(obj, k) != v:
            setattr(obj, k, v)
            changed = True
    if changed:
        obj.save()
    return obj


def main():
    # Top-level order:
    # 1 Home, 2 Portfolio, 3 Resume, 4 Projects, 5 GitHub, 6 LinkedIn, 7 About, 8 Contact
    upsert_nav("Home", defaults={"url": "/", "order": 1, "icon": "fas fa-home", "visible": True})

    portfolio = upsert_nav(
        "Portfolio",
        defaults={"url": "#", "order": 2, "icon": "fas fa-folder-open", "visible": True},
        parent=None,
    )

    upsert_nav("Resume", defaults={"url": "/resume/", "order": 3, "icon": "fas fa-file-alt", "visible": True})
    upsert_nav("Projects", defaults={"url": "/projects/", "order": 4, "icon": "fas fa-briefcase", "visible": True})
    upsert_nav("GitHub", defaults={"url": "https://github.com/TheRealDataBoss", "order": 5, "icon": "fab fa-github", "visible": True, "new_tab": True})
    upsert_nav("LinkedIn", defaults={"url": "https://www.linkedin.com/in/databoss/", "order": 6, "icon": "fab fa-linkedin", "visible": True, "new_tab": True})
    upsert_nav("About", defaults={"url": "/about/", "order": 7, "icon": "fas fa-user", "visible": True})
    upsert_nav("Contact", defaults={"url": "/contact/", "order": 8, "icon": "fas fa-envelope", "visible": True})

    # Portfolio dropdown children
    upsert_nav("Projects", defaults={"url": "/projects/", "order": 1, "icon": "fas fa-briefcase", "visible": True}, parent=portfolio)
    upsert_nav("Resume", defaults={"url": "/resume/", "order": 2, "icon": "fas fa-file-alt", "visible": True}, parent=portfolio)
    upsert_nav("GitHub", defaults={"url": "https://github.com/TheRealDataBoss", "order": 3, "icon": "fab fa-github", "visible": True, "new_tab": True}, parent=portfolio)
    upsert_nav("LinkedIn", defaults={"url": "https://www.linkedin.com/in/databoss/", "order": 4, "icon": "fab fa-linkedin", "visible": True, "new_tab": True}, parent=portfolio)

    print("Updated nav order.")


if __name__ == "__main__":
    main()
