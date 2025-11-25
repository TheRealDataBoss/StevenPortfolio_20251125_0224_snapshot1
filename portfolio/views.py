from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, ListView, DetailView

from .forms import ContactForm
from .models import Category, Project, Resume, SiteSetting


class HomeView(TemplateView):
    template_name = "portfolio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["settings"] = SiteSetting.objects.first()
        context["featured_projects"] = Project.objects.filter(is_featured=True)[:3]
        context["recent_projects"] = Project.objects.order_by("-created_at")[:6]
        context["categories"] = Category.objects.all()
        return context


class ProjectListView(ListView):
    model = Project
    template_name = "portfolio/project_list.html"
    context_object_name = "projects"
    paginate_by = 9

    def get_queryset(self):
        qs = Project.objects.select_related("category").all()
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


class ProjectDetailView(DetailView):
    model = Project
    slug_field = "slug"
    template_name = "portfolio/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["related"] = (
            Project.objects.filter(category=self.object.category)
            .exclude(pk=self.object.pk)
            .order_by("-created_at")[:3]
        )
        return ctx


class AboutView(TemplateView):
    template_name = "portfolio/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["settings"] = SiteSetting.objects.first()
        return ctx


class ResumeView(TemplateView):
    template_name = "portfolio/resume.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["latest_resume"] = Resume.objects.first()
        ctx["resume_entries"] = Resume.objects.all()
        return ctx


class ContactView(TemplateView):
    template_name = "portfolio/contact.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": ContactForm()})

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for reaching out! I'll respond soon.")
            return redirect("portfolio:contact")
        messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {"form": form})
