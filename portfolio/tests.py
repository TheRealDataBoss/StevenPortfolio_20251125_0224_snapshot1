import json
import re

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.models import Category, Certification, ContactMessage, EducationEntry, ImageVariant, LayoutProfile, NavItem, Project, ProjectAttachment, Resume, SiteSetting, TEMPLATE_VARIANT_CHOICES, resolve_active_profile


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
        before = ContactMessage.objects.count()
        payload = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'Test message content.',
        }
        response = self.client.post('/contact/', payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), before + 1)
        msg = ContactMessage.objects.latest('created_at')
        self.assertEqual(msg.name, payload['name'])
        self.assertEqual(msg.email, payload['email'])
        self.assertEqual(msg.subject, payload['subject'])
        self.assertEqual(msg.message, payload['message'])


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

        projects, _ = NavItem.objects.update_or_create(
            title="Projects",
            parent=None,
            defaults={
                "url": "/projects/",
                "order": 3,
                "icon": "fas fa-briefcase",
                "visible": True,
            },
        )

        resume, _ = NavItem.objects.update_or_create(
            title="Resume",
            parent=None,
            defaults={
                "url": "/resume/",
                "order": 4,
                "icon": "fas fa-file-alt",
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
        expected = ["Home", "Portfolio", "Projects", "Resume", "About", "Contact"]
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

    def test_navbar_uses_container_not_container_fluid(self):
        """Navbar inner wrapper must be .container (not .container-fluid) to
        align brand/links with page content edges."""
        response = self.client.get("/")
        html = response.content.decode()
        nav_match = re.search(
            r'<nav\b[^>]*navbar[^>]*>(.*?)</nav>', html, re.DOTALL,
        )
        self.assertIsNotNone(nav_match, "No <nav> with .navbar found")
        nav_html = nav_match.group(1)
        self.assertIn('<div class="container">', nav_html)
        self.assertNotIn("container-fluid", nav_html)

    def test_navbar_nav_has_ms_auto(self):
        """The rendered navbar-nav UL must include ms-auto so links
        sit right-aligned within the .container."""
        response = self.client.get("/")
        html = response.content.decode()
        self.assertRegex(
            html,
            r'<ul\s+class="navbar-nav\s+ms-auto[^"]*"',
        )


class NavbarAlignmentAcrossVariantsTests(TestCase):
    """Guardrail: navbar structure (.container + ms-auto) must hold for every
    core route under every template variant.  Also asserts 200 for each
    combination so variant CSS cannot break page rendering."""

    CORE_ROUTES = ["/", "/projects/", "/about/", "/resume/",
                   "/education/", "/certifications/", "/contact/"]

    @classmethod
    def setUpTestData(cls):
        # Nav items needed so the dynamic branch (with _nav.html) renders.
        NavItem.objects.update_or_create(
            title="Home", parent=None,
            defaults={"url": "/", "order": 1, "visible": True},
        )
        portfolio, _ = NavItem.objects.update_or_create(
            title="Portfolio", parent=None,
            defaults={"url": "#", "order": 2, "visible": True},
        )
        NavItem.objects.update_or_create(
            title="Projects", parent=portfolio,
            defaults={"url": "/projects/", "order": 1, "visible": True},
        )
        NavItem.objects.update_or_create(
            title="Resume", parent=portfolio,
            defaults={"url": "/resume/", "order": 2, "visible": True},
        )
        # Create one LayoutProfile per variant so ?profile= works.
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            LayoutProfile.objects.update_or_create(
                slug=f"test-{slug}",
                defaults={
                    "name": f"Test {label}",
                    "template_variant": slug,
                },
            )

    def _assert_navbar_structure(self, html, label):
        """Shared helper: assert .container inside <nav> and ms-auto on UL."""
        nav_match = re.search(
            r'<nav\b[^>]*navbar[^>]*>(.*?)</nav>', html, re.DOTALL,
        )
        self.assertIsNotNone(nav_match, f"No <nav> found [{label}]")
        nav_html = nav_match.group(1)
        self.assertIn('<div class="container">', nav_html,
                      f"Navbar missing .container [{label}]")
        self.assertNotIn("container-fluid", nav_html,
                         f"Navbar has container-fluid [{label}]")
        self.assertRegex(
            html, r'<ul\s+class="navbar-nav\s+ms-auto[^"]*"',
            f"Navbar UL missing ms-auto [{label}]",
        )

    def test_navbar_structure_default_all_routes(self):
        """Default variant: every core route has correct navbar."""
        for route in self.CORE_ROUTES:
            with self.subTest(route=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200)
                self._assert_navbar_structure(resp.content.decode(),
                                              f"default {route}")

    def test_navbar_structure_all_variants_homepage(self):
        """Every variant renders homepage 200 with correct navbar."""
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            with self.subTest(variant=slug):
                resp = self.client.get(f"/?profile=test-{slug}")
                self.assertEqual(resp.status_code, 200, f"{slug} gave non-200")
                self._assert_navbar_structure(resp.content.decode(), slug)

    def test_default_homepage_hero_has_variant_scoped_spacing(self):
        """Default variant CSS must include hero spacing rule scoped to
        body.variant-default so the hero doesn't sit flush against the navbar."""
        resp = self.client.get("/?profile=test-default")
        html = resp.content.decode()
        self.assertIn("body.variant-default .hero", html,
                       "Default variant CSS missing scoped .hero spacing rule")


@override_settings(DEBUG=True)
class VariantTemplateResolutionTests(TestCase):
    """Guardrail: variant template resolution picks variant-specific templates
    when they exist, falls back to the standard templates otherwise, and
    preserves the navbar alignment contract regardless."""

    CORE_ROUTES = ["/", "/projects/", "/about/", "/resume/",
                   "/education/", "/certifications/", "/contact/",
                   "/projects/vtr-test-project/"]

    # All non-default variants now have a complete set of 8 page templates
    FULL_VARIANTS = [slug for slug, _ in TEMPLATE_VARIANT_CHOICES if slug != "default"]

    @classmethod
    def setUpTestData(cls):
        cat = Category.objects.create(name="VTR Cat", slug="vtr-cat")
        Project.objects.create(
            title="VTR Test Project", slug="vtr-test-project",
            category=cat, visible=True,
        )
        NavItem.objects.update_or_create(
            title="Home", parent=None,
            defaults={"url": "/", "order": 1, "visible": True},
        )
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            LayoutProfile.objects.update_or_create(
                slug=f"vtr-{slug}",
                defaults={"name": f"VTR {label}", "template_variant": slug},
            )

    def test_modern_saas_homepage_uses_variant_template(self):
        """modern_saas has a variant-specific home.html; it should be used."""
        resp = self.client.get("/?profile=vtr-modern_saas")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('data-variant-template="modern_saas"', html,
                       "modern_saas variant home.html was not selected")

    def test_default_homepage_does_not_have_variant_marker(self):
        """Default variant should use the standard home.html (no marker)."""
        resp = self.client.get("/?profile=vtr-default")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertNotIn("data-variant-template=", html,
                          "Default homepage should use the standard template")

    def test_default_variant_fallback_no_variant_marker(self):
        """Default variant should use standard templates on all routes and
        never include a variant marker (no TemplateDoesNotExist)."""
        for route in self.CORE_ROUTES:
            with self.subTest(route=route):
                resp = self.client.get(f"{route}?profile=vtr-default")
                self.assertEqual(resp.status_code, 200,
                                 f"default {route} should render fine")
                self.assertNotIn("data-variant-template=",
                                 resp.content.decode(),
                                 f"default {route} should not have variant marker")

    def test_all_variants_homepage_still_200(self):
        """Every variant renders the homepage without TemplateDoesNotExist."""
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            with self.subTest(variant=slug):
                resp = self.client.get(f"/?profile=vtr-{slug}")
                self.assertEqual(resp.status_code, 200, f"{slug} homepage broke")

    def test_full_variant_all_routes_use_variant_template(self):
        """Variants with complete template sets should render their own
        template (with data-variant-template marker) on every core route."""
        for variant in self.FULL_VARIANTS:
            for route in self.CORE_ROUTES:
                with self.subTest(variant=variant, route=route):
                    resp = self.client.get(f"{route}?profile=vtr-{variant}")
                    self.assertEqual(resp.status_code, 200)
                    self.assertIn(
                        f'data-variant-template="{variant}"',
                        resp.content.decode(),
                        f"{variant} {route} did not use variant template",
                    )

    def test_full_variant_navbar_contract_all_routes(self):
        """Navbar alignment contract must hold on every route for variants
        with custom HTML templates."""
        for variant in self.FULL_VARIANTS:
            for route in self.CORE_ROUTES:
                with self.subTest(variant=variant, route=route):
                    resp = self.client.get(f"{route}?profile=vtr-{variant}")
                    html = resp.content.decode()
                    nav_match = re.search(
                        r'<nav\b[^>]*navbar[^>]*>(.*?)</nav>', html, re.DOTALL,
                    )
                    self.assertIsNotNone(nav_match,
                                         f"No <nav> on {variant} {route}")
                    self.assertIn('<div class="container">',
                                  nav_match.group(1),
                                  f"Missing .container on {variant} {route}")
                    self.assertNotIn("container-fluid",
                                     nav_match.group(1),
                                     f"Has container-fluid on {variant} {route}")
                    self.assertRegex(
                        html,
                        r'<ul\s+class="navbar-nav\s+ms-auto[^"]*"',
                        f"Missing ms-auto on {variant} {route}",
                    )

    def test_full_variants_have_all_template_files_on_disk(self):
        """Guardrail: every variant in FULL_VARIANTS must have all 8 page
        templates on disk under templates/portfolio/variants/<slug>/."""
        import pathlib
        variant_dir = pathlib.Path(__file__).resolve().parent.parent / "templates" / "portfolio" / "variants"
        pages = ["home.html", "project_list.html", "project_detail.html",
                 "about.html", "resume.html", "education.html",
                 "certifications.html", "contact.html"]
        for variant in self.FULL_VARIANTS:
            for page in pages:
                with self.subTest(variant=variant, page=page):
                    path = variant_dir / variant / page
                    self.assertTrue(
                        path.exists(),
                        f"Missing template: variants/{variant}/{page}",
                    )


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
        html = response.content.decode()
        self.assertRegex(html, r'<body\s+class="[^"]*no-motion')

    def test_motion_enabled_no_body_class(self):
        SiteSetting.objects.create(motion_enabled=True)
        response = self.client.get("/")
        html = response.content.decode()
        self.assertNotRegex(html, r'<body\s+class="[^"]*no-motion')


class MediaImgTests(TestCase):
    """Verify {% media_img %} tag outputs correct aspect-ratio classes."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSetting.objects.create(
            full_name="Test User",
            bio_long="Full executive bio paragraph.",
            headshot=SimpleUploadedFile("face.jpg", b"\xff\xd8\xff\xe0", content_type="image/jpeg"),
        )

    def test_about_headshot_has_circle_shape(self):
        response = self.client.get("/about/")
        self.assertContains(response, "img-square")
        self.assertContains(response, "img-shape-circle")

    def test_about_renders_bio_long(self):
        response = self.client.get("/about/")
        self.assertContains(response, "Full executive bio paragraph.")


class ResponsiveImageTests(TestCase):
    """Verify {% responsive_image %} tag and CSS classes in project cards."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Test Cat", slug="test-cat")
        cls.project = Project.objects.create(
            title="Card Project", slug="card-project",
            category=cls.cat, description="A test project.",
            image=SimpleUploadedFile("proj.jpg", b"\xff\xd8\xff\xe0", content_type="image/jpeg"),
            visible=True,
        )

    def test_project_list_card_has_img_card_class(self):
        response = self.client.get("/projects/")
        self.assertContains(response, "img-card")

    def test_project_detail_has_img_hero_class(self):
        response = self.client.get("/projects/card-project/")
        self.assertContains(response, "img-hero")

    def test_base_has_img_css_definitions(self):
        response = self.client.get("/")
        self.assertContains(response, ".img-hero")
        self.assertContains(response, ".img-card")
        self.assertContains(response, ".img-hover-scale")

    def test_image_variant_model(self):
        iv = ImageVariant.objects.create(
            name="banner", aspect_ratio="21:9", crop_mode="cover", order=1,
        )
        self.assertEqual(iv.css_ratio, "21 / 9")
        self.assertEqual(str(iv), "banner (21:9)")

    def test_project_list_card_has_rounded_shape(self):
        response = self.client.get("/projects/")
        self.assertContains(response, "img-shape-rounded")

    def test_base_has_shape_css_definitions(self):
        response = self.client.get("/")
        self.assertContains(response, ".img-shape-circle")
        self.assertContains(response, ".img-shape-rounded")


class ImageVariantShapeCropTests(TestCase):
    """Verify ImageVariant shape and crop fields render correctly."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shape Cat", slug="shape-cat")

    def test_db_variant_circle_shape(self):
        ImageVariant.objects.create(
            name="avatar", aspect_ratio="1:1", crop_mode="cover",
            shape="circle", order=1,
        )
        proj = Project.objects.create(
            title="Circle Test", slug="circle-test",
            category=self.cat, description="Test.",
            image=SimpleUploadedFile("c.jpg", b"\xff\xd8\xff\xe0", content_type="image/jpeg"),
            visible=True,
        )
        # Render via the template tag directly
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image=proj.image, variant="avatar")
        self.assertIn("img-shape-circle", ctx["css_classes"])

    def test_db_variant_rounded_with_custom_radius(self):
        ImageVariant.objects.create(
            name="thumb", aspect_ratio="4:3", crop_mode="cover",
            shape="rounded", border_radius="12px", order=2,
        )
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image="/fake.jpg", variant="thumb")
        self.assertIn("border-radius: 12px", ctx["css_style"])
        self.assertNotIn("img-shape-rounded", ctx["css_classes"])

    def test_db_variant_object_position(self):
        ImageVariant.objects.create(
            name="top-focus", aspect_ratio="16:9", crop_mode="cover",
            object_position="50% 20%", order=3,
        )
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image="/fake.jpg", variant="top-focus")
        self.assertIn("object-position: 50% 20%", ctx["css_style"])

    def test_db_variant_background_color(self):
        ImageVariant.objects.create(
            name="contain-bg", aspect_ratio="16:9", crop_mode="contain",
            background_color="#f0f0f0", order=4,
        )
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image="/fake.jpg", variant="contain-bg")
        self.assertIn("object-fit: contain", ctx["css_style"])
        self.assertIn("background-color: #f0f0f0", ctx["css_style"])

    def test_db_variant_allow_zoom_false(self):
        ImageVariant.objects.create(
            name="no-zoom", aspect_ratio="4:3", crop_mode="cover",
            allow_zoom=False, order=5,
        )
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image="/fake.jpg", variant="no-zoom")
        self.assertNotIn("img-hover-scale", ctx["css_classes"])

    def test_shape_param_overrides_db_variant(self):
        ImageVariant.objects.create(
            name="rect-default", aspect_ratio="4:3", crop_mode="cover",
            shape="rect", order=6,
        )
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image="/fake.jpg", variant="rect-default", shape="circle")
        self.assertIn("img-shape-circle", ctx["css_classes"])

    def test_rect_shape_has_no_rounding(self):
        from portfolio.templatetags.portfolio_tags import responsive_image
        ctx = responsive_image(image="/fake.jpg", variant="card", shape="rect")
        self.assertNotIn("media-img--rounded", ctx["css_classes"])
        self.assertNotIn("img-shape-rounded", ctx["css_classes"])
        self.assertNotIn("img-shape-circle", ctx["css_classes"])


class HomepageHeroDBTests(TestCase):
    """Prove the homepage hero section is driven by SiteSetting."""

    def test_hero_title_from_sitesetting(self):
        SiteSetting.objects.create(hero_title="Unique Hero Headline 7x9q")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unique Hero Headline 7x9q")


class SiteSettingCSSVarsTests(TestCase):
    """Prove SiteSetting color fields render as CSS custom properties."""

    def test_primary_color_renders_in_css_vars(self):
        SiteSetting.objects.create(primary_color="#1a2b3c", hero_start_color="#4d5e6f")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "--primary: #1a2b3c")
        self.assertContains(response, "--hero-start: #4d5e6f")


class EducationEntryModelTests(TestCase):
    """Verify EducationEntry default ordering and visibility filtering."""

    def test_default_ordering_by_order_field(self):
        EducationEntry.objects.create(title="Second", institution="Uni B", order=2)
        EducationEntry.objects.create(title="First", institution="Uni A", order=1)
        EducationEntry.objects.create(title="Third", institution="Uni C", order=3)
        titles = list(EducationEntry.objects.values_list("title", flat=True))
        self.assertEqual(titles, ["First", "Second", "Third"])

    def test_visible_filter(self):
        EducationEntry.objects.create(title="Shown", institution="Uni", order=1, visible=True)
        EducationEntry.objects.create(title="Hidden", institution="Uni", order=2, visible=False)
        self.assertEqual(EducationEntry.objects.filter(visible=True).count(), 1)

    def test_str(self):
        e = EducationEntry(title="BS CS", institution="MIT")
        self.assertEqual(str(e), "BS CS — MIT")


class CertificationModelTests(TestCase):
    """Verify Certification default ordering and visibility filtering."""

    def test_default_ordering_by_order_field(self):
        Certification.objects.create(name="Second Cert", issuer="Org B", order=2)
        Certification.objects.create(name="First Cert", issuer="Org A", order=1)
        Certification.objects.create(name="Third Cert", issuer="Org C", order=3)
        names = list(Certification.objects.values_list("name", flat=True))
        self.assertEqual(names, ["First Cert", "Second Cert", "Third Cert"])

    def test_visible_filter(self):
        Certification.objects.create(name="Shown", issuer="Org", order=1, visible=True)
        Certification.objects.create(name="Hidden", issuer="Org", order=2, visible=False)
        self.assertEqual(Certification.objects.filter(visible=True).count(), 1)

    def test_str(self):
        c = Certification(name="AWS SAA", issuer="Amazon")
        self.assertEqual(str(c), "AWS SAA (Amazon)")


class EducationPageTests(TestCase):
    """Verify /education/ page rendering, ordering, visibility, and pagination."""

    def test_education_page_returns_200(self):
        response = self.client.get("/education/")
        self.assertEqual(response.status_code, 200)

    def test_education_rendered_order(self):
        EducationEntry.objects.create(title="Edu-Second", institution="U", order=2)
        EducationEntry.objects.create(title="Edu-First", institution="U", order=1)
        EducationEntry.objects.create(title="Edu-Third", institution="U", order=3)
        response = self.client.get("/education/")
        html = response.content.decode()
        pos1 = html.index("Edu-First")
        pos2 = html.index("Edu-Second")
        pos3 = html.index("Edu-Third")
        self.assertLess(pos1, pos2)
        self.assertLess(pos2, pos3)

    def test_hidden_education_not_shown(self):
        EducationEntry.objects.create(title="Visible-Edu", institution="U", order=1, visible=True)
        EducationEntry.objects.create(title="Hidden-Edu", institution="U", order=2, visible=False)
        response = self.client.get("/education/")
        self.assertContains(response, "Visible-Edu")
        self.assertNotContains(response, "Hidden-Edu")

    def test_hidden_certification_not_shown(self):
        Certification.objects.create(name="Visible-Cert", issuer="Org", order=1, visible=True)
        Certification.objects.create(name="Hidden-Cert", issuer="Org", order=2, visible=False)
        response = self.client.get("/certifications/")
        self.assertContains(response, "Visible-Cert")
        self.assertNotContains(response, "Hidden-Cert")

    def test_pagination_page_2(self):
        for i in range(12):
            EducationEntry.objects.create(title=f"Edu-{i:02d}", institution="U", order=i)
        response = self.client.get("/education/?page=2")
        self.assertEqual(response.status_code, 200)

    def test_pdf_attachment_shows_preview(self):
        entry = EducationEntry.objects.create(
            title="PDF-Entry", institution="U", order=1,
            attachment=SimpleUploadedFile("diploma.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
        )
        response = self.client.get("/education/")
        self.assertContains(response, "edu-pdf-preview")
        self.assertContains(response, f"/education/{entry.pk}/inline/")

    def test_education_preview_route_returns_200(self):
        entry = EducationEntry.objects.create(
            title="Preview-Entry", institution="U", order=1,
            attachment=SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
        )
        response = self.client.get(f"/education/{entry.pk}/preview/")
        self.assertEqual(response.status_code, 200)

    def test_education_pdf_inline_serves_pdf(self):
        entry = EducationEntry.objects.create(
            title="Inline-Entry", institution="U", order=1,
            attachment=SimpleUploadedFile("file.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
        )
        response = self.client.get(f"/education/{entry.pk}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_category_grouping_renders_headers(self):
        cat_a = Category.objects.create(name="Academic", slug="academic")
        cat_b = Category.objects.create(name="Professional", slug="professional")
        EducationEntry.objects.create(title="Edu-A", institution="U", order=1, category=cat_a)
        EducationEntry.objects.create(title="Edu-B", institution="U", order=2, category=cat_b)
        EducationEntry.objects.create(title="Edu-None", institution="U", order=3)
        response = self.client.get("/education/")
        self.assertContains(response, "Academic")
        self.assertContains(response, "Professional")
        self.assertContains(response, "Other")

    def test_json_ld_schema_present(self):
        EducationEntry.objects.create(title="Schema-Edu", institution="U", order=1)
        response = self.client.get("/education/")
        self.assertContains(response, 'application/ld+json')


class HomepageFeaturedProjectTests(TestCase):
    """Prove featured projects count is admin-configurable and grouped by category."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSetting.objects.create(
            hero_title="Test Hero",
            homepage_featured_projects_count=3,
        )
        cls.cat_a = Category.objects.create(name="Analytics", slug="analytics")
        cls.cat_b = Category.objects.create(name="Web Dev", slug="web-dev")
        # 5 featured + visible, across two categories
        for i in range(3):
            Project.objects.create(
                title=f"Proj-A{i}", slug=f"proj-a{i}", category=cls.cat_a,
                description="d", is_featured=True, visible=True, order=i,
            )
        for i in range(2):
            Project.objects.create(
                title=f"Proj-B{i}", slug=f"proj-b{i}", category=cls.cat_b,
                description="d", is_featured=True, visible=True, order=i,
            )
        # non-featured — should not appear
        Project.objects.create(
            title="NotFeatured", slug="not-featured", category=cls.cat_a,
            description="d", is_featured=False, visible=True, order=0,
        )
        # invisible featured — should not appear
        Project.objects.create(
            title="InvisibleFeatured", slug="invisible-featured", category=cls.cat_a,
            description="d", is_featured=True, visible=False, order=0,
        )

    def test_homepage_limits_featured_count(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # Only 3 of the 5 featured projects should appear
        shown = sum(1 for i in range(3) if f"Proj-A{i}" in html)
        shown += sum(1 for i in range(2) if f"Proj-B{i}" in html)
        self.assertEqual(shown, 3)

    def test_homepage_shows_category_badge(self):
        response = self.client.get("/")
        self.assertContains(response, "Analytics")

    def test_non_featured_excluded(self):
        response = self.client.get("/")
        self.assertNotContains(response, "NotFeatured")

    def test_invisible_featured_excluded(self):
        response = self.client.get("/")
        self.assertNotContains(response, "InvisibleFeatured")


class HomepageFeaturedCountLimitTests(TestCase):
    """Prove homepage_featured_projects_count limits displayed projects."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSetting.objects.create(
            hero_title="Blocks Test",
            homepage_featured_projects_count=1,
        )
        cls.cat_a = Category.objects.create(name="AlphaBlock", slug="alpha-block")
        cls.cat_b = Category.objects.create(name="BetaBlock", slug="beta-block")
        Project.objects.create(
            title="AlphaProj9x", slug="alpha-proj", category=cls.cat_a,
            description="d", is_featured=True, visible=True, order=0,
        )
        Project.objects.create(
            title="BetaProj9x", slug="beta-proj", category=cls.cat_b,
            description="d", is_featured=True, visible=True, order=1,
        )

    def test_only_one_featured_project_shown(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AlphaProj9x")
        self.assertNotContains(response, "BetaProj9x")


class ProjectAttachmentTests(TestCase):
    """Verify ProjectAttachment multi-file support and PDF preview routes."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Attach Cat", slug="attach-cat")
        cls.project = Project.objects.create(
            title="Attach Project", slug="attach-project",
            category=cls.cat, description="A project with attachments.",
            visible=True,
        )
        cls.pdf_att = ProjectAttachment.objects.create(
            project=cls.project, title="Design Doc",
            file=SimpleUploadedFile("design.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            order=1, visible=True,
        )
        cls.hidden_att = ProjectAttachment.objects.create(
            project=cls.project, title="Hidden File",
            file=SimpleUploadedFile("secret.pdf", b"%PDF-1.4 hidden", content_type="application/pdf"),
            order=2, visible=False,
        )
        cls.ext_att = ProjectAttachment.objects.create(
            project=cls.project, title="External Link",
            external_url="https://example.com/doc",
            order=3, visible=True,
        )
        cls.docx_att = ProjectAttachment.objects.create(
            project=cls.project, title="Word Doc",
            file=SimpleUploadedFile("notes.docx", b"PK\x03\x04 fake docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            order=4, visible=True,
        )

    def test_detail_shows_visible_attachment(self):
        response = self.client.get("/projects/attach-project/")
        self.assertContains(response, "Design Doc")

    def test_detail_hides_invisible_attachment(self):
        response = self.client.get("/projects/attach-project/")
        self.assertNotContains(response, "Hidden File")

    def test_detail_shows_external_link(self):
        response = self.client.get("/projects/attach-project/")
        self.assertContains(response, "https://example.com/doc")

    def test_preview_route_returns_200(self):
        response = self.client.get(f"/projects/attachments/{self.pdf_att.pk}/preview/")
        self.assertEqual(response.status_code, 200)

    def test_pdf_inline_serves_pdf(self):
        response = self.client.get(f"/projects/attachments/{self.pdf_att.pk}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_pdf_inline_sets_inline_disposition(self):
        response = self.client.get(f"/projects/attachments/{self.pdf_att.pk}/pdf/")
        disp = response["Content-Disposition"]
        self.assertTrue(disp.startswith("inline"))
        self.assertIn(".pdf", disp)

    def test_download_forces_attachment_disposition(self):
        response = self.client.get(f"/projects/attachments/{self.pdf_att.pk}/download/")
        self.assertEqual(response.status_code, 200)
        disp = response["Content-Disposition"]
        self.assertTrue(disp.startswith("attachment"))
        self.assertIn(".pdf", disp)

    def test_non_pdf_download_forces_attachment(self):
        response = self.client.get(f"/projects/attachments/{self.docx_att.pk}/download/")
        self.assertEqual(response.status_code, 200)
        disp = response["Content-Disposition"]
        self.assertTrue(disp.startswith("attachment"))
        self.assertIn(".docx", disp)

    def test_non_pdf_no_iframe_on_detail(self):
        response = self.client.get("/projects/attach-project/")
        html = response.content.decode()
        # The docx attachment should show Open button, not an iframe
        self.assertContains(response, "Word Doc")
        self.assertNotIn(f"/projects/attachments/{self.docx_att.pk}/pdf/", html)

    def test_pdf_has_iframe_on_detail(self):
        response = self.client.get("/projects/attach-project/")
        self.assertContains(response, f"/projects/attachments/{self.pdf_att.pk}/pdf/")
        self.assertContains(response, "<iframe")

    def test_hidden_attachment_returns_404(self):
        response = self.client.get(f"/projects/attachments/{self.hidden_att.pk}/preview/")
        self.assertEqual(response.status_code, 404)

    def test_hidden_download_returns_404(self):
        response = self.client.get(f"/projects/attachments/{self.hidden_att.pk}/download/")
        self.assertEqual(response.status_code, 404)

    def test_is_pdf_property(self):
        self.assertTrue(self.pdf_att.is_pdf)
        self.assertFalse(self.docx_att.is_pdf)
        self.assertFalse(self.ext_att.is_pdf)

    def test_str_with_title(self):
        self.assertEqual(str(self.pdf_att), "Design Doc")

    def test_str_without_title(self):
        att = ProjectAttachment(external_url="https://example.com")
        self.assertEqual(str(att), "https://example.com")


class MultiTypePreviewTests(TestCase):
    """Verify multi-file-type preview: text, image, audio, video, fallback, and legacy endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Preview Cat", slug="preview-cat")
        cls.project = Project.objects.create(
            title="Preview Project", slug="preview-project",
            category=cls.cat, description="Multi-type preview test.",
            visible=True,
        )
        cls.py_att = ProjectAttachment.objects.create(
            project=cls.project, title="Script File",
            file=SimpleUploadedFile("helper.py", b"print('hello')\n", content_type="text/x-python"),
            order=1, visible=True,
        )
        cls.img_att = ProjectAttachment.objects.create(
            project=cls.project, title="Screenshot",
            file=SimpleUploadedFile("screen.png", b"\x89PNG\r\n\x1a\n fake", content_type="image/png"),
            order=2, visible=True,
        )
        cls.docx_att = ProjectAttachment.objects.create(
            project=cls.project, title="Report",
            file=SimpleUploadedFile("report.docx", b"PK\x03\x04 fake", content_type="application/octet-stream"),
            order=3, visible=True,
        )
        # Legacy attachment on a separate project
        cls.legacy_proj = Project.objects.create(
            title="Legacy Project", slug="legacy-project",
            category=cls.cat, description="Has a legacy attachment.",
            attachment=SimpleUploadedFile("old_report.pdf", b"%PDF-1.4 legacy", content_type="application/pdf"),
            visible=True,
        )

    # --- preview_kind property ---
    def test_preview_kind_text(self):
        self.assertEqual(self.py_att.preview_kind, "text")

    def test_preview_kind_image(self):
        self.assertEqual(self.img_att.preview_kind, "image")

    def test_preview_kind_none(self):
        self.assertEqual(self.docx_att.preview_kind, "none")

    # --- text inline endpoint ---
    def test_text_inline_returns_200(self):
        response = self.client.get(f"/projects/attachments/{self.py_att.pk}/text/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])

    def test_text_inline_contains_content(self):
        response = self.client.get(f"/projects/attachments/{self.py_att.pk}/text/")
        self.assertContains(response, "print")

    def test_text_inline_404_for_non_text(self):
        response = self.client.get(f"/projects/attachments/{self.img_att.pk}/text/")
        self.assertEqual(response.status_code, 404)

    # --- template branching ---
    def test_detail_hides_code_attachment(self):
        """Code-file attachments (.py etc.) are fully hidden from project detail."""
        response = self.client.get("/projects/preview-project/")
        self.assertNotContains(response, f"/projects/attachments/{self.py_att.pk}/text/")
        self.assertNotContains(response, f"/projects/attachments/{self.py_att.pk}/download/")

    def test_detail_shows_image_tag(self):
        response = self.client.get("/projects/preview-project/")
        html = response.content.decode()
        self.assertIn("<img", html)
        self.assertIn("Screenshot", html)

    def test_detail_hides_fallback_for_docx(self):
        """Non-previewable attachments no longer show a fallback message."""
        response = self.client.get("/projects/preview-project/")
        self.assertNotContains(response, "Preview not available")

    # --- legacy endpoints ---
    def test_legacy_download_returns_attachment_disposition(self):
        response = self.client.get(f"/projects/legacy/{self.legacy_proj.pk}/download/")
        self.assertEqual(response.status_code, 200)
        disp = response["Content-Disposition"]
        self.assertTrue(disp.startswith("attachment"))
        self.assertIn(".pdf", disp)

    def test_legacy_inline_returns_pdf(self):
        response = self.client.get(f"/projects/legacy/{self.legacy_proj.pk}/inline/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_legacy_detail_shows_legacy_attachment(self):
        response = self.client.get("/projects/legacy-project/")
        self.assertContains(response, "Attachment")
        self.assertContains(response, f"/projects/legacy/{self.legacy_proj.pk}/download/")

    def test_legacy_download_404_for_no_attachment(self):
        proj = Project.objects.create(
            title="NoAtt", slug="no-att", category=self.cat,
            description="d", visible=True,
        )
        response = self.client.get(f"/projects/legacy/{proj.pk}/download/")
        self.assertEqual(response.status_code, 404)


class CategoryImageTests(TestCase):
    """Verify category images render in project list and homepage, with fallback."""

    @classmethod
    def setUpTestData(cls):
        cls.cat_with_img = Category.objects.create(
            name="ImgCat7z", slug="imgcat7z",
            image=SimpleUploadedFile("cat.jpg", b"\xff\xd8\xff\xe0", content_type="image/jpeg"),
        )
        cls.cat_no_img = Category.objects.create(name="PlainCat7z", slug="plaincat7z")
        Project.objects.create(
            title="ImgCatProj", slug="imgcatproj",
            category=cls.cat_with_img, description="d",
            visible=True, is_featured=True, order=0,
        )
        Project.objects.create(
            title="PlainCatProj", slug="plaincatproj",
            category=cls.cat_no_img, description="d",
            visible=True, is_featured=True, order=1,
        )

    def test_project_list_renders_category_icon(self):
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "category-icon")
        self.assertContains(response, "ImgCat7z")

    def test_project_list_no_error_without_category_image(self):
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PlainCat7z")

    def test_homepage_renders_category_name_on_card(self):
        SiteSetting.objects.create(homepage_featured_projects_count=10)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ImgCat7z")

    def test_homepage_no_error_without_category_image(self):
        SiteSetting.objects.create(homepage_featured_projects_count=10)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PlainCat7z")


class ProjectListPaginationTests(TestCase):
    """Verify project list pagination controls render and function."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="PagCat", slug="pagcat")
        for i in range(10):
            Project.objects.create(
                title=f"PagProj-{i:02d}", slug=f"pagproj-{i:02d}",
                category=cls.cat, description="d", visible=True, order=i,
            )

    def test_page1_has_pagination_and_nine_items(self):
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pagination")
        self.assertContains(response, "?page=2")
        # Page 1 shows first 9 (order 0-8), not the 10th (order 9)
        self.assertContains(response, "PagProj-00")
        self.assertContains(response, "PagProj-08")
        self.assertNotContains(response, "PagProj-09")

    def test_page2_shows_remaining_project(self):
        response = self.client.get("/projects/?page=2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PagProj-09")


class HomepageFeaturedGridTests(TestCase):
    """Verify featured projects render in a single grid regardless of categories."""

    @classmethod
    def setUpTestData(cls):
        cls.settings = SiteSetting.objects.create(homepage_featured_projects_count=3)
        cats = [
            Category.objects.create(name=f"GridCat{i}", slug=f"gridcat{i}")
            for i in range(3)
        ]
        for i, cat in enumerate(cats):
            Project.objects.create(
                title=f"GridProj{i}", slug=f"gridproj{i}",
                category=cat, description="d",
                is_featured=True, visible=True, order=i,
            )

    def test_three_cards_in_single_featured_grid(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # Exactly one featured-grid div in the HTML body
        grid_div = 'class="featured-grid'
        self.assertEqual(html.count(grid_div), 1)
        # Extract from featured-grid div to end of its section
        start = html.index(grid_div)
        section_end = html.index("</section>", start)
        grid_section = html[start:section_end]
        # All 3 project cards inside the single grid
        self.assertEqual(grid_section.count("card-title"), 3)
        self.assertIn("GridProj0", grid_section)
        self.assertIn("GridProj1", grid_section)
        self.assertIn("GridProj2", grid_section)


class NotebookPreviewTests(TestCase):
    """Verify .ipynb rich preview rendering and oversize fallback."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="NB Cat", slug="nb-cat")
        cls.project = Project.objects.create(
            title="NB Project", slug="nb-project",
            category=cls.cat, description="Notebook test.", visible=True,
        )
        notebook = {
            "cells": [
                {"cell_type": "markdown", "source": ["# Hello Notebook"], "metadata": {}},
                {"cell_type": "code", "source": ["print('world')"], "metadata": {}, "outputs": [
                    {"output_type": "stream", "name": "stdout", "text": ["world\n"]}
                ]},
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2,
        }
        cls.nb_att = ProjectAttachment.objects.create(
            project=cls.project, title="Analysis Notebook",
            file=SimpleUploadedFile("analysis.ipynb", json.dumps(notebook).encode(), content_type="application/json"),
            order=1, visible=True,
        )

    def test_notebook_endpoint_returns_200_html(self):
        response = self.client.get(f"/projects/attachments/{self.nb_att.pk}/notebook/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])

    def test_notebook_contains_cell_content(self):
        response = self.client.get(f"/projects/attachments/{self.nb_att.pk}/notebook/")
        self.assertContains(response, "Hello Notebook")
        self.assertContains(response, "print(")
        self.assertContains(response, "world")

    def test_notebook_preview_kind(self):
        self.assertEqual(self.nb_att.preview_kind, "notebook")

    def test_detail_shows_notebook_iframe(self):
        response = self.client.get("/projects/nb-project/")
        self.assertContains(response, f"/projects/attachments/{self.nb_att.pk}/notebook/")

    def test_oversize_notebook_falls_back_to_text(self):
        big_cell = {"cell_type": "code", "source": ["x" * 250_000], "metadata": {}, "outputs": []}
        big_nb = {"cells": [big_cell], "metadata": {}, "nbformat": 4, "nbformat_minor": 2}
        big_att = ProjectAttachment.objects.create(
            project=self.project, title="Big Notebook",
            file=SimpleUploadedFile("big.ipynb", json.dumps(big_nb).encode(), content_type="application/json"),
            order=10, visible=True,
        )
        response = self.client.get(f"/projects/attachments/{big_att.pk}/notebook/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])

    def test_notebook_endpoint_404_for_non_ipynb(self):
        cat = Category.objects.create(name="NB2 Cat", slug="nb2-cat")
        proj = Project.objects.create(
            title="NB2 Project", slug="nb2-project",
            category=cat, description="d", visible=True,
        )
        txt_att = ProjectAttachment.objects.create(
            project=proj, title="Not a notebook",
            file=SimpleUploadedFile("readme.txt", b"hello", content_type="text/plain"),
            order=1, visible=True,
        )
        response = self.client.get(f"/projects/attachments/{txt_att.pk}/notebook/")
        self.assertEqual(response.status_code, 404)


class AdminProjectAttachmentTests(TestCase):
    """Verify admin registration and inline formset for attachments."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser("admin", "admin@test.com", "testpass123")
        cls.cat = Category.objects.create(name="Admin Cat", slug="admin-cat")
        cls.project = Project.objects.create(
            title="Admin Project", slug="admin-project",
            category=cls.cat, description="d", visible=True,
        )

    def setUp(self):
        self.client.login(username="admin", password="testpass123")

    def test_project_change_page_shows_attachment_inline(self):
        response = self.client.get(f"/admin/portfolio/project/{self.project.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project attachments")

    def test_projectattachment_changelist_loads(self):
        response = self.client.get("/admin/portfolio/projectattachment/")
        self.assertEqual(response.status_code, 200)


class SeedIdempotencyTests(TestCase):
    """Verify seed script fills blanks but never overwrites existing content."""

    def _run_seed(self):
        import io
        from contextlib import redirect_stdout
        from pathlib import Path as P
        script = P(__file__).resolve().parent.parent / "scripts" / "seed_portfolio_content.py"
        code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
        with redirect_stdout(io.StringIO()):
            exec(code, {"__file__": str(script), "__name__": "__seed__"})

    def test_seed_preserves_custom_hero_title(self):
        self._run_seed()
        site = SiteSetting.objects.get(pk=1)
        site.hero_title = "CUSTOM"
        site.save()
        self._run_seed()
        site.refresh_from_db()
        self.assertEqual(site.hero_title, "CUSTOM")

    def test_seed_fills_blank_bio_short(self):
        self._run_seed()
        site = SiteSetting.objects.get(pk=1)
        site.bio_short = ""
        site.save()
        self._run_seed()
        site.refresh_from_db()
        self.assertNotEqual(site.bio_short, "")


class CategoryPlaceholderTests(TestCase):
    """Verify category placeholder generator is idempotent and fills blanks."""

    def _run_generator(self):
        import io
        from contextlib import redirect_stdout
        from pathlib import Path as P
        script = P(__file__).resolve().parent.parent / "scripts" / "generate_category_placeholders.py"
        code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
        with redirect_stdout(io.StringIO()):
            exec(code, {"__file__": str(script), "__name__": "__main__"})

    def test_null_image_gets_placeholder(self):
        cat = Category.objects.create(name="PlaceholderTest", slug="placeholdertest")
        self.assertFalse(bool(cat.image))
        self._run_generator()
        cat.refresh_from_db()
        self.assertTrue(bool(cat.image))
        self.assertIn("placeholdertest_placeholder", cat.image.name)

    def test_running_twice_does_not_overwrite(self):
        cat = Category.objects.create(name="IdempotentTest", slug="idempotenttest")
        self._run_generator()
        cat.refresh_from_db()
        first_value = cat.image.name
        self.assertTrue(bool(first_value))
        self._run_generator()
        cat.refresh_from_db()
        self.assertEqual(cat.image.name, first_value)


class ResumePrimaryEnforcementTests(TestCase):
    """Verify only one resume per category can be primary."""

    def test_setting_primary_demotes_existing(self):
        r1 = Resume.objects.create(
            title="Resume A", category="general", is_primary=True,
            file=SimpleUploadedFile("a.pdf", b"%PDF-1.4 test"),
        )
        r2 = Resume.objects.create(
            title="Resume B", category="general", is_primary=True,
            file=SimpleUploadedFile("b.pdf", b"%PDF-1.4 test"),
        )
        r1.refresh_from_db()
        self.assertFalse(r1.is_primary)
        self.assertTrue(r2.is_primary)

    def test_different_categories_both_primary(self):
        r1 = Resume.objects.create(
            title="Resume Gen", category="general", is_primary=True,
            file=SimpleUploadedFile("gen.pdf", b"%PDF-1.4 test"),
        )
        r2 = Resume.objects.create(
            title="Resume Fin", category="finance", is_primary=True,
            file=SimpleUploadedFile("fin.pdf", b"%PDF-1.4 test"),
        )
        r1.refresh_from_db()
        self.assertTrue(r1.is_primary)
        self.assertTrue(r2.is_primary)

    def test_non_primary_does_not_demote(self):
        r1 = Resume.objects.create(
            title="Resume P", category="general", is_primary=True,
            file=SimpleUploadedFile("p.pdf", b"%PDF-1.4 test"),
        )
        Resume.objects.create(
            title="Resume NP", category="general", is_primary=False,
            file=SimpleUploadedFile("np.pdf", b"%PDF-1.4 test"),
        )
        r1.refresh_from_db()
        self.assertTrue(r1.is_primary)


class LayoutProfileTests(TestCase):
    """Verify LayoutProfile model, resolver, admin action, and constraints."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser("lpadmin", "lp@test.com", "testpass123")
        cls.cat = Category.objects.create(name="LP Cat", slug="lp-cat")

    def test_site_default_resolution(self):
        lp = LayoutProfile.objects.create(name="Default Profile", slug="default-profile", is_site_default=True)
        self.assertEqual(resolve_active_profile(), lp)

    def test_category_override_beats_default(self):
        LayoutProfile.objects.create(name="Site Default", slug="site-default", is_site_default=True)
        override = LayoutProfile.objects.create(name="Cat Override", slug="cat-override", category=self.cat)
        self.assertEqual(resolve_active_profile(category=self.cat), override)

    def test_no_profile_returns_none(self):
        self.assertIsNone(resolve_active_profile())

    def test_setting_site_default_demotes_existing(self):
        lp1 = LayoutProfile.objects.create(name="First LP", slug="first-lp", is_site_default=True)
        lp2 = LayoutProfile.objects.create(name="Second LP", slug="second-lp", is_site_default=True)
        lp1.refresh_from_db()
        self.assertFalse(lp1.is_site_default)
        self.assertTrue(lp2.is_site_default)

    def test_unique_category_constraint(self):
        from django.db import IntegrityError
        LayoutProfile.objects.create(name="Cat A", slug="cat-a", category=self.cat)
        with self.assertRaises(IntegrityError):
            LayoutProfile.objects.create(name="Cat B", slug="cat-b", category=self.cat)

    def test_make_site_default_admin_action(self):
        self.client.login(username="lpadmin", password="testpass123")
        lp1 = LayoutProfile.objects.create(name="Old Default", slug="old-default", is_site_default=True)
        lp2 = LayoutProfile.objects.create(name="New Default", slug="new-default")
        response = self.client.post(
            "/admin/portfolio/layoutprofile/",
            {"action": "make_site_default", "_selected_action": [str(lp2.pk)]},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        lp1.refresh_from_db()
        lp2.refresh_from_db()
        self.assertFalse(lp1.is_site_default)
        self.assertTrue(lp2.is_site_default)

    def test_str_with_default_flag(self):
        lp = LayoutProfile(name="Modern", is_site_default=True)
        self.assertIn("[default]", str(lp))

    def test_str_with_category(self):
        lp = LayoutProfile(name="Cat Layout", category=self.cat)
        self.assertIn("LP Cat", str(lp))

    def test_context_has_active_profile(self):
        LayoutProfile.objects.create(
            name="Site Profile", slug="site-profile",
            is_site_default=True, template_variant="modern_saas",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["template_variant"], "modern_saas")

    def test_context_default_when_no_profile(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["template_variant"], "default")
        self.assertIsNone(response.context["active_profile"])

    def test_body_has_variant_data_attribute(self):
        LayoutProfile.objects.create(
            name="SaaS Profile", slug="saas-profile",
            is_site_default=True, template_variant="modern_saas",
        )
        response = self.client.get("/")
        self.assertContains(response, 'data-variant="modern_saas"')
        self.assertContains(response, 'variant-modern_saas')

    def test_layoutprofile_changelist_has_expected_columns(self):
        self.client.login(username="lpadmin", password="testpass123")
        LayoutProfile.objects.create(name="Col Test", slug="col-test")
        response = self.client.get("/admin/portfolio/layoutprofile/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for col in ("Scope", "Slug", "Template variant", "Theme mode", "Accent theme"):
            self.assertIn(col, html)

    def test_make_site_default_action_sets_only_one_true(self):
        self.client.login(username="lpadmin", password="testpass123")
        lp1 = LayoutProfile.objects.create(name="LP1", slug="lp1", is_site_default=True)
        lp2 = LayoutProfile.objects.create(name="LP2", slug="lp2")
        lp3 = LayoutProfile.objects.create(name="LP3", slug="lp3")
        self.client.post(
            "/admin/portfolio/layoutprofile/",
            {"action": "make_site_default", "_selected_action": [str(lp3.pk)]},
            follow=True,
        )
        self.assertEqual(LayoutProfile.objects.filter(is_site_default=True).count(), 1)
        lp3.refresh_from_db()
        self.assertTrue(lp3.is_site_default)

    def test_activate_action_enforces_single_selection(self):
        self.client.login(username="lpadmin", password="testpass123")
        lp1 = LayoutProfile.objects.create(name="Act1", slug="act1")
        lp2 = LayoutProfile.objects.create(name="Act2", slug="act2")
        response = self.client.post(
            "/admin/portfolio/layoutprofile/",
            {"action": "activate_and_make_site_default", "_selected_action": [str(lp1.pk), str(lp2.pk)]},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        # Neither should be default — multi-select rejected
        self.assertEqual(LayoutProfile.objects.filter(is_site_default=True).count(), 0)

    def test_scope_display_logic(self):
        from portfolio.admin import LayoutProfileAdmin
        ma = LayoutProfileAdmin(LayoutProfile, django_admin.site)
        # Site default, no category
        lp_default = LayoutProfile(name="D", is_site_default=True, category=None)
        self.assertIn("Site Default", ma.scope_display(lp_default))
        # Category override
        lp_cat = LayoutProfile(name="C", is_site_default=False, category=self.cat)
        self.assertIn("LP Cat", ma.scope_display(lp_cat))
        # Inactive site profile
        lp_inactive = LayoutProfile(name="I", is_site_default=False, category=None)
        self.assertEqual(ma.scope_display(lp_inactive), "Inactive Site Profile")

    def test_all_ten_variant_choices_exist_and_model_accepts_each(self):
        from portfolio.models import TEMPLATE_VARIANT_CHOICES
        slugs = [slug for slug, _ in TEMPLATE_VARIANT_CHOICES]
        expected = [
            "default", "modern_saas", "executive_minimal", "data_lab",
            "split_screen", "magazine_editorial", "card_dashboard",
            "glass_modern", "bold_branding", "timeline_pro", "technical_research",
        ]
        self.assertEqual(slugs, expected)
        # Verify model accepts every slug without error
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            if slug == "default":
                continue
            lp = LayoutProfile(
                name=f"Test {label}", slug=f"test-{slug}",
                template_variant=slug,
            )
            lp.full_clean()


class SeedNavAndContentTests(TestCase):
    """Verify seed creates NavItems, cert attachments, and education entries."""

    def _run_seed(self):
        import io
        from contextlib import redirect_stdout
        from pathlib import Path as P
        script = P(__file__).resolve().parent.parent / "scripts" / "seed_portfolio_content.py"
        code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
        with redirect_stdout(io.StringIO()):
            exec(code, {"__file__": str(script), "__name__": "__seed__"})

    def test_seed_nav_dropdown_has_education_and_certifications(self):
        self._run_seed()
        children = dict(
            NavItem.objects.filter(parent__title="Portfolio", visible=True)
            .values_list("title", "url")
        )
        self.assertIn("Education", children)
        self.assertEqual(children["Education"], "/education/")
        self.assertIn("Certifications", children)
        self.assertEqual(children["Certifications"], "/certifications/")

    def test_seed_nav_top_level_has_education_and_certifications(self):
        self._run_seed()
        top = dict(
            NavItem.objects.filter(parent=None, visible=True)
            .values_list("title", "url")
        )
        # Education + Certifications must be top-level
        self.assertIn("Education", top)
        self.assertEqual(top["Education"], "/education/")
        self.assertIn("Certifications", top)
        self.assertEqual(top["Certifications"], "/certifications/")
        # Projects must also be top-level
        self.assertIn("Projects", top)
        self.assertEqual(top["Projects"], "/projects/")
        # Resume must NOT be top-level (dropdown-only)
        self.assertNotIn("Resume", top)

    def test_seed_nav_github_linkedin_top_level(self):
        self._run_seed()
        top = dict(
            NavItem.objects.filter(parent=None, visible=True)
            .values_list("title", "url")
        )
        self.assertIn("GitHub", top)
        self.assertTrue(top["GitHub"].startswith("https://"))
        self.assertIn("LinkedIn", top)
        self.assertTrue(top["LinkedIn"].startswith("https://"))

    def test_seed_nav_github_linkedin_in_portfolio_dropdown(self):
        self._run_seed()
        children = dict(
            NavItem.objects.filter(parent__title="Portfolio", visible=True)
            .values_list("title", "url")
        )
        self.assertIn("GitHub", children)
        self.assertTrue(children["GitHub"].startswith("https://"))
        self.assertIn("LinkedIn", children)
        self.assertTrue(children["LinkedIn"].startswith("https://"))

    def test_seed_nav_top_level_ordering(self):
        """Top-level nav order is exactly: Home, Projects, Portfolio, Education, …"""
        self._run_seed()
        actual = list(
            NavItem.objects.filter(parent=None, visible=True)
            .order_by("order")
            .values_list("title", flat=True)
        )
        expected = [
            "Home", "Portfolio", "Projects", "Education", "Certifications",
            "GitHub", "LinkedIn", "About", "Contact",
        ]
        self.assertEqual(actual, expected)

    def test_seed_nav_no_duplicate_top_level(self):
        self._run_seed()
        self._run_seed()  # run twice to prove idempotence
        from collections import Counter
        titles = list(
            NavItem.objects.filter(parent=None)
            .values_list("title", flat=True)
        )
        dupes = {t: c for t, c in Counter(titles).items() if c > 1}
        self.assertEqual(dupes, {}, f"Duplicate top-level NavItems: {dupes}")

    def test_seed_certifications_have_attachments(self):
        self._run_seed()
        certs = Certification.objects.all()
        self.assertEqual(certs.count(), 3)
        for cert in certs:
            self.assertTrue(bool(cert.attachment), f"{cert.name} missing attachment")

    def test_seed_education_institutions_exist(self):
        self._run_seed()
        institutions = set(EducationEntry.objects.values_list("institution", flat=True))
        self.assertIn("Kennesaw State University", institutions)
        self.assertIn("University of Alabama", institutions)

    def test_seed_education_have_images(self):
        self._run_seed()
        for edu in EducationEntry.objects.all():
            self.assertTrue(bool(edu.image), f"{edu.institution} missing image")

    def test_seed_education_have_attachments(self):
        self._run_seed()
        for edu in EducationEntry.objects.all():
            self.assertTrue(bool(edu.attachment), f"{edu.institution} missing attachment")

    def test_seed_education_page_shows_image_and_inline(self):
        self._run_seed()
        response = self.client.get("/education/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # At least one <img> thumbnail from entry.image
        self.assertIn("<img", html)
        # At least one /education/<pk>/inline/ iframe for text preview
        self.assertRegex(html, r"/education/\d+/inline/")


class CertificationInlinePreviewTests(TestCase):
    """Verify certification inline endpoint and education page iframe integration."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="CertInline Cat", slug="certinline-cat")
        cls.cert = Certification.objects.create(
            name="Inline Test Cert", issuer="Test Org",
            category=cls.cat,
            attachment=SimpleUploadedFile("test_cert.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            visible=True, order=0,
        )

    def test_inline_returns_200_with_inline_disposition(self):
        response = self.client.get(f"/certifications/{self.cert.pk}/inline/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Disposition"].startswith("inline"))

    def test_certifications_page_iframe_uses_inline(self):
        response = self.client.get("/certifications/")
        self.assertContains(response, f"/certifications/{self.cert.pk}/inline/")

    def test_preview_returns_200(self):
        response = self.client.get(f"/certifications/{self.cert.pk}/preview/")
        self.assertEqual(response.status_code, 200)


class SeparatePagesTests(TestCase):
    """Verify /education/ and /certifications/ are independent pages."""

    @classmethod
    def setUpTestData(cls):
        cls.edu = EducationEntry.objects.create(
            title="Separate-Edu", institution="Uni", order=1, visible=True,
        )
        cls.cert = Certification.objects.create(
            name="Separate-Cert", issuer="Org", order=1, visible=True,
        )

    def test_education_page_does_not_contain_certifications_header(self):
        response = self.client.get("/education/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Separate-Edu")
        self.assertNotContains(response, "Separate-Cert")

    def test_certifications_page_returns_200_with_cert(self):
        response = self.client.get("/certifications/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Separate-Cert")
        self.assertNotContains(response, "Separate-Edu")

    def test_certifications_page_uses_own_template(self):
        response = self.client.get("/certifications/")
        self.assertTemplateUsed(response, "portfolio/certifications.html")

    def test_certifications_page_has_json_ld(self):
        response = self.client.get("/certifications/")
        self.assertContains(response, "application/ld+json")


class EducationInlinePreviewTests(TestCase):
    """Verify education inline endpoint and multi-type preview on page."""

    @classmethod
    def setUpTestData(cls):
        cls.pdf_entry = EducationEntry.objects.create(
            title="PDF-Edu", institution="U", order=1,
            attachment=SimpleUploadedFile("diploma.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            visible=True,
        )
        cls.txt_entry = EducationEntry.objects.create(
            title="Txt-Edu", institution="U", order=2,
            attachment=SimpleUploadedFile("notes.txt", b"Some notes here", content_type="text/plain"),
            visible=True,
        )
        cls.img_entry = EducationEntry.objects.create(
            title="Img-Edu", institution="U", order=3,
            attachment=SimpleUploadedFile("photo.png", b"\x89PNG\r\n\x1a\n fake", content_type="image/png"),
            visible=True,
        )

    def test_inline_pdf_returns_200_with_inline_disposition(self):
        response = self.client.get(f"/education/{self.pdf_entry.pk}/inline/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline"))

    def test_inline_text_returns_200(self):
        response = self.client.get(f"/education/{self.txt_entry.pk}/inline/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])

    def test_inline_image_returns_200(self):
        response = self.client.get(f"/education/{self.img_entry.pk}/inline/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], "inline")

    def test_inline_no_attachment_returns_404(self):
        entry = EducationEntry.objects.create(
            title="No-Att", institution="U", order=10, visible=True,
        )
        response = self.client.get(f"/education/{entry.pk}/inline/")
        self.assertEqual(response.status_code, 404)

    def test_education_page_pdf_iframe_uses_inline(self):
        response = self.client.get("/education/")
        self.assertContains(response, f"/education/{self.pdf_entry.pk}/inline/")

    def test_education_page_text_iframe_uses_inline(self):
        response = self.client.get("/education/")
        self.assertContains(response, f"/education/{self.txt_entry.pk}/inline/")

    def test_download_forces_attachment_disposition(self):
        response = self.client.get(f"/education/{self.pdf_entry.pk}/download/")
        self.assertEqual(response.status_code, 200)
        disp = response["Content-Disposition"]
        self.assertTrue(disp.startswith("attachment"))

    def test_download_no_attachment_returns_404(self):
        entry = EducationEntry.objects.create(
            title="No-Att-DL", institution="U", order=11, visible=True,
        )
        response = self.client.get(f"/education/{entry.pk}/download/")
        self.assertEqual(response.status_code, 404)


class EducationPlaceholderTests(TestCase):
    """Verify education placeholder generator is idempotent and fills blanks."""

    def _run_generator(self):
        import io
        from contextlib import redirect_stdout
        from pathlib import Path as P
        script = P(__file__).resolve().parent.parent / "scripts" / "generate_education_placeholders.py"
        code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
        with redirect_stdout(io.StringIO()):
            exec(code, {"__file__": str(script), "__name__": "__main__"})

    def test_null_image_gets_placeholder(self):
        entry = EducationEntry.objects.create(
            title="BS CS", institution="Placeholder Uni", order=1,
        )
        self.assertFalse(bool(entry.image))
        self._run_generator()
        entry.refresh_from_db()
        self.assertTrue(bool(entry.image))
        self.assertIn("placeholder", entry.image.name)

    def test_running_twice_does_not_overwrite(self):
        entry = EducationEntry.objects.create(
            title="MS DS", institution="Idempotent Uni", order=2,
        )
        self._run_generator()
        entry.refresh_from_db()
        first_value = entry.image.name
        self.assertTrue(bool(first_value))
        self._run_generator()
        entry.refresh_from_db()
        self.assertEqual(entry.image.name, first_value)


class DesignTokenTests(TestCase):
    """Verify design-token CSS injection, fallback, image overrides, and admin form."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser("dtadmin", "dt@test.com", "testpass123")
        cls.ss = SiteSetting.objects.create(
            primary_color="#112233",
            text_color="#0f172a",
        )

    def test_layoutprofile_token_css_vars_present_on_homepage(self):
        """When a LayoutProfile has token colors, those CSS vars appear on the page."""
        LayoutProfile.objects.create(
            name="Token Profile", slug="token-profile",
            is_site_default=True,
            accent_color="#ff0000",
            bg_color="#00ff00",
            surface_color="#0000ff",
            token_text_color="#111111",
            muted_text_color="#999999",
            border_color="#cccccc",
        )
        response = self.client.get(reverse("portfolio:home"))
        content = response.content.decode()
        self.assertIn("--accent: #ff0000;", content)
        self.assertIn("--bg: #00ff00;", content)
        self.assertIn("--surface: #0000ff;", content)
        self.assertIn("--text: #111111;", content)
        self.assertIn("--text-muted: #999999;", content)
        self.assertIn("--border: #cccccc;", content)

    def test_layoutprofile_token_fallback_to_sitesetting(self):
        """When LayoutProfile has no tokens, the default SiteSetting CSS vars remain."""
        LayoutProfile.objects.create(
            name="Empty Token", slug="empty-token", is_site_default=True,
        )
        response = self.client.get(reverse("portfolio:home"))
        content = response.content.decode()
        # SiteSetting primary_color should still render via existing :root block
        self.assertIn("#112233", content)
        # Token vars should NOT appear since fields are blank
        self.assertNotIn("--accent:", content)

    def test_layoutprofile_hero_headshot_override_used(self):
        """When LayoutProfile provides hero/headshot images, they appear in context."""
        hero = SimpleUploadedFile("hero.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, content_type="image/png")
        headshot = SimpleUploadedFile("head.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, content_type="image/png")
        lp = LayoutProfile.objects.create(
            name="Image Token", slug="image-token", is_site_default=True,
            hero_image=hero, headshot_image=headshot,
        )
        response = self.client.get(reverse("portfolio:home"))
        ctx = response.context
        self.assertEqual(ctx["resolved_hero_image"], lp.hero_image)
        self.assertEqual(ctx["resolved_headshot_image"], lp.headshot_image)

    def test_layoutprofile_admin_form_contains_token_fields(self):
        """The LayoutProfile admin change page contains the Design Tokens fieldsets."""
        self.client.login(username="dtadmin", password="testpass123")
        lp = LayoutProfile.objects.create(name="Admin Token", slug="admin-token")
        response = self.client.get(f"/admin/portfolio/layoutprofile/{lp.pk}/change/")
        content = response.content.decode()
        for field in ("accent_color", "bg_color", "surface_color", "token_text_color",
                      "muted_text_color", "border_color", "hero_image", "headshot_image",
                      "font_stack", "type_scale"):
            self.assertIn(f'name="{field}"', content, f"Missing field: {field}")


class DataLabVariantTests(TestCase):
    """Verify the data_lab variant CSS is included when active."""

    def test_data_lab_variant_css_included_on_homepage(self):
        """When active_profile.template_variant='data_lab', homepage includes data_lab CSS."""
        LayoutProfile.objects.create(
            name="Data Lab", slug="data-lab",
            is_site_default=True,
            template_variant="data_lab",
        )
        response = self.client.get(reverse("portfolio:home"))
        content = response.content.decode()
        self.assertIn("variant-data_lab", content)
        self.assertIn("body.variant-data_lab", content)
        self.assertIn("--dl-accent", content)


class SeedLayoutProfileTests(TestCase):
    """Verify seed script creates one LayoutProfile per variant."""

    def _run_seed(self):
        import io
        from contextlib import redirect_stdout
        from pathlib import Path as P
        script = P(__file__).resolve().parent.parent / "scripts" / "seed_portfolio_content.py"
        code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
        with redirect_stdout(io.StringIO()):
            exec(code, {"__file__": str(script), "__name__": "__main__"})

    def test_seed_creates_one_profile_per_variant(self):
        self._run_seed()
        self.assertEqual(
            LayoutProfile.objects.count(),
            len(TEMPLATE_VARIANT_CHOICES),
        )
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            self.assertTrue(
                LayoutProfile.objects.filter(slug=f"variant-{slug}").exists(),
                f"Missing profile for variant: {slug}",
            )

    def test_seed_exactly_one_site_default(self):
        self._run_seed()
        defaults = LayoutProfile.objects.filter(is_site_default=True)
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.first().template_variant, "default")

    def test_seed_idempotent_preserves_customized_tokens(self):
        self._run_seed()
        lp = LayoutProfile.objects.get(slug="variant-data_lab")
        lp.accent_color = "#ff00ff"
        lp.save(update_fields=["accent_color"])
        self._run_seed()
        lp.refresh_from_db()
        self.assertEqual(lp.accent_color, "#ff00ff")


@override_settings(DEBUG=True)
class ProfilePreviewTests(TestCase):
    """Verify ?profile=<slug> preview override in DEBUG mode."""

    def test_preview_querystring_sets_active_profile_and_body_class(self):
        LayoutProfile.objects.create(
            name="Preview DL", slug="preview-dl",
            template_variant="data_lab",
        )
        response = self.client.get(reverse("portfolio:home") + "?profile=preview-dl")
        ctx = response.context
        self.assertEqual(ctx["active_profile"].slug, "preview-dl")
        self.assertEqual(ctx["template_variant"], "data_lab")
        self.assertIn("variant-data_lab", response.content.decode())

    def test_preview_bad_slug_ignored(self):
        response = self.client.get(reverse("portfolio:home") + "?profile=nonexistent")
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=False)
    def test_preview_disabled_when_not_debug(self):
        """In production (DEBUG=False), ?profile= should have no effect."""
        LayoutProfile.objects.create(
            name="Prod DL", slug="prod-dl",
            template_variant="data_lab",
        )
        response = self.client.get(reverse("portfolio:home") + "?profile=prod-dl")
        ctx = response.context
        # Should NOT pick up the profile override
        self.assertIsNone(ctx["active_profile"])


class TemplateEncodingGuardrailTests(TestCase):
    """Scan every template file for encoding problems that silently break
    rendering: UTF-8 BOM (EF BB BF) and bare cp1252 bytes that indicate
    a file was saved in the wrong encoding."""

    import pathlib
    TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"

    # Bare bytes that should never appear in a valid UTF-8 template.
    # Range 0x80-0x9F are C1 control codes — valid in cp1252 but not in
    # well-formed UTF-8 text (they only appear as trail bytes in multi-byte
    # sequences, never as leading bytes).
    CP1252_LEAD_BYTES = set(range(0x80, 0xA0))

    def _template_files(self):
        """Yield all .html and .css files under the templates directory."""
        for ext in ("*.html", "*.css"):
            yield from self.TEMPLATE_DIR.rglob(ext)

    def test_no_utf8_bom(self):
        """No template file should start with the UTF-8 BOM (EF BB BF)."""
        BOM = b"\xef\xbb\xbf"
        for path in self._template_files():
            with self.subTest(file=str(path.relative_to(self.TEMPLATE_DIR))):
                data = path.read_bytes()
                self.assertFalse(
                    data.startswith(BOM),
                    f"{path.name} starts with UTF-8 BOM — re-save as UTF-8 without BOM",
                )

    def test_no_cp1252_leading_bytes(self):
        """No template file should contain bare cp1252 leading bytes
        (0x80-0x9F) which indicate wrong-encoding saves."""
        for path in self._template_files():
            with self.subTest(file=str(path.relative_to(self.TEMPLATE_DIR))):
                data = path.read_bytes()
                bad = []
                i = 0
                while i < len(data):
                    b = data[i]
                    if b < 0x80:
                        i += 1          # ASCII
                    elif 0xC2 <= b <= 0xDF:
                        i += 2          # 2-byte UTF-8
                    elif 0xE0 <= b <= 0xEF:
                        i += 3          # 3-byte UTF-8
                    elif 0xF0 <= b <= 0xF4:
                        i += 4          # 4-byte UTF-8
                    elif b in self.CP1252_LEAD_BYTES:
                        bad.append((i, hex(b)))
                        i += 1
                    else:
                        i += 1          # other byte
                self.assertEqual(
                    bad, [],
                    f"{path.name} has bare cp1252 bytes at: {bad[:10]}",
                )

    def test_all_templates_valid_utf8(self):
        """Every template must decode as valid UTF-8."""
        for path in self._template_files():
            with self.subTest(file=str(path.relative_to(self.TEMPLATE_DIR))):
                data = path.read_bytes()
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    self.fail(f"{path.name} is not valid UTF-8: {exc}")


@override_settings(DEBUG=True)
class VariantReviewTests(TestCase):
    """Variant Review Mode page tests."""

    def test_variant_review_returns_200_in_debug(self):
        response = self.client.get("/variant-review/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Variant Review Mode")

    def test_variant_review_lists_all_variants(self):
        response = self.client.get("/variant-review/")
        for slug, label in TEMPLATE_VARIANT_CHOICES:
            with self.subTest(variant=slug):
                self.assertContains(response, label)

    def test_variant_review_has_core_page_links(self):
        """Review page should include links for all core pages per variant."""
        # Create a project so the project detail link appears
        cat = Category.objects.create(name="Rev Cat", slug="rev-cat")
        Project.objects.create(title="Rev Proj", slug="rev-proj",
                               category=cat, visible=True)
        for slug, _ in TEMPLATE_VARIANT_CHOICES:
            LayoutProfile.objects.update_or_create(
                slug=f"rev-{slug}",
                defaults={"name": f"Rev {slug}", "template_variant": slug},
            )
        response = self.client.get("/variant-review/")
        html = response.content.decode()
        # Must include links for at least 8 core pages per variant
        for page_name in ["Home", "Projects", "Project Detail", "About",
                          "Resume", "Education", "Certifications", "Contact"]:
            self.assertIn(page_name, html,
                          f"Missing '{page_name}' link on review page")

    def test_variant_review_has_data_variant_slug_attributes(self):
        """Each variant row should have a data-variant-slug attribute."""
        response = self.client.get("/variant-review/")
        html = response.content.decode()
        for slug, _ in TEMPLATE_VARIANT_CHOICES:
            with self.subTest(variant=slug):
                self.assertIn(f'data-variant-slug="{slug}"', html)

    @override_settings(DEBUG=False)
    def test_variant_review_404_when_not_debug(self):
        response = self.client.get("/variant-review/")
        self.assertEqual(response.status_code, 404)
