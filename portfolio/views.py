from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView, ListView, DetailView

from .forms import ContactForm
from .mixins import ThemeTemplateMixin
from .models import Category, Project, Resume, SiteSetting


def _is_pdf(field):
    return field and field.name and field.name.lower().endswith(".pdf")


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
        context["settings"] = SiteSetting.objects.first()
        context["featured_projects"] = Project.objects.filter(is_featured=True, visible=True)[:3]
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
