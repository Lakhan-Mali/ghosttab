"""Sessions list view."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import BrowserSession


@login_required
def session_list(request):
    sessions = BrowserSession.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "sessions/session_list.html", {
        "sessions": sessions, "active_nav": "sessions",
    })
