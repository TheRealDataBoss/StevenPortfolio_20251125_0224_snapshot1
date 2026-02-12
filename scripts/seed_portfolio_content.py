"""
Seed script for portfolio content.

Usage:
    python manage.py shell -c "exec(open('scripts/seed_portfolio_content.py').read())"

    -- OR --

    python scripts/seed_portfolio_content.py
"""

import os
import sys
from pathlib import Path

# Django setup (no-op if already configured, e.g. via manage.py shell)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from django.core.files import File
from portfolio.models import (
    Category,
    Certification,
    EducationEntry,
    LayoutProfile,
    NavItem,
    Project,
    ProjectAttachment,
    SiteSetting,
    TEMPLATE_VARIANT_CHOICES,
)

BASE_DIR = SCRIPT_DIR / "seed_assets"


def attach_file(instance, field_name, filename):
    """Attach a file to a model's FileField/ImageField if not already set."""
    field = getattr(instance, field_name)
    if field:
        return  # already has a file, skip
    filepath = BASE_DIR / filename
    if not filepath.exists():
        print(f"  WARNING: {filepath} not found, skipping attachment.")
        return
    with open(filepath, "rb") as f:
        field.save(filename, File(f), save=True)
    print(f"  Attached {filename} -> {instance}.{field_name}")


def set_if_blank(obj, field_name, value):
    """Set field on obj only if current value is empty/None. Returns True if set."""
    current = getattr(obj, field_name, None)
    if not current:
        setattr(obj, field_name, value)
        return True
    return False


# ---------------------------------------------------------------------------
# 1. Categories
# ---------------------------------------------------------------------------
print("=" * 60)
print("SEEDING PORTFOLIO CONTENT")
print("=" * 60)

CATEGORIES = [
    "Machine Learning",
    "Applied AI",
    "Predictive Modeling",
    "Certifications",
    "Education",
]

CATEGORY_DESCRIPTIONS = {
    "Machine Learning": "Projects exploring supervised and unsupervised learning, neural networks, and production ML pipelines.",
    "Applied AI": "Real-world AI applications including NLP, computer vision, and intelligent automation.",
    "Predictive Modeling": "Statistical and ML-based predictive analytics for business optimization and forecasting.",
    "Certifications": "Professional certifications validating expertise in data science, cloud, and analytics.",
    "Education": "Academic credentials and continuing education coursework.",
}

cats = {}
for name in CATEGORIES:
    obj, created = Category.objects.get_or_create(name=name)
    cats[name] = obj
    print(f"{'Created' if created else 'Exists '} Category: {name}")
    if set_if_blank(obj, "description", CATEGORY_DESCRIPTIONS.get(name, "")):
        obj.save()
        print(f"  Enriched: {name}")


