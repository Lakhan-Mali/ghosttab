"""Browser extension API URLs (no login_required decorator — see views)."""
from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.ext_health, name="ext_health"),
    path("login/", views.ext_login, name="ext_login"),
    path("import/", views.ext_import, name="ext_import"),
]
