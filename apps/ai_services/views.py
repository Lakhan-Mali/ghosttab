"""AI service views (JSON API, CSRF-protected, rate-limited)."""
import time
import json
import logging
from collections import defaultdict, deque

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.core.permissions import get_owned_project_or_404
from apps.projects.models import ActionItem, SavedPage
from apps.ai_services import services

logger = logging.getLogger(__name__)

# Simple in-memory sliding-window rate limiter (per user, per hour).
# Swap for Redis/django-ratelimit in production.
_RATE_BUCKETS: dict[int, deque[float]] = defaultdict(deque)


def _check_rate_limit(user) -> bool:
    now = time.time()
    window = 3600.0
    limit = settings.AI_RATE_LIMIT_PER_HOUR
    q = _RATE_BUCKETS[user.id]
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def _json_error(message: str, status: int = 400, **extra):
    return JsonResponse({"ok": False, "error": message, **extra}, status=status)


@login_required
@require_POST
@csrf_protect
def group_pages_api(request):
    """Group a user-supplied list of page IDs into suggested clusters."""
    if not _check_rate_limit(request.user):
        return _json_error("Rate limit reached. Try again later.", status=429)
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    page_ids = body.get("page_ids", [])
    if not isinstance(page_ids, list) or len(page_ids) > settings.AI_MAX_PAGES_PER_REQUEST:
        return _json_error(f"page_ids must be a list of at most {settings.AI_MAX_PAGES_PER_REQUEST} ids.")
    pages = list(SavedPage.objects.filter(id__in=page_ids, project__user=request.user))
    result = services.group_pages(pages)
    return JsonResponse({"ok": True, "result": result})


@login_required
@require_POST
@csrf_protect
def infer_goal_api(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    if not _check_rate_limit(request.user):
        return _json_error("Rate limit reached. Try again later.", status=429)
    result = services.infer_project_goal(project)
    if "goal" in result:
        project.goal = result["goal"]
        project.save(update_fields=["goal", "updated_at"])
    return JsonResponse({"ok": True, "result": result})


@login_required
@require_POST
@csrf_protect
def summarize_api(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    if not _check_rate_limit(request.user):
        return _json_error("Rate limit reached. Try again later.", status=429)
    result = services.summarize_research(project)
    return JsonResponse({"ok": True, "result": result})


@login_required
@require_POST
@csrf_protect
def generate_actions_api(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    if not _check_rate_limit(request.user):
        return _json_error("Rate limit reached. Try again later.", status=429)
    result = services.generate_next_actions(project)
    new_actions = []
    with transaction.atomic():
        for a in result.get("actions", []):
            ai = ActionItem.objects.create(
                project=project,
                title=a["title"][:400],
                rationale=a.get("rationale", ""),
                ai_generated=True,
                status=ActionItem.Status.PENDING,
            )
            new_actions.append({"id": ai.id, "title": ai.title, "rationale": ai.rationale, "status": ai.status})
    return JsonResponse({"ok": True, "result": {"actions": new_actions, "provider": result.get("provider", "demo")}})


@login_required
@require_POST
@csrf_protect
def compare_api(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    if not _check_rate_limit(request.user):
        return _json_error("Rate limit reached. Try again later.", status=429)
    result = services.compare_products(project)
    return JsonResponse({"ok": True, "result": result})
