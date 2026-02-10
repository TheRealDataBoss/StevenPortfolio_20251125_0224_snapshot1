# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

This is a Windows environment. Use PowerShell commands only (Get-ChildItem, Select-String, Get-Content, etc.). Do not use Unix commands (find, grep, cat, ls, etc.).

## Common Commands

```powershell
# Activate virtual environment (required before running Python commands)
.\.venv\Scripts\Activate.ps1

# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Install dependencies
pip install -r requirements.txt
```

## Project Overview

Django 5.0 portfolio website using SQLite. Admin panel uses django-jazzmin for styling.

**Tech Stack:** Django 5.0, Pillow (images), django-jazzmin (admin), Bootstrap 5, FontAwesome

## Architecture

```
core/           # Django project settings, URLs, WSGI/ASGI
portfolio/      # Main application
  models.py     # Project, Category, Resume, ContactMessage, SiteSetting, NavItem
  views.py      # Class-based views (HomeView, ProjectListView, etc.)
  admin.py      # Admin configurations with custom forms
  context_processors.py  # Injects nav_categories and site_settings globally
templates/portfolio/     # Django templates extending base.html
static/css/              # Theme CSS files
```

## Key Models

- **SiteSetting**: Singleton for site-wide config (hero text, theme colors as hex values). Colors are exposed as CSS variables in base.html.
- **Project/Category**: Portfolio items with slug-based URLs, filtering, and search
- **NavItem**: Dynamic navigation with parent/child hierarchy, visibility controls, and group-based access
- **Resume**: File uploads with category labels
- **ContactMessage**: Form submissions from contact page

## Theming

Site colors are configured via SiteSetting admin and rendered as CSS custom properties (--primary, --nav-bg, --hero-start, etc.) in the base template. Theme presets (light/dark/blue/green/purple) exist as static CSS files but the hex color fields take precedence.

## URL Structure

- `/` - Home
- `/projects/` - Project list (supports `?category=` and `?q=` params)
- `/projects/<slug>/` - Project detail
- `/about/`, `/resume/`, `/contact/` - Static pages
- `/admin/` - Django admin
