import re

from django.test import TestCase
from django.urls import reverse

from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.models import Category, NavItem, Project, Resume, SiteSetting


class HomepageTestCase(TestCase):
    """Smoke test: verify homepage renders without errors."""

    def test_homepage_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_homepage_uses_correct_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'portfolio/home.html')


class ContactFormTestCase(TestCase):
    """Test contact form GET and POST."""

    def test_contact_page_returns_200(self):
        response = self.client.get('/contact/')
        self.assertEqual(response.status_code, 200)

    def test_contact_post_redirects_on_success(self):
        response = self.client.post('/contact/', {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'Test message content.',
        })
        self.assertEqual(response.status_code, 302)


class AllPagesTestCase(TestCase):
    """Verify all main pages render."""

    def test_projects_page(self):
        response = self.client.get('/projects/')
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get('/about/')
        self.assertEqual(response.status_code, 200)

    def test_resume_page(self):
        response = self.client.get('/resume/')
        self.assertEqual(response.status_code, 200)


class ResumeDownloadTests(TestCase):
    """Verify /resume/ surfaces the primary resume download link."""

    def test_resume_page_shows_download_when_primary_exists(self):
        Resume.objects.create(
            title="My Resume",
            category="general",
            is_primary=True,
            file=SimpleUploadedFile("resume.pdf", b"%PDF-1.4 test content"),
        )
        response = self.client.get("/resume/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Download Resume")
        self.assertContains(response, "/media/resumes/")

    def test_resume_page_shows_message_when_no_primary(self):
        response = self.client.get("/resume/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No resume uploaded yet")


class NavigationWiringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Mirror the intended production nav state in a deterministic way.
        home, _ = NavItem.objects.update_or_create(
            title="Home",
            parent=None,
            defaults={
                "url": "/",
                "order": 1,
                "icon": "fas fa-home",
                "visible": True,
            },
        )

        portfolio, _ = NavItem.objects.update_or_create(
            title="Portfolio",
            parent=None,
            defaults={
                "url": "#",
                "order": 2,
                "icon": "fas fa-folder-open",
                "visible": True,
            },
        )

        resume, _ = NavItem.objects.update_or_create(
            title="Resume",
            parent=None,
            defaults={
                "url": "/resume/",
                "order": 3,
                "icon": "fas fa-file-alt",
                "visible": True,
            },
        )

        projects, _ = NavItem.objects.update_or_create(
            title="Projects",
            parent=None,
            defaults={
                "url": "/projects/",
                "order": 4,
                "icon": "fas fa-briefcase",
                "visible": True,
            },
        )

        about, _ = NavItem.objects.update_or_create(
            title="About",
            parent=None,
            defaults={
                "url": "/about/",
                "order": 5,
                "icon": "fas fa-user",
                "visible": True,
            },
        )

        contact, _ = NavItem.objects.update_or_create(
            title="Contact",
            parent=None,
            defaults={
                "url": "/contact/",
                "order": 6,
                "icon": "fas fa-envelope",
                "visible": True,
            },
        )

        # Dropdown children under Portfolio (mirrored links intentionally)
        NavItem.objects.update_or_create(
            title="Projects",
            parent=portfolio,
            defaults={
                "url": "/projects/",
                "order": 1,
                "icon": "fas fa-briefcase",
                "visible": True,
            },
        )
        NavItem.objects.update_or_create(
            title="Resume",
            parent=portfolio,
            defaults={
                "url": "/resume/",
                "order": 2,
                "icon": "fas fa-file-alt",
                "visible": True,
            },
        )

    def test_navitems_db_order_top_level(self):
        expected = ["Home", "Portfolio", "Resume", "Projects", "About", "Contact"]
        actual = list(
            NavItem.objects.filter(parent__isnull=True, visible=True)
            .order_by("order")
            .values_list("title", flat=True)
        )
        self.assertEqual(actual, expected)

    def test_navitems_db_order_portfolio_children(self):
        expected = ["Projects", "Resume"]
        actual = list(
            NavItem.objects.filter(parent__title="Portfolio", visible=True)
            .order_by("order")
            .values_list("title", flat=True)
        )
        self.assertEqual(actual, expected)

    def test_homepage_renders_nav_titles(self):
        # Basic integration sanity: ensure these labels appear in rendered HTML.
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        for title in ["Home", "Portfolio", "Resume", "Projects", "About", "Contact"]:
            self.assertContains(response, title)

    def test_portfolio_dropdown_contains_children(self):
        """The navbar renders Portfolio as a dropdown with Projects and Resume children."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        # Extract the <li class="nav-item dropdown"> block that contains "Portfolio".
        # Use the dropdown-menu within that block to verify children.
        dropdown_block = re.search(
            r'<li\s+class="nav-item dropdown">\s*'
            r'<a[^>]*dropdown-toggle[^>]*>.*?Portfolio.*?</a>\s*'
            r'<ul\s+class="dropdown-menu"[^>]*>(.*?)</ul>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(dropdown_block, "No dropdown-menu found for Portfolio")
        menu_html = dropdown_block.group(1)

        # Both children should appear as dropdown-items inside the menu.
        self.assertIn("Projects", menu_html)
        self.assertIn("Resume", menu_html)
        self.assertEqual(menu_html.count("dropdown-item"), 2)


class ProjectVisibilityTests(TestCase):
    """Task 1: projects respect visible/order fields."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Data Science", slug="data-science")
        cls.visible = Project.objects.create(
            title="Visible Project", slug="visible-project",
            category=cls.cat, description="A visible project.",
            visible=True, order=1,
        )
        cls.hidden = Project.objects.create(
            title="Hidden Project", slug="hidden-project",
            category=cls.cat, description="A hidden project.",
            visible=False, order=2,
        )

    def test_project_list_shows_visible_only(self):
        response = self.client.get("/projects/")
        self.assertContains(response, "Visible Project")
        self.assertNotContains(response, "Hidden Project")

    def test_project_detail_renders(self):
        response = self.client.get("/projects/visible-project/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Project")

    def test_project_list_links_to_detail(self):
        response = self.client.get("/projects/")
        self.assertContains(response, "/projects/visible-project/")


