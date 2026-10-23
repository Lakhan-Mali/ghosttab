"""Project views: dashboard, detail, create, add URL, mark action, delete."""
import logging
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.permissions import get_owned_project_or_404
from apps.ai_services.demo_data import DEMO_PROJECTS
from .forms import ProjectForm, SavedPageForm, QuickAddURLForm, BulkImportURLsForm
from .models import Project, SavedPage, ActionItem

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@login_required
def dashboard(request):
    user = request.user
    projects_qs = Project.objects.filter(user=user).select_related("user")

    # Search
    q = (request.GET.get("q") or "").strip()
    if q:
        projects_qs = projects_qs.filter(title__icontains=q)

    # Status filter
    status = request.GET.get("status", "")
    if status in Project.Status.values:
        projects_qs = projects_qs.filter(status=status)

    projects_qs = projects_qs.order_by("-updated_at")
    paginator = Paginator(projects_qs, 12)
    page = paginator.get_page(request.GET.get("page"))

    # Sidebar nav stats
    pending_action_count = (
        ActionItem.objects.filter(project__user=user)
        .exclude(status=ActionItem.Status.DONE)
        .count()
    )
    recent_actions = (
        ActionItem.objects.filter(project__user=user)
        .order_by("-created_at")[:6]
        .select_related("project")
    )

    welcome = request.GET.get("welcome") == "1"

    return render(request, "projects/dashboard.html", {
        "projects": page,
        "page_obj": page,
        "q": q,
        "status_filter": status,
        "status_choices": Project.Status.choices,
        "pending_action_count": pending_action_count,
        "recent_actions": recent_actions,
        "quick_add_form": QuickAddURLForm(),
        "welcome": welcome,
        "active_nav": "overview",
    })


# --------------------------------------------------------------------------- #
# Project CRUD
# --------------------------------------------------------------------------- #
@login_required
@require_http_methods(["GET", "POST"])
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, "Project created. Add some URLs to begin.")
            return redirect("project_detail", project_id=project.id)
    else:
        form = ProjectForm()
    return render(request, "projects/project_form.html", {"form": form, "is_new": True, "active_nav": "new_project"})