# ---------------------------------------------------------------------------
# 2. Projects
# ---------------------------------------------------------------------------
print()
PROJECTS = [
    {
        "title": "Amazon-Style Recommendation Engine",
        "slug": "amazon-style-recommendation-engine",
        "category": "Machine Learning",
        "description": (
            "Collaborative filtering + similarity modeling system inspired "
            "by Amazon's recommendation pipeline. Implements user-item and "
            "item-item similarity matrices to generate ranked product "
            "suggestions from sparse interaction data."
        ),
        "summary": "Collaborative filtering system for personalized product recommendations",
        "tech_stack": "Python, scikit-learn, NumPy, Pandas, Surprise",
        "tags": "recommendation systems, collaborative filtering, matrix factorization",
        "attachment_file": "Amazon_Recommendation_Systems.pdf",
        "notes": "Built using the Surprise library for rapid prototyping of collaborative filtering models. Evaluated with RMSE and precision@k on a held-out test set.",
        "order": 0,
    },
    {
        "title": "Making Sense of Unstructured Data",
        "slug": "making-sense-of-unstructured-data",
        "category": "Applied AI",
        "description": (
            "NLP-driven document processing and structured extraction "
            "framework for unstructured text. Combines tokenization, "
            "entity recognition, and topic modeling to convert raw "
            "documents into queryable structured records."
        ),
        "summary": "NLP pipeline for extracting structured insights from raw text",
        "tech_stack": "Python, NLTK, spaCy, Pandas, scikit-learn",
        "tags": "NLP, text mining, document processing, information extraction",
        "attachment_file": "Making_Sense_of_Unstructured_Data.pdf",
        "notes": "Pipeline processes PDF, DOCX, and plain-text inputs. Entity extraction accuracy benchmarked against a manually labeled gold-standard corpus.",
        "order": 1,
    },
    {
        "title": "Lead Scoring Model Development",
        "slug": "lead-scoring-model-development",
        "category": "Predictive Modeling",
        "description": (
            "End-to-end predictive lead scoring system using supervised ML "
            "for conversion optimization. Features engineered from CRM "
            "activity logs and demographic data feed a gradient-boosted "
            "classifier that prioritizes high-value prospects."
        ),
        "summary": "ML-powered lead scoring for sales conversion optimization",
        "tech_stack": "Python, XGBoost, Pandas, scikit-learn, Matplotlib",
        "tags": "predictive modeling, lead scoring, classification, sales analytics",
        "attachment_file": "Lead_Scoring_Model_Development.pdf",
        "notes": "Feature engineering from CRM activity logs yielded a 23% lift in AUC over the baseline logistic regression model.",
        "order": 2,
    },
]

for proj_data in PROJECTS:
    proj, created = Project.objects.get_or_create(
        slug=proj_data["slug"],
        defaults={
            "title": proj_data["title"],
            "category": cats[proj_data["category"]],
            "description": proj_data["description"],
            "summary": proj_data.get("summary", ""),
            "tech_stack": proj_data.get("tech_stack", ""),
            "tags": proj_data.get("tags", ""),
            "visible": True,
            "is_featured": True,
            "order": proj_data["order"],
        },
    )
    print(f"{'Created' if created else 'Exists '} Project: {proj.title}")
    attach_file(proj, "attachment", proj_data["attachment_file"])
    # Enrich blank text fields on existing projects
    changed = False
    for field in ("summary", "description", "tech_stack", "tags", "notes"):
        if field in proj_data:
            changed |= set_if_blank(proj, field, proj_data[field])
    if changed:
        proj.save()
        print(f"  Enriched: {proj.title}")


# ---------------------------------------------------------------------------
# 2b. ProjectAttachments — migrate legacy Project.attachment + add extras
# ---------------------------------------------------------------------------
print()
for proj_data in PROJECTS:
    proj = Project.objects.get(slug=proj_data["slug"])
    # Migrate the legacy attachment to a ProjectAttachment row
    if proj.attachment:
        att, created = ProjectAttachment.objects.get_or_create(
            project=proj,
            title=proj_data["attachment_file"].replace("_", " ").rsplit(".", 1)[0],
            defaults={"order": 0, "visible": True},
        )
        if created and not att.file:
            att.file = proj.attachment  # reuse the same file reference
            att.save()
            print(f"Created ProjectAttachment (PDF): {att.title} -> {proj.title}")
        elif created:
            print(f"Created ProjectAttachment: {att.title} -> {proj.title}")
        else:
            print(f"Exists  ProjectAttachment: {att.title} -> {proj.title}")

# Add a sample .py attachment to the first project
first_proj = Project.objects.get(slug=PROJECTS[0]["slug"])
py_att, created = ProjectAttachment.objects.get_or_create(
    project=first_proj,
    title="Helper Script",
    defaults={"order": 10, "visible": True},
)
if created:
    py_path = BASE_DIR / "sample_script.py"
    if py_path.exists():
        with open(py_path, "rb") as f:
            py_att.file.save("sample_script.py", File(f), save=True)
        print(f"Created ProjectAttachment (py): Helper Script -> {first_proj.title}")
    else:
        # Create a minimal sample .py in-memory
        from django.core.files.base import ContentFile
        py_att.file.save("sample_script.py", ContentFile(
            b'"""Sample helper script for recommendation engine."""\n\n'
            b'import numpy as np\n\n\n'
            b'def cosine_similarity(a, b):\n'
            b'    """Compute cosine similarity between two vectors."""\n'
            b'    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))\n'
        ), save=True)
        print(f"Created ProjectAttachment (py, generated): Helper Script -> {first_proj.title}")
