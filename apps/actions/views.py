"""Action queue: aggregated view across all projects."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.projects.models import ActionItem


@login_required
def action_queue(request):
    base = ActionItem.objects.filter(project__user=request.user).select_related("project")
    pending = base.exclude(status=ActionItem.Status.DONE).order_by("created_at")
    completed = base.filter(status=ActionItem.Status.DONE).order_by("-completed_at")[:20]
    return render(request, "actions/queue.html", {
        "pending": pending,
        "completed": completed,
        "pending_count": pending.count(),
        "active_nav": "queue",
    })
