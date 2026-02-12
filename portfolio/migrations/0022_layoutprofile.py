from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0021_resume_unique_primary_per_category"),
    ]

    operations = [
        migrations.CreateModel(
            name="LayoutProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                ("is_site_default", models.BooleanField(default=False, help_text="Use as the site-wide default when no category override matches")),
                ("template_variant", models.CharField(choices=[("default", "Default"), ("modern_saas", "Modern SaaS")], default="default", help_text="Template layout variant", max_length=30)),
                ("theme_mode", models.CharField(blank=True, choices=[("light", "Light"), ("dark", "Dark")], help_text="Override theme mode; leave blank to inherit from Site Settings", max_length=10)),
                ("accent_theme", models.CharField(choices=[("inherit", "Inherit from Site Settings"), ("light", "Light"), ("dark", "Dark"), ("blue", "Blue"), ("green", "Green"), ("purple", "Purple")], default="inherit", help_text="CSS theme preset; 'inherit' uses the Site Settings theme", max_length=20)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.OneToOneField(blank=True, help_text="Leave blank for a site-wide profile; set to override a specific category", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="layout_profile", to="portfolio.category")),
            ],
            options={
                "verbose_name": "Layout profile",
                "verbose_name_plural": "Layout profiles",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="layoutprofile",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_site_default=True),
                fields=("is_site_default",),
                name="unique_site_default_profile",
            ),
        ),
    ]
