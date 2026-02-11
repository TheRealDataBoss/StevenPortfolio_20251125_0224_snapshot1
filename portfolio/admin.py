from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import Category, ContactMessage, NavItem, Project, Resume, SiteSetting


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
        ("Personal Info", {"fields": ("full_name", "headline", "bio_short", "bio_long", "headshot")}),
        ("Social Links", {"fields": ("linkedin_url", "github_url")}),
        ("Hero", {"fields": ("hero_title", "hero_subtitle", "hero_image")}),
        ("About", {"fields": ("about_title", "about_body")}),
        ("Resume", {"fields": ("resume_file",)}),
        ("Media Defaults", {
            "fields": (("default_image_ratio", "default_image_fit"),),
        }),
        ("Theme", {
            "fields": (
                ("theme", "motion_enabled"),
                ("primary_color", "button_text_color"),
                ("nav_bg_color", "nav_text_color"),
                ("hero_start_color", "hero_end_color", "hero_text_color"),
                ("footer_bg_color", "footer_text_color"),
                ("page_bg_color", "text_color"),
            )
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
# 3. Projects
# ---------------------------------------------------------------------------

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "visible", "order", "created_at")
    list_editable = ("visible", "order")
    list_filter = ("category", "is_featured", "visible", "created_at")
    search_fields = ("title", "summary", "description", "tags", "tech_stack")
    readonly_fields = ("created_at", "updated_at", "thumbnail")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Basics", {"fields": ("title", "slug", "category", "summary", "description", "tags", "tech_stack")}),
        ("Links", {"fields": ("repo_url", "live_url")}),
        ("Media", {"fields": ("image", "attachment", "thumbnail")}),
        ("Meta", {"fields": ("is_featured", "visible", "order", "created_at", "updated_at")}),
    )

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;border-radius:6px;">', obj.image.url)
        return ""
    thumbnail.short_description = "Preview"


# ---------------------------------------------------------------------------
# 4. Resumes
# ---------------------------------------------------------------------------

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_primary", "has_preview", "has_alternate", "updated_at")
    list_filter = ("category", "is_primary")
    search_fields = ("title", "category")
    ordering = ("-updated_at",)
    fieldsets = (
        (None, {"fields": ("title", "category", "is_primary")}),
        ("Files", {"fields": ("file", "preview_pdf", "alternate_file")}),
    )

    def has_preview(self, obj):
        return bool(obj.preview_pdf)
    has_preview.boolean = True
    has_preview.short_description = "PDF Preview"

    def has_alternate(self, obj):
        return bool(obj.alternate_file)
    has_alternate.boolean = True
    has_alternate.short_description = "Alt File"


# ---------------------------------------------------------------------------
# 5. Contact Messages
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
# 6. Categories
# ---------------------------------------------------------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    list_filter = ("name",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
