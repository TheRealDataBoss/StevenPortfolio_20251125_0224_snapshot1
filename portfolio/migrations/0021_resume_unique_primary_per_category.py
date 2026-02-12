from django.db import migrations, models


def demote_duplicate_primaries(apps, schema_editor):
    """Keep only the most-recently-updated primary per category."""
    Resume = apps.get_model("portfolio", "Resume")
    seen = set()
    for r in Resume.objects.filter(is_primary=True).order_by("-updated_at"):
        if r.category in seen:
            r.is_primary = False
            r.save(update_fields=["is_primary"])
        else:
            seen.add(r.category)


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0020_category_image"),
    ]

    operations = [
        migrations.RunPython(demote_duplicate_primaries, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="resume",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_primary=True),
                fields=("category",),
                name="unique_primary_per_category",
            ),
        ),
    ]
