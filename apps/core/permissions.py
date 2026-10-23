"""Ownership helpers and permission decorators."""
from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden

from apps.projects.models import Project


def get_owned_project_or_404(user, project_id):
    """Return a project only if it belongs to the user, else 404."""
    return get_object_or_404(Project, id=project_id, user=user)


def require_project_owner(view_func):
    """Decorator that ensures the URL's project_id belongs to the request user."""
    @wraps(view_func)
    def _wrapped(request, project_id, *args, **kwargs):
        project = get_object_or_404(Project, id=project_id, user=request.user)
        request.owned_project = project
        return view_func(request, project_id, *args, **kwargs)
    return _wrapped
