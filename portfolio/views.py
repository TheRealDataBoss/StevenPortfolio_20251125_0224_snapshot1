from collections import OrderedDict
from html import escape
import json

from django.conf import settings as django_settings
from django.contrib import messages
from django.db.models import Q
import mimetypes
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView, ListView, DetailView

from .forms import ContactForm
from .mixins import ThemeTemplateMixin
from .models import Category, Certification, EducationEntry, LayoutProfile, Project, ProjectAttachment, Resume, SiteSetting, TEMPLATE_VARIANT_CHOICES


def _is_pdf(field):
    return field and field.name and field.name.lower().endswith(".pdf")


def _file_ext(field):
    """Return lowercase file extension from a FileField, or empty string."""
    if field and field.name and "." in field.name:
        return field.name.rsplit(".", 1)[-1].lower()
    return ""


_TEXT_EXTS = {
    "py", "js", "ts", "json", "md", "txt", "csv", "yml", "yaml",
    "toml", "cfg", "ini", "html", "css", "xml", "sql",
    "sh", "bat", "ps1", "r", "rb", "go", "rs", "java", "c", "cpp", "h",
}

# Extensions hidden from public project-detail attachment list
_ATTACHMENT_DENY_EXTS = {
    "py", "txt", "md", "ps1", "sh", "js", "ts", "json", "yaml", "yml", "csv",
}
_ATTACHMENT_DENY_TITLES = {"helper script", "project notes"}
_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"}
_AUDIO_EXTS = {"mp3", "wav", "ogg", "flac", "m4a"}
_VIDEO_EXTS = {"mp4", "webm", "ogv", "mov"}


def _preview_kind_for_ext(ext):
    """Return preview kind string for a file extension."""
    if ext == "pdf":
        return "pdf"
    if ext == "ipynb":
        return "notebook"
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _TEXT_EXTS:
        return "text"
    if ext in _AUDIO_EXTS:
        return "audio"
    if ext in _VIDEO_EXTS:
        return "video"
    return "none"


def _is_docx(field):
    return field and field.name and field.name.lower().endswith(".docx")


def _find_pdf(resume):
    """Return the best PDF FileField from a Resume, or None."""
    if resume.preview_pdf:
        return resume.preview_pdf
    if _is_pdf(resume.file):
        return resume.file
    if _is_pdf(resume.alternate_file):
        return resume.alternate_file
    return None


