from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import Category, Certification, ContactMessage, EducationEntry, ImageVariant, LayoutProfile, NavItem, Project, ProjectAttachment, Resume, SiteSetting

# Shared form for LayoutProfile color pickers
class LayoutProfileForm(forms.ModelForm):
    class Meta:
        model = LayoutProfile
        fields = "__all__"
        widgets = {
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "bg_color": forms.TextInput(attrs={"type": "color"}),
            "surface_color": forms.TextInput(attrs={"type": "color"}),
            "token_text_color": forms.TextInput(attrs={"type": "color"}),
            "muted_text_color": forms.TextInput(attrs={"type": "color"}),
            "border_color": forms.TextInput(attrs={"type": "color"}),
        }


# ---------------------------------------------------------------------------
# 1. Site Settings (singleton)
# ---------------------------------------------------------------------------

class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = "__all__"
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color"}),
            "button_text_color": forms.TextInput(attrs={"type": "color"}),
            "nav_bg_color": forms.TextInput(attrs={"type": "color"}),
            "nav_text_color": forms.TextInput(attrs={"type": "color"}),
            "hero_start_color": forms.TextInput(attrs={"type": "color"}),
            "hero_end_color": forms.TextInput(attrs={"type": "color"}),
            "hero_text_color": forms.TextInput(attrs={"type": "color"}),
            "footer_bg_color": forms.TextInput(attrs={"type": "color"}),
            "footer_text_color": forms.TextInput(attrs={"type": "color"}),
            "page_bg_color": forms.TextInput(attrs={"type": "color"}),
            "text_color": forms.TextInput(attrs={"type": "color"}),
        }


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    form = SiteSettingForm
    list_display = ("full_name", "headline", "theme", "primary_color_display")
    fieldsets = (
        ("Hero Identity", {
            "fields": ("hero_label", "hero_title", "hero_roles", "hero_subtitle", "hero_image"),
            "description": "Controls the homepage hero block: label, name, roles, tagline, and image.",
        }),
        ("Personal Info", {
            "fields": ("full_name", "headline", "bio_short", "bio_long", "headshot"),
        }),
        ("Social Links", {"fields": ("linkedin_url", "github_url")}),
        ("About", {
            "fields": ("about_title", "about_body"),
            "classes": ("collapse",),
        }),
        ("Resume", {"fields": ("resume_file",)}),
        ("Homepage", {
            "fields": ("homepage_featured_projects_count", "homepage_featured_category_blocks_count"),
            "classes": ("collapse",),
        }),
        ("Media Defaults", {
            "fields": (("default_image_ratio", "default_image_fit"),),
            "classes": ("collapse",),
        }),
        ("Theme & Colors", {
            "fields": (
                ("theme", "motion_enabled"),
                ("primary_color", "button_text_color"),
                ("nav_bg_color", "nav_text_color"),
                ("hero_start_color", "hero_end_color", "hero_text_color"),
                ("footer_bg_color", "footer_text_color"),
                ("page_bg_color", "text_color"),
            ),
            "classes": ("collapse",),
        }),
    )

    def primary_color_display(self, obj):
        return format_html(
            '<div style="width:40px;height:20px;border:1px solid #ccc;background:{}"></div>',
            obj.primary_color,
        )
    primary_color_display.short_description = "Primary"

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSetting.objects.first()
        if obj:
            return redirect("admin:portfolio_sitesetting_change", obj.pk)
        return super().changelist_view(request, extra_context=extra_context)


# ---------------------------------------------------------------------------
# 2. Navigation Items
# ---------------------------------------------------------------------------

@admin.register(NavItem)
class NavItemAdmin(admin.ModelAdmin):
    list_display = ("title", "parent", "url", "order", "visible", "new_tab", "login_required", "primary_groups")
    list_editable = ("order", "visible")
    list_filter = ("visible", "new_tab", "login_required", "parent")
    search_fields = ("title", "url")
    ordering = ("order",)
    fieldsets = (
        (None, {"fields": ("title", "url", "parent", "order", "icon")}),
        ("Behavior", {"fields": ("visible", "external", "new_tab", "login_required", "allowed_groups")}),
    )
    filter_horizontal = ("allowed_groups",)

    def primary_groups(self, obj):
        return ", ".join(g.name for g in obj.allowed_groups.all())
    primary_groups.short_description = "Allowed groups"


# ---------------------------------------------------------------------------
# 3. Image Variants
# ---------------------------------------------------------------------------