else:
    print(f"Exists  ProjectAttachment: Helper Script -> {first_proj.title}")

# Add a sample .docx attachment to the second project
second_proj = Project.objects.get(slug=PROJECTS[1]["slug"])
docx_att, created = ProjectAttachment.objects.get_or_create(
    project=second_proj,
    title="Project Notes",
    defaults={"order": 10, "visible": True},
)
if created:
    docx_path = BASE_DIR / "project_notes.docx"
    if docx_path.exists():
        with open(docx_path, "rb") as f:
            docx_att.file.save("project_notes.docx", File(f), save=True)
        print(f"Created ProjectAttachment (docx): Project Notes -> {second_proj.title}")
    else:
        from django.core.files.base import ContentFile
        docx_att.file.save("project_notes.docx", ContentFile(b"PK\x03\x04 placeholder docx"), save=True)
        print(f"Created ProjectAttachment (docx, placeholder): Project Notes -> {second_proj.title}")
else:
    print(f"Exists  ProjectAttachment: Project Notes -> {second_proj.title}")


# ---------------------------------------------------------------------------
# 3. Certifications
# ---------------------------------------------------------------------------
print()
CERTIFICATIONS = [
    {
        "name": "IBM Data Science Certification",
        "issuer": "IBM",
        "description": (
            "Comprehensive data science methodology covering data analysis, "
            "visualization, machine learning, and applied data science "
            "capstone projects."
        ),
        "attachment_file": "IBM Data Science Certification.pdf",
        "order": 0,
    },
    {
        "name": "MIT Certificate",
        "issuer": "MIT",
        "description": (
            "Advanced analytics and machine learning techniques from the "
            "Massachusetts Institute of Technology professional education "
            "program."
        ),
        "attachment_file": "MIT Certificate.pdf",
        "order": 1,
    },
    {
        "name": "Google Analytics Certification",
        "issuer": "Google",
        "description": (
            "Proficiency in Google Analytics including data collection, "
            "processing, configuration, and reporting for digital marketing "
            "optimization."
        ),
        "attachment_file": "Google Analytics Certification.pdf",
        "order": 2,
    },
]

for cert_data in CERTIFICATIONS:
    cert, created = Certification.objects.get_or_create(
        name=cert_data["name"],
        defaults={
            "issuer": cert_data["issuer"],
            "category": cats["Certifications"],
            "description": cert_data.get("description", ""),
            "visible": True,
            "order": cert_data["order"],
        },
    )
    print(f"{'Created' if created else 'Exists '} Certification: {cert.name}")
    attach_file(cert, "attachment", cert_data["attachment_file"])
    if set_if_blank(cert, "description", cert_data.get("description", "")):
        cert.save()
        print(f"  Enriched: {cert.name}")


# ---------------------------------------------------------------------------
# 4. Education Entries
# ---------------------------------------------------------------------------
print()
EDUCATION_ENTRIES = [
    {
        "institution": "Kennesaw State University",
        "title": "B.S. \u2014 Kennesaw State University",
        "description": (
            "Bachelor\u2019s degree with honors and multiple academic society "
            "distinctions. Coursework included statistics, data structures, "
            "algorithms, and applied mathematics."
        ),
        "location": "Kennesaw, GA",
        "order": 10,
    },
    {
        "institution": "University of Alabama",
        "title": "B.S. \u2014 University of Alabama",
        "description": (
            "Undergraduate studies emphasizing analytical methods, "
            "quantitative reasoning, and foundational research techniques "
            "across the sciences and applied mathematics."
        ),
        "location": "Tuscaloosa, AL",
        "order": 20,
    },
]

