"""Project URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("new/", views.project_create, name="project_create"),
    path("import-demo/", views.import_demo_data, name="import_demo_data"),
    path("quick-add-url/", views.quick_add_url, name="quick_add_url"),
    path("settings/", lambda r: __import__("django.shortcuts", fromlist=["redirect"]).redirect("/auth/settings/"), name="settings_link"),
    path("<int:project_id>/", views.project_detail, name="project_detail"),
    path("<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("<int:project_id>/delete/", views.project_delete, name="project_delete"),
    # Pages
    path("<int:project_id>/pages/add/", views.page_add, name="page_add"),
    path("<int:project_id>/pages/bulk/", views.page_bulk_add, name="page_bulk_add"),
    path("<int:project_id>/pages/<int:page_id>/edit/", views.page_edit, name="page_edit"),
    path("<int:project_id>/pages/<int:page_id>/delete/", views.page_delete, name="page_delete"),
    # Actions
    path("<int:project_id>/actions/add/", views.action_add, name="action_add"),
    path("<int:project_id>/actions/<int:action_id>/toggle/", views.action_toggle, name="action_toggle"),
    path("<int:project_id>/actions/<int:action_id>/delete/", views.action_delete, name="action_delete"),
]