class AboutPageTests(TestCase):
    """Task 2: about page renders SiteSetting personal fields."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSetting.objects.create(
            full_name="Steven Wazlavek",
            headline="Data Analyst | Python Developer",
            bio_long="Test bio content for about page.",
            linkedin_url="https://linkedin.com/in/test",
            github_url="https://github.com/test",
        )

    def test_about_shows_full_name(self):
        response = self.client.get("/about/")
        self.assertContains(response, "Steven Wazlavek")

    def test_about_shows_headline(self):
        response = self.client.get("/about/")
        self.assertContains(response, "Data Analyst | Python Developer")

    def test_about_shows_social_links(self):
        response = self.client.get("/about/")
        self.assertContains(response, "https://linkedin.com/in/test")
        self.assertContains(response, "https://github.com/test")

    def test_contact_shows_social_links(self):
        response = self.client.get("/contact/")
        self.assertContains(response, "https://linkedin.com/in/test")
        self.assertContains(response, "https://github.com/test")


class NavActiveStateTests(TestCase):
    """Task 3: active class applied to current nav item."""

    @classmethod
    def setUpTestData(cls):
        NavItem.objects.create(title="Projects", url="/projects/", order=1, visible=True)
        NavItem.objects.create(title="About", url="/about/", order=2, visible=True)

    def test_projects_nav_active_on_projects_page(self):
        response = self.client.get("/projects/")
        html = response.content.decode()
        # The Projects nav link should have the active class
        match = re.search(r'<a\s+class="nav-link\s+active"\s+href="/projects/"', html)
        self.assertIsNotNone(match, "Projects nav link should have 'active' class on /projects/")

    def test_about_nav_not_active_on_projects_page(self):
        response = self.client.get("/projects/")
        html = response.content.decode()
        # The About nav link should NOT have the active class on /projects/
        match = re.search(r'<a\s+class="nav-link\s+active"\s+href="/about/"', html)
        self.assertIsNone(match, "About nav link should NOT have 'active' class on /projects/")


class ThemeTemplateSwitchingTests(TestCase):
    """Verify ThemeTemplateMixin selects templates based on SiteSetting.theme."""

    def test_default_uses_standard_templates(self):
        """No SiteSetting at all — light theme, standard templates."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portfolio/home.html")

    def test_light_theme_uses_standard_templates(self):
        SiteSetting.objects.create(theme="light")
        response = self.client.get("/")
        self.assertTemplateUsed(response, "portfolio/home.html")

    def test_dark_theme_uses_dark_base(self):
        """Dark theme should extend dark/base.html which extends base.html."""
        SiteSetting.objects.create(theme="dark")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portfolio/dark/base.html")
        self.assertTemplateUsed(response, "portfolio/base.html")

    def test_dark_theme_injects_base_template_context(self):
        SiteSetting.objects.create(theme="dark")
        response = self.client.get("/")
        self.assertEqual(response.context["base_template"], "portfolio/dark/base.html")

    def test_light_theme_no_base_template_in_context(self):
        SiteSetting.objects.create(theme="light")
        response = self.client.get("/")
        self.assertNotIn("base_template", response.context)

    def test_dark_theme_loads_dark_css(self):
        SiteSetting.objects.create(theme="dark")
        response = self.client.get("/")
        self.assertContains(response, "theme_dark.css")

    def test_motion_disabled_adds_body_class(self):
        SiteSetting.objects.create(motion_enabled=False)
        response = self.client.get("/")
        self.assertContains(response, "no-motion")

    def test_motion_enabled_no_class(self):
        SiteSetting.objects.create(motion_enabled=True)
        response = self.client.get("/")
        self.assertNotContains(response, "no-motion")


class MediaImgTests(TestCase):
    """Verify {% media_img %} tag outputs correct aspect-ratio classes."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSetting.objects.create(
            full_name="Test User",
            bio_long="Full executive bio paragraph.",
            headshot=SimpleUploadedFile("face.jpg", b"\xff\xd8\xff\xe0", content_type="image/jpeg"),
        )

    def test_about_headshot_has_media_img_classes(self):
        response = self.client.get("/about/")
        self.assertContains(response, "media-img")
        self.assertContains(response, "media-img--portrait")
        self.assertContains(response, "media-img--cover")

    def test_about_renders_bio_long(self):
        response = self.client.get("/about/")
        self.assertContains(response, "Full executive bio paragraph.")