@xframe_options_sameorigin
def resume_pdf_inline(request):
    resume = Resume.objects.filter(is_primary=True).order_by("-updated_at", "-id").first()
    if not resume:
        raise Http404
    pdf_file = _find_pdf(resume)
    if not pdf_file:
        raise Http404
    response = FileResponse(pdf_file.open(), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="Steven_Wazlavek_Resume.pdf"'
    return response


class HomeView(ThemeTemplateMixin, TemplateView):
    template_name = "portfolio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SiteSetting.objects.first()
        context["settings"] = settings
        count = settings.homepage_featured_projects_count if settings else 3
        featured_qs = (
            Project.objects.select_related("category")
            .filter(visible=True, is_featured=True)
            .order_by("order", "-created_at")[:count]
        )
        featured_list = list(featured_qs)
        context["featured_projects"] = featured_list
        all_groups = _group_by_category(featured_list)
        blocks = settings.homepage_featured_category_blocks_count if settings else 3
        context["featured_project_groups"] = all_groups[:blocks]
        context["recent_projects"] = Project.objects.filter(visible=True).order_by("-created_at")[:6]
        context["categories"] = Category.objects.all()
        return context


class ProjectListView(ThemeTemplateMixin, ListView):
    model = Project
    template_name = "portfolio/project_list.html"
    context_object_name = "projects"
    paginate_by = 9

    def get_queryset(self):
        qs = Project.objects.select_related("category").filter(visible=True)
        cat = self.request.GET.get("category")
        q = self.request.GET.get("q")
        if cat:
            qs = qs.filter(category__slug=cat)
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(tags__icontains=q)
                | Q(category__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.all()
        ctx["current_category"] = self.request.GET.get("category")
        ctx["search_term"] = self.request.GET.get("q", "")
        return ctx


class ProjectDetailView(ThemeTemplateMixin, DetailView):
    model = Project
    slug_field = "slug"
    template_name = "portfolio/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["related"] = (
            Project.objects.filter(category=self.object.category, visible=True)
            .exclude(pk=self.object.pk)
            .order_by("-created_at")[:3]
        )
        # Filter attachments for public display (deny-list by title + extension)
        project = self.object
        visible_attachments = []
        for att in project.attachments.filter(visible=True).order_by("order"):
            if att.title.strip().lower() in _ATTACHMENT_DENY_TITLES:
                continue
            if _file_ext(att.file) in _ATTACHMENT_DENY_EXTS:
                continue
            visible_attachments.append(att)
        ctx["visible_attachments"] = visible_attachments

        # Legacy attachment preview info
        if project.attachment:
            ext = _file_ext(project.attachment)
            ctx["legacy_preview_kind"] = _preview_kind_for_ext(ext)
        return ctx


class AboutView(ThemeTemplateMixin, TemplateView):
    template_name = "portfolio/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["settings"] = SiteSetting.objects.first()
        return ctx


class ResumeViewerView(TemplateView):
    """Standalone PDF.js viewer page, embedded via iframe on /resume/."""
    template_name = "portfolio/resume_viewer.html"

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return xframe_options_sameorigin(view)


class ResumeView(ThemeTemplateMixin, TemplateView):
    template_name = "portfolio/resume.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["latest_resume"] = Resume.objects.first()
        ctx["resume_entries"] = Resume.objects.all()

        resume = ctx.get("primary_resume")  # from context processor
        if not resume:
            resume = Resume.objects.filter(is_primary=True).order_by("-updated_at", "-id").first()

        has_pdf = False
        download_primary_url = None
        download_pdf_url = None

        if resume:
            # Best DOCX for download
            if _is_docx(resume.file):
                download_primary_url = resume.file.url
            elif _is_docx(resume.alternate_file):
                download_primary_url = resume.alternate_file.url
            elif resume.file:
                download_primary_url = resume.file.url

            # Best PDF for preview and download
            pdf_field = _find_pdf(resume)
            if pdf_field:
                has_pdf = True
                download_pdf_url = pdf_field.url

        ctx["has_pdf"] = has_pdf
        ctx["download_primary_url"] = download_primary_url
        ctx["download_pdf_url"] = download_pdf_url
        return ctx


@xframe_options_sameorigin
def education_pdf_inline(request, pk):
    """Serve an EducationEntry PDF attachment inline."""
    entry = EducationEntry.objects.filter(pk=pk).first()
    if not entry or not _is_pdf(entry.attachment):
        raise Http404
    response = FileResponse(entry.attachment.open(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{entry.attachment.name.split("/")[-1]}"'
    return response


@xframe_options_sameorigin
def education_inline(request, pk):
    """Serve an EducationEntry attachment inline (PDF, image, or text)."""
    entry = EducationEntry.objects.filter(pk=pk).first()
    if not entry or not entry.attachment:
        raise Http404
    ext = _file_ext(entry.attachment)
    if ext == "pdf":
        response = FileResponse(entry.attachment.open(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{entry.attachment.name.split("/")[-1]}"'
        return response
    if ext in _IMAGE_EXTS:
        ct = mimetypes.guess_type(entry.attachment.name)[0] or "application/octet-stream"
        response = FileResponse(entry.attachment.open(), content_type=ct)
        response["Content-Disposition"] = "inline"
        return response
    if ext in _TEXT_EXTS:
        content = entry.attachment.read(50_000).decode("utf-8", errors="replace")
        return HttpResponse(content, content_type="text/plain; charset=utf-8")
    raise Http404


def education_download(request, pk):
    """Force-download an EducationEntry attachment."""
    entry = EducationEntry.objects.filter(pk=pk).first()
    if not entry or not entry.attachment:
        raise Http404
    filename = entry.attachment.name.split("/")[-1]
    response = FileResponse(entry.attachment.open())
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@xframe_options_sameorigin
def certification_pdf_inline(request, pk):
    """Serve a Certification PDF attachment inline."""
    cert = Certification.objects.filter(pk=pk).first()
    if not cert or not _is_pdf(cert.attachment):
        raise Http404
    response = FileResponse(cert.attachment.open(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{cert.attachment.name.split("/")[-1]}"'
    return response


class PDFViewerView(TemplateView):
    """Generic PDF.js viewer, receives pdf_url via URL kwargs."""
    template_name = "portfolio/pdf_viewer.html"

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return xframe_options_sameorigin(view)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pdf_url"] = self.kwargs.get("pdf_url", "")
        return ctx


def education_preview(request, pk):
    """Viewer page for an EducationEntry PDF attachment."""
    from django.urls import reverse
    entry = EducationEntry.objects.filter(pk=pk).first()
    if not entry or not _is_pdf(entry.attachment):
        raise Http404
    pdf_url = reverse("portfolio:education_pdf_inline", args=[pk])
    return render(request, "portfolio/pdf_viewer.html", {"pdf_url": pdf_url, "title": str(entry)})


@xframe_options_sameorigin
def certification_inline(request, pk):
    """Serve a Certification attachment inline (PDF, image, or text)."""
    cert = Certification.objects.filter(pk=pk).first()
    if not cert or not cert.attachment:
        raise Http404
    ext = _file_ext(cert.attachment)
    if ext == "pdf":
        response = FileResponse(cert.attachment.open(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{cert.attachment.name.split("/")[-1]}"'
        return response
    if ext in _IMAGE_EXTS:
        ct = mimetypes.guess_type(cert.attachment.name)[0] or "application/octet-stream"
        response = FileResponse(cert.attachment.open(), content_type=ct)
        response["Content-Disposition"] = "inline"
        return response
    if ext in _TEXT_EXTS:
        content = cert.attachment.read(50_000).decode("utf-8", errors="replace")
        return HttpResponse(content, content_type="text/plain; charset=utf-8")
    raise Http404


def certification_preview(request, pk):
    """Viewer page for a Certification PDF attachment (standalone new-tab use)."""
    from django.urls import reverse
    cert = Certification.objects.filter(pk=pk).first()
    if not cert or not _is_pdf(cert.attachment):
        raise Http404
    pdf_url = reverse("portfolio:certification_inline", args=[pk])
    return render(request, "portfolio/pdf_viewer.html", {"pdf_url": pdf_url, "title": str(cert)})


@xframe_options_sameorigin
def project_attachment_pdf_inline(request, pk):
    """Serve a ProjectAttachment PDF file inline."""
    att = ProjectAttachment.objects.filter(pk=pk, visible=True).first()
    if not att or not _is_pdf(att.file):
        raise Http404
    response = FileResponse(att.file.open(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{att.file.name.split("/")[-1]}"'
    return response


def project_attachment_preview(request, pk):
    """Viewer page for a ProjectAttachment PDF."""
    from django.urls import reverse
    att = ProjectAttachment.objects.filter(pk=pk, visible=True).first()
    if not att or not _is_pdf(att.file):
        raise Http404
    pdf_url = reverse("portfolio:project_attachment_pdf_inline", args=[pk])
    return render(request, "portfolio/pdf_viewer.html", {"pdf_url": pdf_url, "title": str(att)})


def project_attachment_download(request, pk):
    """Force-download a ProjectAttachment file."""
    att = ProjectAttachment.objects.filter(pk=pk, visible=True).first()
    if not att or not att.file:
        raise Http404
    filename = att.file.name.split("/")[-1]
    response = FileResponse(att.file.open())
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@xframe_options_sameorigin
def project_attachment_text_inline(request, pk):
    """Serve a ProjectAttachment text file inline as text/plain."""
    att = ProjectAttachment.objects.filter(pk=pk, visible=True).first()
    if not att or not att.is_text_previewable:
        raise Http404
    content = att.file.read(50_000).decode("utf-8", errors="replace")
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# Notebook (.ipynb) rendering
# ---------------------------------------------------------------------------
_NOTEBOOK_MAX_BYTES = 200_000
_NOTEBOOK_MAX_CELLS = 200

_NOTEBOOK_CSS = (
    "body{font-family:system-ui,-apple-system,sans-serif;margin:1em;font-size:13px;}"
    ".nb-md{background:#f8f9fa;border-left:3px solid #6c757d;padding:8px 12px;margin:8px 0;}"
    ".nb-code{background:#1e1e1e;color:#d4d4d4;padding:8px 12px;margin:8px 0;border-radius:4px;}"
    ".nb-code pre{margin:0;white-space:pre-wrap;word-break:break-all;}"
    ".nb-out{background:#fff3cd;border-left:3px solid #ffc107;padding:8px 12px;margin:4px 0 8px 0;}"
    ".nb-out pre{margin:0;white-space:pre-wrap;word-break:break-all;}"
    ".nb-md pre{margin:0;white-space:pre-wrap;word-break:break-word;}"
    ".nb-raw{background:#e2e3e5;padding:8px 12px;margin:8px 0;}"
    ".nb-raw pre{margin:0;white-space:pre-wrap;}"
)


def _render_notebook_html(raw_bytes):
    """Parse .ipynb JSON and return safe HTML body string, or None on failure/oversize."""
    if len(raw_bytes) > _NOTEBOOK_MAX_BYTES:
        return None
    try:
        nb = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    cells = nb.get("cells", [])
    if len(cells) > _NOTEBOOK_MAX_CELLS:
        return None
    parts = []
    for cell in cells:
        ct = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))
        if ct == "markdown":
            parts.append(f'<div class="nb-md"><pre>{escape(source)}</pre></div>')
        elif ct == "code":
            parts.append(f'<div class="nb-code"><pre><code>{escape(source)}</code></pre></div>')
            for out in cell.get("outputs", []):
                if out.get("output_type") == "stream":
                    text = "".join(out.get("text", []))
                    parts.append(f'<div class="nb-out"><pre>{escape(text)}</pre></div>')
                elif "text/plain" in out.get("data", {}):
                    text = "".join(out["data"]["text/plain"])
                    parts.append(f'<div class="nb-out"><pre>{escape(text)}</pre></div>')
        elif ct == "raw":
            parts.append(f'<div class="nb-raw"><pre>{escape(source)}</pre></div>')
    return "\n".join(parts)


def _notebook_response(file_field):
    """Build an HttpResponse for a notebook file. Returns (response, is_rich)."""
    raw = file_field.read(_NOTEBOOK_MAX_BYTES + 1)
    html_body = _render_notebook_html(raw)
    if html_body is None:
        content = raw[:50_000].decode("utf-8", errors="replace")
        return HttpResponse(content, content_type="text/plain; charset=utf-8"), False
    page = (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<style>{_NOTEBOOK_CSS}</style></head><body>'
        f'{html_body}</body></html>'
    )
    return HttpResponse(page, content_type="text/html; charset=utf-8"), True


@xframe_options_sameorigin
def project_attachment_notebook_inline(request, pk):
    """Render a ProjectAttachment .ipynb as rich HTML."""
    att = ProjectAttachment.objects.filter(pk=pk, visible=True).first()
    if not att or att.file_ext != "ipynb":
        raise Http404
    response, _ = _notebook_response(att.file)
    return response


def legacy_attachment_download(request, pk):
    """Force-download a Project's legacy attachment field."""
    project = Project.objects.filter(pk=pk, visible=True).first()
    if not project or not project.attachment:
        raise Http404
    filename = project.attachment.name.split("/")[-1]
    response = FileResponse(project.attachment.open())
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@xframe_options_sameorigin
def legacy_attachment_inline(request, pk):
    """Serve a Project's legacy attachment inline for preview."""
    project = Project.objects.filter(pk=pk, visible=True).first()
    if not project or not project.attachment:
        raise Http404
    ext = _file_ext(project.attachment)
    if ext == "pdf":
        response = FileResponse(project.attachment.open(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{project.attachment.name.split("/")[-1]}"'
        return response
    if ext in _IMAGE_EXTS or ext in _AUDIO_EXTS or ext in _VIDEO_EXTS:
        ct = mimetypes.guess_type(project.attachment.name)[0] or "application/octet-stream"
        response = FileResponse(project.attachment.open(), content_type=ct)
        response["Content-Disposition"] = "inline"
        return response
    if ext == "ipynb":
        resp, _ = _notebook_response(project.attachment)
        return resp
    if ext in _TEXT_EXTS:
        content = project.attachment.read(50_000).decode("utf-8", errors="replace")
        return HttpResponse(content, content_type="text/plain; charset=utf-8")
    raise Http404


def _group_by_category(queryset):
    """Group a queryset by category. Returns [(name, category_obj_or_None, [items])]."""
    groups = OrderedDict()
    cat_objs = OrderedDict()
    for item in queryset:
        if item.category:
            name = item.category.name
            cat_objs[name] = item.category
        else:
            name = "Other"
            cat_objs.setdefault(name, None)
        groups.setdefault(name, []).append(item)
    # Move "Other" to end if present
    if "Other" in groups:
        other = groups.pop("Other")
        groups["Other"] = other
        cat_objs.pop("Other", None)
        cat_objs["Other"] = None
    return [(name, cat_objs[name], items) for name, items in groups.items()]


class EducationView(ThemeTemplateMixin, ListView):
    model = EducationEntry
    template_name = "portfolio/education.html"
    context_object_name = "education_entries"
    paginate_by = 10

    def get_queryset(self):
        return EducationEntry.objects.select_related("category").filter(visible=True).order_by("order", "id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for entry in ctx["education_entries"]:
            entry.preview_kind = _preview_kind_for_ext(_file_ext(entry.attachment))
        ctx["education_groups"] = _group_by_category(ctx["education_entries"])
        ctx["all_education"] = EducationEntry.objects.select_related("category").filter(visible=True).order_by("order", "id")
        return ctx


class CertificationsView(ThemeTemplateMixin, ListView):
    model = Certification
    template_name = "portfolio/certifications.html"
    context_object_name = "certifications"
    paginate_by = 10

    def get_queryset(self):
        return Certification.objects.select_related("category").filter(visible=True).order_by("order", "id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for cert in ctx["certifications"]:
            cert.preview_kind = _preview_kind_for_ext(_file_ext(cert.attachment))
        ctx["cert_groups"] = _group_by_category(ctx["certifications"])
        ctx["all_certifications"] = Certification.objects.select_related("category").filter(visible=True).order_by("order", "id")
        return ctx


class ContactView(ThemeTemplateMixin, TemplateView):
    template_name = "portfolio/contact.html"

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(form=ContactForm())
        return render(request, self.get_template_names(), ctx)

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for reaching out! I'll respond soon.")
            return redirect("portfolio:contact")
        messages.error(request, "Please correct the errors below.")
        ctx = self.get_context_data(form=form)
        return render(request, self.get_template_names(), ctx)


def variant_review(request):
    """DEBUG-only page for quickly previewing every variant across core pages."""
    if not django_settings.DEBUG:
        raise Http404

    first_project = Project.objects.filter(visible=True).first()
    project_detail_url = first_project.get_absolute_url() if first_project else None

    core_pages = [
        ("Home", "/"),
        ("Projects", "/projects/"),
    ]
    if project_detail_url:
        core_pages.append(("Project Detail", project_detail_url))
    core_pages += [
        ("About", "/about/"),
        ("Resume", "/resume/"),
        ("Education", "/education/"),
        ("Certifications", "/certifications/"),
        ("Contact", "/contact/"),
    ]

    profiles = LayoutProfile.objects.order_by("template_variant", "name")
    variants = []
    for slug, label in TEMPLATE_VARIANT_CHOICES:
        profile = profiles.filter(template_variant=slug).first()
        variants.append({
            "slug": slug,
            "label": label,
            "profile_slug": profile.slug if profile else None,
        })

    return render(request, "portfolio/variant_review.html", {
        "variants": variants,
        "core_pages": core_pages,
    })