@login_required
@require_http_methods(["GET", "POST"])
def project_detail(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    pages = project.pages.all().order_by("-created_at")
    actions = project.action_items.all().order_by("created_at")
    latest_summary = project.analyses.filter(kind="summary").first()
    latest_comparison = project.analyses.filter(kind="comparison").first()
    latest_goal = project.analyses.filter(kind="goal").first()

    page_form = SavedPageForm()
    bulk_form = BulkImportURLsForm(initial={"project_id": project.id})

    return render(request, "projects/project_detail.html", {
        "project": project,
        "pages": pages,
        "actions": actions,
        "page_form": page_form,
        "bulk_form": bulk_form,
        "latest_summary": latest_summary,
        "latest_comparison": latest_comparison,
        "latest_goal": latest_goal,
        "active_nav": "project",
    })


@login_required
@require_http_methods(["GET", "POST"])
def project_edit(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated.")
            return redirect("project_detail", project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    return render(request, "projects/project_form.html", {
        "form": form, "is_new": False, "project": project, "active_nav": "project",
    })


@login_required
@require_POST
@csrf_protect
def project_delete(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    title = project.title
    project.delete()
    messages.success(request, f"Deleted project “{title}”.")
    return redirect("dashboard")


# --------------------------------------------------------------------------- #
# SavedPage
# --------------------------------------------------------------------------- #
@login_required
@require_POST
@csrf_protect
def page_add(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    form = SavedPageForm(request.POST)
    if form.is_valid():
        page = form.save(commit=False)
        page.project = project
        if not page.domain:
            page.domain = urlparse(page.url).netloc
        try:
            page.save()
            messages.success(request, f"Added “{page.title or page.domain}”.")
        except Exception:
            messages.error(request, "That URL is already saved to this project.")
    else:
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(request, f"{field}: {e}")
    return redirect("project_detail", project_id=project.id)


@login_required
@require_POST
@csrf_protect
def page_bulk_add(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    form = BulkImportURLsForm(request.POST)
    if form.is_valid():
        urls = form.cleaned_data["urls"]
        added = 0
        skipped = 0
        with transaction.atomic():
            for url in urls:
                _, created = SavedPage.objects.get_or_create(
                    project=project, url=url,
                    defaults={"domain": urlparse(url).netloc},
                )
                if created:
                    added += 1
                else:
                    skipped += 1
        messages.success(request, f"Imported {added} URL(s); {skipped} already present.")
    else:
        messages.error(request, "Could not import URLs. Check the format.")
    return redirect("project_detail", project_id=project.id)


@login_required
@require_POST
@csrf_protect
def page_delete(request, project_id: int, page_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    page = get_object_or_404(SavedPage, id=page_id, project=project)
    page.delete()
    messages.success(request, "Removed page.")
    return redirect("project_detail", project_id=project.id)


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def page_edit(request, project_id: int, page_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    page = get_object_or_404(SavedPage, id=page_id, project=project)
    if request.method == "POST":
        form = SavedPageForm(request.POST, instance=page)
        if form.is_valid():
            page = form.save(commit=False)
            if not page.domain:
                page.domain = urlparse(page.url).netloc
            page.save()
            messages.success(request, "Page updated.")
            return redirect("project_detail", project_id=project.id)
    else:
        form = SavedPageForm(instance=page)
    return render(request, "projects/page_edit.html", {
        "form": form, "project": project, "page": page, "active_nav": "project",
    })


# --------------------------------------------------------------------------- #
# ActionItem
# --------------------------------------------------------------------------- #
@login_required
@require_POST
@csrf_protect
def action_toggle(request, project_id: int, action_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    action = get_object_or_404(ActionItem, id=action_id, project=project)
    if action.status == ActionItem.Status.DONE:
        action.reopen()
        new_status = "pending"
    else:
        action.mark_done()
        new_status = "done"
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("json"):
        return JsonResponse({"ok": True, "status": new_status, "id": action.id})
    return redirect("project_detail", project_id=project.id)


@login_required
@require_POST
@csrf_protect
def action_add(request, project_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    title = (request.POST.get("title") or "").strip()
    if title:
        ActionItem.objects.create(project=project, title=title[:400], rationale=request.POST.get("rationale", ""))
        messages.success(request, "Action added.")
    else:
        messages.error(request, "Action title is required.")
    return redirect("project_detail", project_id=project.id)


@login_required
@require_POST
@csrf_protect
def action_delete(request, project_id: int, action_id: int):
    project = get_owned_project_or_404(request.user, project_id)
    action = get_object_or_404(ActionItem, id=action_id, project=project)
    action.delete()
    messages.success(request, "Removed action.")
    return redirect("project_detail", project_id=project.id)


# --------------------------------------------------------------------------- #
# Quick-add URL from dashboard
# --------------------------------------------------------------------------- #
@login_required
@require_POST
@csrf_protect
def quick_add_url(request):
    form = QuickAddURLForm(request.POST)
    if form.is_valid():
        url = form.cleaned_data["url"]
        pid = form.cleaned_data.get("project_id")
        if pid:
            project = get_owned_project_or_404(request.user, pid)
        else:
            project = Project.objects.create(
                user=request.user,
                title="New project — rename me",
                status=Project.Status.NEW,
            )
        SavedPage.objects.get_or_create(
            project=project, url=url,
            defaults={"domain": urlparse(url).netloc, "title": urlparse(url).netloc},
        )
        messages.success(request, "URL added.")
        return redirect("project_detail", project_id=project.id)
    messages.error(request, "Could not add URL.")
    return redirect("dashboard")


# --------------------------------------------------------------------------- #
# Demo data import
# --------------------------------------------------------------------------- #
@login_required
@require_POST
@csrf_protect
def import_demo_data(request):
    if request.user.profile.demo_data_imported:
        messages.info(request, "Demo data is already in your workspace.")
        return redirect("dashboard")
    with transaction.atomic():
        for d in DEMO_PROJECTS:
            project = Project.objects.create(
                user=request.user,
                title=d.title,
                goal=d.goal,
                status=d.status,
                is_demo=True,
            )
            for p in d.pages:
                SavedPage.objects.create(
                    project=project,
                    url=p.url,
                    title=p.title,
                    domain=p.domain,
                    note=p.note,
                    raw_text=p.raw_text,
                    source="paste",
                )
            for a in d.actions:
                ActionItem.objects.create(
                    project=project,
                    title=a.title,
                    rationale=a.rationale,
                    status=a.status,
                    ai_generated=True,
                )
        request.user.profile.demo_data_imported = True
        request.user.profile.save(update_fields=["demo_data_imported"])
    messages.success(request, "Demo workspace imported. Explore it as if it were your own.")
    return redirect("dashboard")
