"""Sessions URLs (authenticated web views)."""
from django.urls import path
from .views_app import session_list

urlpatterns = [
    path("", session_list, name="session_list"),
]
