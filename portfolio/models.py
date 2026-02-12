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

CROP_MODE_CHOICES = (
    ("cover", "Cover (fill, crop edges)"),
    ("contain", "Contain (fit inside, letterbox)"),
)

SHAPE_CHOICES = (
    ("rect", "Rectangle (no rounding)"),
    ("rounded", "Rounded corners"),
    ("circle", "Circle (forces 1:1 ratio)"),
)


class ImageVariant(models.Model):
    """Admin-configurable image display presets (e.g. hero, card, portrait)."""
    name = models.CharField(max_length=60, unique=True, help_text="Slug-like key, e.g. hero, card, portrait")
    aspect_ratio = models.CharField(max_length=10, help_text="CSS ratio, e.g. 16:9, 4:3, 1:1")
    width = models.PositiveIntegerField(blank=True, null=True, help_text="Optional max width in px")
    height = models.PositiveIntegerField(blank=True, null=True, help_text="Optional max height in px")
    crop_mode = models.CharField(max_length=10, choices=CROP_MODE_CHOICES, default="cover", help_text="COVER crops to fill; CONTAIN fits fully with possible letterboxing")
    shape = models.CharField(max_length=10, choices=SHAPE_CHOICES, default="rect", help_text="RECT: no rounding; ROUNDED: custom radius; CIRCLE: fully round (1:1)")
    border_radius = models.CharField(max_length=20, blank=True, help_text='Custom border radius for ROUNDED shape, e.g. "12px" or "1rem"')
    object_position = models.CharField(max_length=40, default="center center", help_text='CSS object-position to control crop focus, e.g. "50% 20%"')
    background_color = models.CharField(max_length=30, blank=True, help_text='Background color for CONTAIN mode letterboxing, e.g. "#f0f0f0"')
    allow_zoom = models.BooleanField(default=True, help_text="Enable CSS scale on hover (only when site motion is enabled)")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Image variant"
        verbose_name_plural = "Image variants"

    def __str__(self):
        return f"{self.name} ({self.aspect_ratio})"

    @property
    def css_ratio(self):
        """Convert '16:9' → '16 / 9' for CSS aspect-ratio property."""
        return self.aspect_ratio.replace(":", " / ")


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/images/", blank=True, null=True)

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
    image_variant = models.ForeignKey(ImageVariant, blank=True, null=True, on_delete=models.SET_NULL, help_text="Display preset for this project's image")
    attachment = models.FileField(upload_to="projects/files/", blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Freeform project notes displayed on the detail page")
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


class ProjectAttachment(models.Model):
    project = models.ForeignKey(Project, related_name="attachments", on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to="projects/attachments/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Project attachment"
        verbose_name_plural = "Project attachments"

    @property
    def file_ext(self):
        if self.file and self.file.name:
            return self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""
        return ""

    @property
    def is_pdf(self):
        return self.file_ext == "pdf"

    @property
    def is_image(self):
        return self.file_ext in ("jpg", "jpeg", "png", "gif", "webp", "svg", "bmp")

    @property
    def is_text_previewable(self):
        return self.file_ext in (
            "py", "js", "ts", "json", "md", "txt", "csv", "yml", "yaml",
            "toml", "cfg", "ini", "html", "css", "xml", "sql",
            "sh", "bat", "ps1", "r", "rb", "go", "rs", "java", "c", "cpp", "h",
        )

    @property
    def is_audio(self):
        return self.file_ext in ("mp3", "wav", "ogg", "flac", "m4a")

    @property
    def is_video(self):
        return self.file_ext in ("mp4", "webm", "ogv", "mov")

    @property
    def is_notebook(self):
        return self.file_ext == "ipynb"

    @property
    def is_previewable(self):
        return self.is_pdf or self.is_image or self.is_text_previewable or self.is_notebook or self.is_audio or self.is_video

    @property
    def preview_kind(self):
        """Return a string tag for template branching: pdf/image/text/notebook/audio/video/none."""
        if self.is_pdf:
            return "pdf"
        if self.is_image:
            return "image"
        if self.is_notebook:
            return "notebook"
        if self.is_text_previewable:
            return "text"
        if self.is_audio:
            return "audio"
        if self.is_video:
            return "video"
        return "none"

    def __str__(self):
        if self.title:
            return self.title
        if self.file and self.file.name:
            return self.file.name.split("/")[-1]
        if self.external_url:
            return self.external_url
        return f"Attachment #{self.pk}"


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
    hero_label = models.CharField(max_length=80, blank=True, help_text="Small eyebrow label above the name, e.g. 'Personal Site'")
    hero_title = models.CharField(max_length=180, default="Welcome to my portfolio")
    hero_roles = models.CharField(max_length=255, blank=True, help_text="Pipe-separated roles, e.g. 'Data Analyst | Data Scientist | BI'")
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
    homepage_featured_projects_count = models.PositiveIntegerField(default=3, help_text="How many featured projects to show on the homepage")
    homepage_featured_category_blocks_count = models.PositiveIntegerField(default=3, help_text="How many category blocks to show in Featured Projects on homepage")

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
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                condition=models.Q(is_primary=True),
                name="unique_primary_per_category",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.is_primary:
            Resume.objects.filter(
                category=self.category, is_primary=True,
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

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


class EducationEntry(models.Model):
    title = models.CharField(max_length=200, help_text="Degree or program name")
    institution = models.CharField(max_length=200, help_text="School or university")
    category = models.ForeignKey(Category, related_name="education_entries", blank=True, null=True, on_delete=models.SET_NULL)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True, help_text="Institution or program URL")
    attachment = models.FileField(upload_to="education/files/", blank=True, null=True)
    image = models.ImageField(upload_to="education/images/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Education entry"
        verbose_name_plural = "Education entries"

    def __str__(self):
        return f"{self.title} — {self.institution}"


class Certification(models.Model):
    name = models.CharField(max_length=200, help_text="Certification name")
    issuer = models.CharField(max_length=200, help_text="Issuing organization")
    category = models.ForeignKey(Category, related_name="certifications", blank=True, null=True, on_delete=models.SET_NULL)
    issue_date = models.DateField(blank=True, null=True)
    expires_date = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True, help_text="Verification URL")
    description = models.TextField(blank=True)
    attachment = models.FileField(upload_to="certifications/files/", blank=True, null=True)
    image = models.ImageField(upload_to="certifications/images/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Certification"
        verbose_name_plural = "Certifications"

    def __str__(self):
        return f"{self.name} ({self.issuer})"


# ---------------------------------------------------------------------------
# Layout Profiles
# ---------------------------------------------------------------------------
TEMPLATE_VARIANT_CHOICES = (
    ("default", "Default"),
    ("modern_saas", "Modern SaaS"),
    ("executive_minimal", "Executive Minimal"),
    ("data_lab", "Data Lab"),
    ("split_screen", "Split Screen"),
    ("magazine_editorial", "Magazine Editorial"),
    ("card_dashboard", "Card Dashboard"),
    ("glass_modern", "Glass Modern"),
    ("bold_branding", "Bold Branding"),
    ("timeline_pro", "Timeline Pro"),
    ("technical_research", "Technical Research"),
)

ACCENT_THEME_CHOICES = (
    ("inherit", "Inherit from Site Settings"),
) + THEME_CHOICES

FONT_STACK_CHOICES = (
    ("system", "System (default)"),
    ("sans", "Sans-serif (Inter / Helvetica)"),
    ("serif", "Serif (Georgia / Merriweather)"),
)

TYPE_SCALE_CHOICES = (
    ("default", "Default"),
    ("compact", "Compact"),
    ("spacious", "Spacious"),
)


class LayoutProfile(models.Model):
    """Site-wide or category-specific layout profile.

    Resolution order: category override > site default > built-in fallback.
    """
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    category = models.OneToOneField(
        Category, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="layout_profile",
        help_text="Leave blank for a site-wide profile; set to override a specific category",
    )
    is_site_default = models.BooleanField(
        default=False,
        help_text="Use as the site-wide default when no category override matches",
    )
    template_variant = models.CharField(
        max_length=30, choices=TEMPLATE_VARIANT_CHOICES, default="default",
        help_text="Template layout variant",
    )
    theme_mode = models.CharField(
        max_length=10, choices=(("light", "Light"), ("dark", "Dark")),
        blank=True,
        help_text="Override theme mode; leave blank to inherit from Site Settings",
    )
    accent_theme = models.CharField(
        max_length=20, choices=ACCENT_THEME_CHOICES, default="inherit",
        help_text="CSS theme preset; 'inherit' uses the Site Settings theme",
    )

    # --- Design Tokens: Colors ---
    accent_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR], help_text="Override --accent (hex)")
    bg_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR], help_text="Override --bg (hex)")
    surface_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR], help_text="Override --surface (hex)")
    token_text_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR], help_text="Override --text (hex)")
    muted_text_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR], help_text="Override --text-muted (hex)")
    border_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR], help_text="Override --border (hex)")

    # --- Design Tokens: Images ---
    hero_image = models.ImageField(upload_to="profiles/hero/", blank=True, null=True, help_text="Override hero background image")
    headshot_image = models.ImageField(upload_to="profiles/headshot/", blank=True, null=True, help_text="Override headshot photo")

    # --- Design Tokens: Typography ---
    font_stack = models.CharField(max_length=10, choices=FONT_STACK_CHOICES, default="system", help_text="Font family preset")
    type_scale = models.CharField(max_length=10, choices=TYPE_SCALE_CHOICES, default="default", help_text="Type size scale")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Layout profile"
        verbose_name_plural = "Layout profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["is_site_default"],
                condition=models.Q(is_site_default=True),
                name="unique_site_default_profile",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.is_site_default:
            LayoutProfile.objects.filter(
                is_site_default=True,
            ).exclude(pk=self.pk).update(is_site_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.name
        if self.is_site_default:
            label += " [default]"
        if self.category:
            label += f" \u2192 {self.category.name}"
        return label


def resolve_active_profile(category=None):
    """Resolve the active LayoutProfile for a given context.

    Priority: category override > site default > None.
    """
    if category is not None:
        try:
            return LayoutProfile.objects.get(category=category)
        except LayoutProfile.DoesNotExist:
            pass
    return LayoutProfile.objects.filter(is_site_default=True).first()


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