for edu_data in EDUCATION_ENTRIES:
    edu, created = EducationEntry.objects.get_or_create(
        institution=edu_data["institution"],
        defaults={
            "title": edu_data["title"],
            "description": edu_data["description"],
            "location": edu_data.get("location", ""),
            "category": cats["Education"],
            "visible": True,
            "order": edu_data["order"],
        },
    )
    print(f"{'Created' if created else 'Exists '} EducationEntry: {edu.title}")
    changed = False
    for field in ("description", "location"):
        if field in edu_data:
            changed |= set_if_blank(edu, field, edu_data[field])
    if changed:
        edu.save()
        print(f"  Enriched: {edu.title}")


# ---------------------------------------------------------------------------
# 4b. Education media — placeholder images + text summaries
# ---------------------------------------------------------------------------
from django.core.files.base import ContentFile as _ContentFile
from django.conf import settings as _django_settings
from django.utils.text import slugify as _edu_slugify

_EDU_IMG_DIR = Path(_django_settings.MEDIA_ROOT) / "education" / "images"
_EDU_IMG_DIR.mkdir(parents=True, exist_ok=True)

EDUCATION_SUMMARIES = {
    "Kennesaw State University": (
        "Kennesaw State University — Academic Summary\n"
        + "=" * 50 + "\n\n"
        "Degree: Bachelor of Science\n"
        "Location: Kennesaw, GA\n\n"
        "Academic Highlights:\n"
        "- Graduated with honors and multiple academic society distinctions\n"
        "- Coursework: Statistics, Data Structures, Algorithms, Applied Mathematics\n"
        "- Senior capstone project in data analytics and predictive modeling\n"
        "- Active participation in undergraduate research programs\n"
        "- Strong foundation in quantitative analysis and scientific computing\n"
    ),
    "University of Alabama": (
        "University of Alabama — Academic Summary\n"
        + "=" * 50 + "\n\n"
        "Degree: Bachelor of Science\n"
        "Location: Tuscaloosa, AL\n\n"
        "Academic Highlights:\n"
        "- Emphasis on analytical methods and quantitative reasoning\n"
        "- Foundational research techniques across sciences and applied mathematics\n"
        "- Interdisciplinary project work combining statistics and domain expertise\n"
        "- Collaborative research in applied data analysis methodologies\n"
        "- Coursework in probability, linear algebra, and scientific programming\n"
    ),
}

print()
for edu in EducationEntry.objects.all():
    slug = _edu_slugify(edu.institution)

    # Image: attach placeholder if blank
    if not edu.image:
        img_rel = f"education/images/{slug}_placeholder.png"
        img_abs = Path(_django_settings.MEDIA_ROOT) / img_rel
        if img_abs.exists():
            # File already on disk (from generator), just assign DB path
            edu.image = img_rel
            edu.save(update_fields=["image"])
            print(f"  Attached placeholder image: {edu.institution}")
        else:
            # Generate minimal gradient placeholder with Pillow
            try:
                from PIL import Image as _PImg, ImageDraw as _PDraw
                import io as _io
                _w, _h = 600, 400
                _img = _PImg.new("RGB", (_w, _h))
                _draw = _PDraw.Draw(_img)
                _palette_idx = hash(slug) % 6
                _tops = [(13,27,56),(20,60,90),(50,20,70),(15,50,40),(80,30,20),(30,30,50)]
                _bots = [(44,62,80),(40,100,130),(90,50,120),(40,90,70),(130,60,40),(70,70,100)]
                _top, _bot = _tops[_palette_idx], _bots[_palette_idx]
                for _y in range(_h):
                    _t = _y / max(_h - 1, 1)
                    _draw.line([(0, _y), (_w - 1, _y)], fill=(
                        int(_top[0] + (_bot[0] - _top[0]) * _t),
                        int(_top[1] + (_bot[1] - _top[1]) * _t),
                        int(_top[2] + (_bot[2] - _top[2]) * _t),
                    ))
                _buf = _io.BytesIO()
                _img.save(_buf, "PNG", optimize=True)
                edu.image.save(f"{slug}_placeholder.png", _ContentFile(_buf.getvalue()), save=True)
                print(f"  Generated + attached image: {edu.institution}")
            except ImportError:
                print(f"  WARNING: Pillow not available, skipping image for {edu.institution}")

    # Attachment: create text summary if blank
    if not edu.attachment:
        text = EDUCATION_SUMMARIES.get(
            edu.institution,
            f"{edu.institution} — Academic Summary\n"
            + "=" * 50 + "\n\nDegree program details.\n",
        )
        filename = f"{slug}_summary.txt"
        edu.attachment.save(filename, _ContentFile(text.encode("utf-8")), save=True)
        print(f"  Attached text summary: {edu.institution}")


