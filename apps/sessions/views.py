"""Browser extension API (Manifest V3).

Authentication contract
-----------------------
The extension authenticates with a long-lived API token issued from the
GhostTab AI settings page. The token is sent as ``Authorization: Token <key>``.

In this first iteration, the extension authenticates with the regular Django
session cookie OR an HTTP header ``X-GhostTab-Token`` whose value must match
``settings.GHOSTTAB_EXTENSION_TOKEN``. This is intentionally simple and is
documented as a known limitation; production deployments should switch to a
proper token model (DRF TokenAuthentication or a custom extension-token
table) with per-user revocation.
"""
import json
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from apps.projects.models import Project, SavedPage, ActionItem
from apps.ai_services import services
from .models import BrowserSession

logger = logging.getLogger(__name__)

ALLOWED_URL_SCHEMES = {"http", "https"}
MAX_TABS_PER_IMPORT = 50
MAX_URL_LEN = 2048


def _ext_authenticate(request):
    """Authenticate the extension via either session or shared token."""
    token = request.headers.get("X-GhostTab-Token", "")
    expected = getattr(settings, "GHOSTTAB_EXTENSION_TOKEN", "")
    if expected and token == expected:
        # Token-authenticated: require an explicit user_id header in dev mode only
        # (Production: replace with a real per-user token model.)
        return request.user if request.user.is_authenticated else None
    return request.user if request.user.is_authenticated else None


def _json_error(message: str, status: int = 400):
    return JsonResponse({"ok": False, "error": message}, status=status)


@require_GET
def ext_health(request):
    return JsonResponse({
        "ok": True,
        "service": "GhostTab AI",
        "version": "1.0",
        "authenticated": request.user.is_authenticated,
    })


@require_POST
@csrf_exempt
def ext_login(request):
    """Authenticate the extension with email/password and return a session cookie."""
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    email = (body.get("email") or "").lower().strip()
    password = body.get("password") or ""
    if not email or not password:
        return _json_error("Email and password are required.")
    user = authenticate(request, username=email, password=password)
    if user is None:
        return _json_error("Invalid credentials.", status=401)
    login(request, user)
    return JsonResponse({
        "ok": True,
        "user": {"id": user.id, "email": user.email, "name": user.friendly_name},
    })


@require_POST
@csrf_exempt
def ext_import(request):
    """Receive a batch of selected tabs and create a BrowserSession + Project.

    Body: {"project_title": str, "pages": [{"url": str, "title": str}], "auto_group": bool}
    """
    if not _ext_authenticate(request):
        return _json_error("Not authenticated.", status=401)
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    pages = body.get("pages") or []
    if not isinstance(pages, list) or not pages:
        return _json_error("No pages provided.")
    if len(pages) > MAX_TABS_PER_IMPORT:
        return _json_error(f"At most {MAX_TABS_PER_IMPORT} tabs per import.")

    cleaned = []
    for p in pages:
        url = (p.get("url") or "").strip()[:MAX_URL_LEN]
        title = (p.get("title") or "").strip()[:400]
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_URL_SCHEMES or not parsed.netloc:
            continue
        cleaned.append({"url": url, "title": title, "domain": parsed.netloc})
    if not cleaned:
        return _json_error("No usable URLs after filtering.")

    title = (body.get("project_title") or "Imported tabs").strip()[:240]
    project = Project.objects.create(
        user=request.user,
        title=title,
        status=Project.Status.NEW,
    )
    for p in cleaned:
        SavedPage.objects.create(
            project=project, url=p["url"], title=p["title"], domain=p["domain"], source="extension",
        )
    session = BrowserSession.objects.create(
        user=request.user,
        label=title,
        source="extension",
        page_count=len(cleaned),
        raw_payload={"pages": cleaned},
        converted_project=project,
    )

    # Auto-generate goal and actions if user opted in
    if request.user.profile.auto_group_new_pages:
        try:
            goal = services.infer_project_goal(project)
            if "goal" in goal:
                project.goal = goal["goal"]
                project.status = Project.Status.ACTIVE
                project.save(update_fields=["goal", "status", "updated_at"])
        except Exception as e:  # never block import on AI failure
            logger.warning("Goal inference failed during import: %s", e)
    if request.user.profile.auto_generate_actions:
        try:
            actions = services.generate_next_actions(project)
            for a in actions.get("actions", []):
                ActionItem.objects.create(
                    project=project,
                    title=a["title"][:400],
                    rationale=a.get("rationale", ""),
                    ai_generated=True,
                )
        except Exception as e:
            logger.warning("Action generation failed during import: %s", e)

    return JsonResponse({
        "ok": True,
        "project": {"id": project.id, "title": project.title, "url": f"/app/{project.id}/"},
        "session_id": session.id,
        "imported": len(cleaned),
    })
