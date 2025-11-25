import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from portfolio.models import SiteSetting
SiteSetting.objects.get_or_create(
    defaults={
        "hero_title": "Welcome to my portfolio",
        "hero_subtitle": "",
        "about_title": "About Me",
        "about_body": ""
    }
)
print("Default SiteSetting: ensured")
