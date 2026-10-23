"""Rate-limited AI API endpoints."""
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.decorators.http import require_POST

from . import views

urlpatterns = [
    path("group/", login_required(views.group_pages_api), name="api_group_pages"),
    path("goal/<int:project_id>/", login_required(views.infer_goal_api), name="api_infer_goal"),
    path("summarize/<int:project_id>/", login_required(views.summarize_api), name="api_summarize"),
    path("actions/<int:project_id>/", login_required(views.generate_actions_api), name="api_generate_actions"),
    path("compare/<int:project_id>/", login_required(views.compare_api), name="api_compare"),
]
