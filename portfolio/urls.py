from django.urls import path
from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("projects/<slug:slug>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("resume/viewer/", views.ResumeViewerView.as_view(), name="resume_viewer"),
    path("resume/preview/", views.resume_pdf_inline, name="resume_pdf_inline"),
    path("resume/", views.ResumeView.as_view(), name="resume"),
    path("contact/", views.ContactView.as_view(), name="contact"),
]