@admin.register(ImageVariant)
class ImageVariantAdmin(admin.ModelAdmin):
    list_display = ("name", "aspect_ratio", "crop_mode", "shape", "allow_zoom", "order")
    list_editable = ("order",)
    ordering = ("order", "name")
    fieldsets = (
        (None, {"fields": ("name", "aspect_ratio", ("width", "height"), "order")}),
        ("Crop & Fit", {
            "fields": ("crop_mode", "object_position", "background_color"),
            "description": "COVER crops to fill the container. CONTAIN fits the full image with possible letterboxing. object_position controls crop focus (e.g. '50% 20%' shifts focus upward).",
        }),
        ("Shape", {
            "fields": ("shape", "border_radius"),
            "description": "RECT = sharp corners. ROUNDED = custom radius. CIRCLE = fully round (forces 1:1 aspect ratio).",
        }),
        ("Behavior", {"fields": ("allow_zoom",)}),
    )


# ---------------------------------------------------------------------------
# 4. Layout Profiles
# ---------------------------------------------------------------------------

@admin.register(LayoutProfile)
class LayoutProfileAdmin(admin.ModelAdmin):
    form = LayoutProfileForm
    list_display = (
        "name", "slug", "scope_display", "category", "is_site_default",
        "template_variant", "theme_mode", "accent_theme", "preview_link", "updated_at",
    )
    list_editable = ("is_site_default",)
    list_filter = ("category", "template_variant", "theme_mode", "accent_theme", "is_site_default")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-is_site_default", "category", "name")
    readonly_fields = ("hero_image_preview", "headshot_image_preview")
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "is_site_default")}),
        ("Layout", {"fields": ("template_variant", "theme_mode", "accent_theme")}),
        ("Design Tokens — Colors", {
            "fields": (
                ("accent_color", "bg_color"),
                ("surface_color", "token_text_color"),
                ("muted_text_color", "border_color"),
            ),
            "classes": ("collapse",),
            "description": "Optional hex overrides. Leave blank to inherit from Site Settings.",
        }),
        ("Design Tokens — Images", {
            "fields": ("hero_image", "hero_image_preview", "headshot_image", "headshot_image_preview"),
            "classes": ("collapse",),
            "description": "Optional image overrides. Leave blank to inherit from Site Settings.",
        }),
        ("Design Tokens — Typography", {
            "fields": (("font_stack", "type_scale"),),
            "classes": ("collapse",),
        }),
    )
    actions = ["make_site_default", "activate_and_make_site_default"]

    def hero_image_preview(self, obj):
        if obj.hero_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px;">', obj.hero_image.url)
        return "No image"
    hero_image_preview.short_description = "Hero preview"

    def headshot_image_preview(self, obj):
        if obj.headshot_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:6px;">', obj.headshot_image.url)
        return "No image"
    headshot_image_preview.short_description = "Headshot preview"

    def preview_link(self, obj):
        return format_html('<a href="/?profile={}" target="_blank">Preview</a>', obj.slug)
    preview_link.short_description = "Preview"

    def scope_display(self, obj):
        if obj.category:
            return format_html("Category: {}", obj.category.name)
        if obj.is_site_default:
            return format_html('<strong style="color:#198754;">Site Default</strong>')
        return "Inactive Site Profile"
    scope_display.short_description = "Scope"

    @admin.action(description="Set as site-wide default profile")
    def make_site_default(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one profile.", level="error")
            return
        profile = queryset.first()
        LayoutProfile.objects.filter(is_site_default=True).exclude(pk=profile.pk).update(is_site_default=False)
        profile.is_site_default = True
        profile.save(update_fields=["is_site_default"])
        self.message_user(request, f'"{profile.name}" is now the site-wide default.')

    @admin.action(description="Activate and make site default")
    def activate_and_make_site_default(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one profile.", level="error")
            return
        profile = queryset.first()
        LayoutProfile.objects.filter(is_site_default=True).exclude(pk=profile.pk).update(is_site_default=False)
        profile.is_site_default = True
        profile.save(update_fields=["is_site_default"])
        self.message_user(request, f'"{profile.name}" is now active as the site-wide default.')


# ---------------------------------------------------------------------------
# 5. Projects
# ---------------------------------------------------------------------------

class ProjectAttachmentInline(admin.TabularInline):
    model = ProjectAttachment
    extra = 0
    fields = ("title", "file", "external_url", "visible", "order")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "visible", "order", "created_at")
    list_editable = ("visible", "order")
    list_filter = ("category", "is_featured", "visible", "created_at")
    search_fields = ("title", "summary", "description", "tags", "tech_stack")
    readonly_fields = ("created_at", "updated_at", "thumbnail")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProjectAttachmentInline]
    fieldsets = (
        ("Basics", {"fields": ("title", "slug", "category", "summary", "description", "tags", "tech_stack")}),
        ("Project Notes", {
            "fields": ("notes",),
            "description": "Freeform notes displayed on the project detail page. Supports paragraphs and line breaks.",
        }),
        ("Links", {"fields": ("repo_url", "live_url")}),
        ("Media", {"fields": ("image", "image_variant", "thumbnail")}),
        ("Legacy Attachment (deprecated)", {
            "classes": ("collapse",),
            "fields": ("attachment",),
            "description": "Use the Attachments inline below instead. This field is retained for backward compatibility.",
        }),
        ("Meta", {"fields": ("is_featured", "visible", "order", "created_at", "updated_at")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "notes":
            kwargs["widget"] = forms.Textarea(attrs={"rows": 12, "style": "width:100%;"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;border-radius:6px;">', obj.image.url)
        return ""
    thumbnail.short_description = "Preview"


@admin.register(ProjectAttachment)
class ProjectAttachmentAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "file_name_display", "kind", "visible", "order")
    list_filter = ("visible",)
    list_editable = ("visible", "order")
    search_fields = ("title", "project__title", "file")
    ordering = ("project", "order")

    def file_name_display(self, obj):
        if obj.file and obj.file.name:
            return obj.file.name.split("/")[-1]
        return "-"
    file_name_display.short_description = "File"

    def kind(self, obj):
        return obj.preview_kind
    kind.short_description = "Type"


# ---------------------------------------------------------------------------
# 6. Resumes
# ---------------------------------------------------------------------------

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "primary_badge", "has_preview", "has_alternate", "updated_at")
    list_filter = ("category", "is_primary")
    search_fields = ("title", "category")
    ordering = ("-updated_at",)
    fieldsets = (
        (None, {"fields": ("title", "category", "is_primary")}),
        ("Files", {"fields": ("file", "preview_pdf", "alternate_file")}),
    )

    def primary_badge(self, obj):
        if obj.is_primary:
            return format_html(
                '<span style="background:#198754;color:#fff;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">PRIMARY</span>'
            )
        return ""
    primary_badge.short_description = "Status"

    def has_preview(self, obj):
        return bool(obj.preview_pdf)
    has_preview.boolean = True
    has_preview.short_description = "PDF Preview"

    def has_alternate(self, obj):
        return bool(obj.alternate_file)
    has_alternate.boolean = True
    has_alternate.short_description = "Alt File"


# ---------------------------------------------------------------------------
# 7. Contact Messages
# ---------------------------------------------------------------------------

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "created_at")

    def has_add_permission(self, request):
        return False


# ---------------------------------------------------------------------------
# 8. Categories
# ---------------------------------------------------------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "thumbnail", "description")
    list_filter = ("name",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("image_preview",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description")}),
        ("Image", {"fields": ("image", "image_preview")}),
    )

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:32px;border-radius:4px;">', obj.image.url)
        return format_html('<span style="color:#999;">—</span>')
    thumbnail.short_description = "Image"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:160px;border-radius:8px;">', obj.image.url)
        return "No image uploaded"
    image_preview.short_description = "Preview"


# ---------------------------------------------------------------------------
# 9. Education
# ---------------------------------------------------------------------------

@admin.register(EducationEntry)
class EducationEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "institution", "category", "start_date", "end_date", "visible", "order")
    list_editable = ("visible", "order")
    list_filter = ("visible", "institution", "category")
    search_fields = ("title", "institution", "description")
    ordering = ("order", "id")
    fieldsets = (
        (None, {"fields": ("title", "institution", "category", "location", "url")}),
        ("Dates", {"fields": (("start_date", "end_date"),)}),
        ("Content", {"fields": ("description", "image", "attachment")}),
        ("Display", {"fields": (("visible", "order"),)}),
    )


# ---------------------------------------------------------------------------
# 10. Certifications
# ---------------------------------------------------------------------------

@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer", "category", "issue_date", "expires_date", "visible", "order")
    list_editable = ("visible", "order")
    list_filter = ("visible", "issuer", "category")
    search_fields = ("name", "issuer", "description")
    ordering = ("order", "id")
    fieldsets = (
        (None, {"fields": ("name", "issuer", "category", "credential_id", "credential_url")}),
        ("Dates", {"fields": (("issue_date", "expires_date"),)}),
        ("Content", {"fields": ("description", "image", "attachment")}),
        ("Display", {"fields": (("visible", "order"),)}),
    )
