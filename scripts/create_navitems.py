from portfolio.models import NavItem
if not NavItem.objects.exists():
    NavItem.objects.create(title="Home", url="/", order=0, visible=True)
    NavItem.objects.create(title="Projects", url="/projects/", order=10, visible=True)
    NavItem.objects.create(title="About", url="/about/", order=20, visible=True)
    NavItem.objects.create(title="Contact", url="/contact/", order=30, visible=True)
    print("Created sample NavItems: Home, Projects, About, Contact")
else:
    print("NavItem table already has entries; skipping sample creation.")