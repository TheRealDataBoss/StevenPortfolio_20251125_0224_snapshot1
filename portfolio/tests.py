import re

from django.test import TestCase
from django.urls import reverse

from portfolio.models import NavItem


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