# ---------------------------------------------------------------------------
# 5. SiteSetting
# ---------------------------------------------------------------------------
print()
BIO_LONG = (
    "I am a data scientist and machine learning engineer with a deep "
    "passion for transforming complex datasets into actionable business "
    "intelligence. My work spans the full ML lifecycle — from exploratory "
    "analysis and feature engineering through model development, validation, "
    "and production deployment.\n\n"
    "Throughout my career I have designed and delivered predictive modeling "
    "systems, recommendation engines, and NLP pipelines that drive measurable "
    "impact. I specialize in Python-based ML stacks including scikit-learn, "
    "TensorFlow, and XGBoost, and I am comfortable working across cloud "
    "platforms and containerized environments.\n\n"
    "I hold a Bachelor of Science from Kennesaw State University where I "
    "graduated with honors. I complement my technical expertise with strong "
    "communication skills, regularly translating complex analytical findings "
    "into clear narratives for stakeholders at every level.\n\n"
    "When I am not building models, I enjoy contributing to the data science "
    "community, exploring emerging AI research, and continuously expanding my "
    "skill set through professional certifications and hands-on experimentation."
)

SITE_DEFAULTS = {
    "full_name": "Steven Wazlavek",
    "headline": "Data Scientist | Machine Learning | Applied AI",
    "bio_short": "Data scientist building production-ready machine learning systems.",
    "bio_long": BIO_LONG,
    "hero_label": "Personal Site",
    "hero_title": "Data Science & Machine Learning Portfolio",
    "hero_roles": "Data Analyst | Data Scientist | Business Intelligence",
    "hero_subtitle": "Building intelligent systems that transform data into decisions",
    "about_body": BIO_LONG,
    "homepage_featured_projects_count": 3,
}

site, created = SiteSetting.objects.get_or_create(
    pk=1,
    defaults=SITE_DEFAULTS,
)

if created:
    print("Created SiteSetting")
else:
    changed = False
    for field, value in SITE_DEFAULTS.items():
        changed |= set_if_blank(site, field, value)
    if changed:
        site.save()
        print("  Filled blank SiteSetting fields")
    else:
        print("Exists  SiteSetting (no blanks to fill)")

attach_file(site, "hero_image", "hero image.jpg")
attach_file(site, "headshot", "Personal_Image.jpg")


# ---------------------------------------------------------------------------
# 6. Navigation Items
# ---------------------------------------------------------------------------
print()

# Read social URLs from SiteSetting for external nav links
_site = SiteSetting.objects.first()
_github_url = (_site.github_url if _site and _site.github_url else "https://github.com")
_linkedin_url = (_site.linkedin_url if _site and _site.linkedin_url else "https://linkedin.com")

TOP_LEVEL_NAV = [
    {"title": "Home", "url": "/", "order": 1, "icon": "fas fa-home"},
    {"title": "Portfolio", "url": "#", "order": 2, "icon": "fas fa-folder-open"},
    {"title": "Projects", "url": "/projects/", "order": 3, "icon": "fas fa-briefcase"},
    {"title": "Education", "url": "/education/", "order": 4, "icon": "fas fa-graduation-cap"},
    {"title": "Certifications", "url": "/certifications/", "order": 5, "icon": "fas fa-certificate"},
    {"title": "GitHub", "url": _github_url, "order": 6, "icon": "fab fa-github", "external": True, "new_tab": True},
    {"title": "LinkedIn", "url": _linkedin_url, "order": 7, "icon": "fab fa-linkedin", "external": True, "new_tab": True},
    {"title": "About", "url": "/about/", "order": 50, "icon": "fas fa-user"},
    {"title": "Contact", "url": "/contact/", "order": 60, "icon": "fas fa-envelope"},
]

