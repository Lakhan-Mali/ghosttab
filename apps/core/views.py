"""Core views: landing page, interactive demo, privacy."""
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def landing_page(request):
    """Marketing landing page with animated hero preview."""
    return render(request, "landing/index.html", {"active_nav": "home"})


@require_GET
def interactive_demo(request):
    """Hands-on demo workspace — no account required."""
    from apps.ai_services.demo_data import build_demo_workspace
    workspace = build_demo_workspace()
    return render(request, "landing/demo.html", {"workspace": workspace, "active_nav": "demo"})


@require_GET
def privacy_view(request):
    return render(request, "landing/privacy.html", {"active_nav": "privacy"})
