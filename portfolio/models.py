from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import RegexValidator

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}){1,2}$',
    message='Enter a valid hex color, e.g. #00aaff'
)

THEME_CHOICES = (
    ("light", "Light"),
    ("dark", "Dark"),
    ("blue", "Blue"),
    ("green", "Green"),
    ("purple", "Purple"),
)

IMAGE_RATIO_CHOICES = (
    ("square", "Square (1:1)"),
    ("landscape", "Landscape (4:3)"),
    ("wide", "Wide (16:9)"),
    ("ultrawide", "Ultrawide (21:9)"),
    ("portrait", "Portrait (4:5)"),
)

IMAGE_FIT_CHOICES = (
    ("cover", "Cover (fill, crop edges)"),
    ("contain", "Contain (fit inside, letterbox)"),
)

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("portfolio:project_list") + f"?category={self.slug}"


class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, related_name="projects", on_delete=models.CASCADE)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to="projects/images/", blank=True, null=True)
    attachment = models.FileField(upload_to="projects/files/", blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords")
    tech_stack = models.CharField(max_length=255, blank=True, help_text="Comma-separated technologies, e.g. Python, Django, PostgreSQL")
    repo_url = models.URLField(blank=True, help_text="GitHub / source repository URL")
    live_url = models.URLField(blank=True, help_text="Live demo / deployed URL")
    is_featured = models.BooleanField(default=False)
    visible = models.BooleanField(default=True, help_text="Uncheck to hide from public pages")
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self):
        return reverse("portfolio:project_detail", args=[self.slug])


class SiteSetting(models.Model):
    # Personal info
    full_name = models.CharField(max_length=180, blank=True, help_text="Your display name")
    headline = models.CharField(max_length=255, blank=True, help_text="Short tagline, e.g. 'Data Analyst | Python Developer'")
    bio_short = models.CharField(max_length=300, blank=True, help_text="One-liner for cards and meta descriptions")
    bio_long = models.TextField(blank=True, help_text="Full bio for the About page")
    headshot = models.ImageField(upload_to="site/headshot/", blank=True, null=True, help_text="Professional headshot photo")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile URL")
    github_url = models.URLField(blank=True, help_text="GitHub profile URL")

    # Hero section
    hero_title = models.CharField(max_length=180, default="Welcome to my portfolio")
    hero_subtitle = models.CharField(max_length=255, blank=True)
    hero_image = models.ImageField(upload_to="site/hero/", blank=True, null=True)
    about_title = models.CharField(max_length=180, default="About Me")
    about_body = models.TextField(blank=True)
    resume_file = models.FileField(upload_to="resumes/", blank=True, null=True, help_text="Upload a resume PDF for site-wide download link")

    # theme choice retained for quick presets
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="light", help_text="Visual theme preset")
    motion_enabled = models.BooleanField(default=True, help_text="Enable CSS animations and transitions")
    default_image_ratio = models.CharField(max_length=20, choices=IMAGE_RATIO_CHOICES, default="landscape", help_text="Default aspect ratio for images site-wide")
    default_image_fit = models.CharField(max_length=10, choices=IMAGE_FIT_CHOICES, default="cover", help_text="Default object-fit for images")

    # Per-color fields (hex strings). Use HTML5 color pickers in admin.
    primary_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#0d6efd", help_text="Primary brand color (hex)")
    button_text_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#ffffff")
    nav_bg_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#0b1220")
    nav_text_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#ffffff")
    hero_start_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#0d6efd")
    hero_end_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#6f42c1")
    hero_text_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#ffffff")
    footer_bg_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#0f172a")
    footer_text_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#cbd5e1")
    page_bg_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#f8fafc")
    text_color = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#0f172a")

    class Meta:
        verbose_name = "Site setting"
        verbose_name_plural = "Site settings"

    def __str__(self) -> str:
        return "Site Settings"


class Resume(models.Model):
    category = models.CharField(
        max_length=50,
        default="general",
        help_text="Category label, e.g. general/finance/marketing."
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="If true, this resume is the primary one for its category."
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="resumes/", help_text="Primary resume file (PDF or DOCX)")
    preview_pdf = models.FileField(upload_to="resumes/previews/", blank=True, null=True, help_text="Optional PDF for inline preview (use when main file is DOCX)")
    alternate_file = models.FileField(upload_to="resumes/", blank=True, null=True, help_text="Optional second format (e.g. DOCX if main is PDF, or vice versa)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Message from {self.name}: {self.subject}"


# ---- NavItem: editable navigation entries ----
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

class NavItem(models.Model):
    title = models.CharField(max_length=120)
    url = models.CharField(max_length=255, blank=True, help_text="Relative (e.g., /about/) or absolute URL (https://...)")
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, db_index=True)
    visible = models.BooleanField(default=True)
    external = models.BooleanField(default=False, help_text="Treat url as external")
    new_tab = models.BooleanField(default=False, help_text="Open in new tab")
    login_required = models.BooleanField(default=False, help_text="Show only to authenticated users")
    allowed_groups = models.ManyToManyField(Group, blank=True, help_text="If set, only members of these groups see the item")
    icon = models.CharField(max_length=64, blank=True, help_text="Optional icon class (fontawesome)")

    class Meta:
        ordering = ("order", "title")
        verbose_name = "Navigation item"
        verbose_name_plural = "Navigation items"

    def __str__(self):
        return self.title

    def get_link(self):
        return self.url or "#"

# Clear nav cache after changes
@receiver([post_save, post_delete], sender=NavItem)
def _clear_nav_cache(sender, **kwargs):
    try:
        cache.delete('nav_items_v1')
    except:
        pass