PORTFOLIO_CHILDREN_NAV = [
    {"title": "Projects", "url": "/projects/", "order": 10, "icon": "fas fa-briefcase"},
    {"title": "Resume", "url": "/resume/", "order": 20, "icon": "fas fa-file-alt"},
    {"title": "Education", "url": "/education/", "order": 30, "icon": "fas fa-graduation-cap"},
    {"title": "Certifications", "url": "/certifications/", "order": 40, "icon": "fas fa-certificate"},
    {"title": "GitHub", "url": _github_url, "order": 50, "icon": "fab fa-github", "external": True, "new_tab": True},
    {"title": "LinkedIn", "url": _linkedin_url, "order": 60, "icon": "fab fa-linkedin", "external": True, "new_tab": True},
]

# Remove top-level items that are dropdown-only (NOT also top-level)
DROPDOWN_ONLY_TITLES = {"Resume"}
removed = NavItem.objects.filter(parent=None, title__in=DROPDOWN_ONLY_TITLES).delete()[0]
if removed:
    print(f"  Removed {removed} duplicated top-level NavItem(s)")

# Upsert top-level items
for item_data in TOP_LEVEL_NAV:
    nav, created = NavItem.objects.update_or_create(
        title=item_data["title"],
        parent=None,
        defaults={
            "url": item_data["url"],
            "order": item_data["order"],
            "icon": item_data.get("icon", ""),
            "visible": True,
            "external": item_data.get("external", False),
            "new_tab": item_data.get("new_tab", False),
        },
    )
    print(f"{'Created' if created else 'Exists '} NavItem (top): {nav.title}")

# Upsert Portfolio dropdown children
portfolio_nav = NavItem.objects.get(title="Portfolio", parent=None)
for child_data in PORTFOLIO_CHILDREN_NAV:
    nav, created = NavItem.objects.update_or_create(
        title=child_data["title"],
        parent=portfolio_nav,
        defaults={
            "url": child_data["url"],
            "order": child_data["order"],
            "icon": child_data.get("icon", ""),
            "visible": True,
            "external": child_data.get("external", False),
            "new_tab": child_data.get("new_tab", False),
        },
    )
    print(f"{'Created' if created else 'Exists '} NavItem (child): {nav.title}")


# ---------------------------------------------------------------------------
# 7. Layout Profiles — one per template variant
# ---------------------------------------------------------------------------
print()

