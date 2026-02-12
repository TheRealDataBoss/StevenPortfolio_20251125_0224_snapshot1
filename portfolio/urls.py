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
    path("education/", views.EducationView.as_view(), name="education"),
    path("education/<int:pk>/preview/", views.education_preview, name="education_preview"),
    path("education/<int:pk>/inline/", views.education_inline, name="education_inline"),
    path("education/<int:pk>/download/", views.education_download, name="education_download"),
    path("education/<int:pk>/pdf/", views.education_pdf_inline, name="education_pdf_inline"),
    path("certifications/", views.CertificationsView.as_view(), name="certifications"),
    path("certifications/<int:pk>/inline/", views.certification_inline, name="certification_inline"),
    path("certifications/<int:pk>/preview/", views.certification_preview, name="certification_preview"),
    path("certifications/<int:pk>/pdf/", views.certification_pdf_inline, name="certification_pdf_inline"),
    path("projects/attachments/<int:pk>/preview/", views.project_attachment_preview, name="project_attachment_preview"),
    path("projects/attachments/<int:pk>/pdf/", views.project_attachment_pdf_inline, name="project_attachment_pdf_inline"),
    path("projects/attachments/<int:pk>/text/", views.project_attachment_text_inline, name="project_attachment_text_inline"),
    path("projects/attachments/<int:pk>/notebook/", views.project_attachment_notebook_inline, name="project_attachment_notebook_inline"),
    path("projects/attachments/<int:pk>/download/", views.project_attachment_download, name="project_attachment_download"),
    path("projects/legacy/<int:pk>/download/", views.legacy_attachment_download, name="legacy_attachment_download"),
    path("projects/legacy/<int:pk>/inline/", views.legacy_attachment_inline, name="legacy_attachment_inline"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("variant-review/", views.variant_review, name="variant_review"),
]
