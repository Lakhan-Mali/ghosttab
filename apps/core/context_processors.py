"""Core context processors and shared helpers."""
import os


def app_context(request):
    """Expose app-wide configuration to templates."""
    return {
        "APP_NAME": "GhostTab AI",
        "APP_TAGLINE": "Pick up where your mind left off.",
        "AI_DEMO_MODE": os.environ.get("AI_PROVIDER", "demo") == "demo",
        "SUPPORT_EMAIL": os.environ.get("SUPPORT_EMAIL", "support@ghosttab.local"),
    }