LAYOUT_PROFILE_TOKENS = {
    "default": {
        "accent_color": "#0d6efd",
        "bg_color": "#f8fafc",
        "surface_color": "#ffffff",
        "token_text_color": "#0f172a",
        "muted_text_color": "#64748b",
        "border_color": "#e2e8f0",
        "font_stack": "system",
        "type_scale": "default",
    },
    "modern_saas": {
        "accent_color": "#6366f1",
        "bg_color": "#f8fafc",
        "surface_color": "#ffffff",
        "token_text_color": "#1e293b",
        "muted_text_color": "#64748b",
        "border_color": "#e2e8f0",
        "font_stack": "sans",
        "type_scale": "default",
    },
    "executive_minimal": {
        "accent_color": "#1a1a1a",
        "bg_color": "#ffffff",
        "surface_color": "#fafafa",
        "token_text_color": "#1a1a1a",
        "muted_text_color": "#555555",
        "border_color": "#e5e5e5",
        "font_stack": "system",
        "type_scale": "spacious",
    },
    "data_lab": {
        "accent_color": "#38bdf8",
        "bg_color": "#0f172a",
        "surface_color": "#1e293b",
        "token_text_color": "#e2e8f0",
        "muted_text_color": "#94a3b8",
        "border_color": "#334155",
        "font_stack": "system",
        "type_scale": "default",
    },
    "split_screen": {
        "accent_color": "#f97316",
        "bg_color": "#fffbeb",
        "surface_color": "#ffffff",
        "token_text_color": "#292524",
        "muted_text_color": "#78716c",
        "border_color": "#e7e5e4",
        "font_stack": "sans",
        "type_scale": "default",
    },
    "magazine_editorial": {
        "accent_color": "#b91c1c",
        "bg_color": "#fef2f2",
        "surface_color": "#ffffff",
        "token_text_color": "#1c1917",
        "muted_text_color": "#57534e",
        "border_color": "#d6d3d1",
        "font_stack": "serif",
        "type_scale": "spacious",
    },
    "card_dashboard": {
        "accent_color": "#14b8a6",
        "bg_color": "#f0fdfa",
        "surface_color": "#ffffff",
        "token_text_color": "#134e4a",
        "muted_text_color": "#5eead4",
        "border_color": "#99f6e4",
        "font_stack": "sans",
        "type_scale": "compact",
    },
    "glass_modern": {
        "accent_color": "#a78bfa",
        "bg_color": "#0c0a1a",
        "surface_color": "#1a1530",
        "token_text_color": "#e8e0ff",
        "muted_text_color": "#a599c8",
        "border_color": "#2d2550",
        "font_stack": "sans",
        "type_scale": "default",
    },
    "bold_branding": {
        "accent_color": "#e11d48",
        "bg_color": "#fff1f2",
        "surface_color": "#ffffff",
        "token_text_color": "#1c1917",
        "muted_text_color": "#6b7280",
        "border_color": "#fecdd3",
        "font_stack": "sans",
        "type_scale": "spacious",
    },
    "timeline_pro": {
        "accent_color": "#2563eb",
        "bg_color": "#eff6ff",
        "surface_color": "#ffffff",
        "token_text_color": "#1e3a5f",
        "muted_text_color": "#6b7280",
        "border_color": "#bfdbfe",
        "font_stack": "system",
        "type_scale": "default",
    },
    "technical_research": {
        "accent_color": "#059669",
        "bg_color": "#f0fdf4",
        "surface_color": "#ffffff",
        "token_text_color": "#14532d",
        "muted_text_color": "#6b7280",
        "border_color": "#bbf7d0",
        "font_stack": "serif",
        "type_scale": "compact",
    },
}

for variant_slug, variant_label in TEMPLATE_VARIANT_CHOICES:
    profile_slug = f"variant-{variant_slug}"
    profile_name = f"Variant \u2014 {variant_label}"
    tokens = LAYOUT_PROFILE_TOKENS.get(variant_slug, {})

    defaults = {
        "name": profile_name,
        "template_variant": variant_slug,
        "is_site_default": (variant_slug == "default"),
        **tokens,
    }

    profile, created = LayoutProfile.objects.get_or_create(
        slug=profile_slug,
        defaults=defaults,
    )

    if created:
        print(f"Created LayoutProfile: {profile_name}")
    else:
        # Update token fields only where the existing value is blank
        changed = False
        for field, value in tokens.items():
            changed |= set_if_blank(profile, field, value)
        # Always keep template_variant in sync
        if profile.template_variant != variant_slug:
            profile.template_variant = variant_slug
            changed = True
        if changed:
            profile.save()
            print(f"Updated LayoutProfile: {profile_name}")
        else:
            print(f"Exists  LayoutProfile: {profile_name}")


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("SEED COMPLETE")
print(f"  Categories:         {Category.objects.count()}")
print(f"  Projects:           {Project.objects.count()}")
print(f"  ProjectAttachments: {ProjectAttachment.objects.count()}")
print(f"  Certifications:     {Certification.objects.count()}")
print(f"  Education:          {EducationEntry.objects.count()}")
print(f"  NavItems:           {NavItem.objects.count()}")
print(f"  LayoutProfiles:     {LayoutProfile.objects.count()}")
print(f"  SiteSetting:        {'YES' if SiteSetting.objects.exists() else 'NO'}")
print("=" * 60)
