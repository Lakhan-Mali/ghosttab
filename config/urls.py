"""
Root URL configuration for GhostTab AI.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import landing_page, interactive_demo, privacy_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # Marketing
    path("", landing_page, name="landing"),
    path("demo/", interactive_demo, name="interactive_demo"),
    path("privacy/", privacy_view, name="privacy"),
    # Auth
    path("auth/", include("apps.accounts.urls")),
    # Authenticated application
    path("app/", include("apps.projects.urls")),
    path("app/sessions/", include("apps.sessions.urls")),
    path("app/actions/", include("apps.actions.urls")),
    # AI services API
    path("api/ai/", include("apps.ai_services.urls")),
    # Browser extension API
    path("api/extension/", include("apps.sessions.urls_extension")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
        if hasattr(settings, "MEDIA_URL") else []
