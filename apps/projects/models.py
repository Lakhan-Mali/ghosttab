"""
Project, SavedPage, ActionItem, AIAnalysis models.

Design notes
------------
- Every user-specific model is ownership-scoped through ``Project.user``.
- ``SavedPage`` stores URL + lightweight metadata only. We do NOT fetch
  arbitrary URLs on the backend unless the operator explicitly enables a
  hardened metadata fetcher (see ``apps.sessions.url_metadata``).
- ``AIAnalysis`` stores the structured JSON output of the AI service so we
  can replay summaries, comparisons, and action lists without re-calling
  the provider.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# --------------------------------------------------------------------------- #
# Project
# --------------------------------------------------------------------------- #
class Project(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=240)
    goal = models.TextField(blank=True, help_text="AI-inferred or user-edited goal.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    is_demo = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "-updated_at"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    # ---- convenience -----------------------------------------------------
    @property
    def completion_ratio(self):
        actions = self.action_items.all()
        total = actions.count()
        if not total:
            return 0.0
        return actions.filter(status=ActionItem.Status.DONE).count() / total

    @property
    def pending_action_count(self):
        return self.action_items.exclude(status=ActionItem.Status.DONE).count()

    @property
    def next_action(self):
        return (
            self.action_items.exclude(status=ActionItem.Status.DONE)
            .order_by("created_at")
            .first()
        )


# --------------------------------------------------------------------------- #
# SavedPage
# --------------------------------------------------------------------------- #
class SavedPage(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="pages"
    )
    url = models.URLField(max_length=2048)
    title = models.CharField(max_length=400, blank=True)
    domain = models.CharField(max_length=240, blank=True)
    favicon_url = models.URLField(max_length=600, blank=True)
    note = models.TextField(blank=True)
    raw_text = models.TextField(blank=True, help_text="Optional pasted text for AI context.")
    source = models.CharField(max_length=20, default="manual")  # manual | extension | paste
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "-created_at"]),
            models.Index(fields=["domain"]),
        ]
        ordering = ["-created_at"]
        unique_together = [("project", "url")]

    def __str__(self):
        return self.title or self.url

    def clean(self):
        if self.url and not self.url.lower().startswith(("http://", "https://")):
            raise ValidationError({"url": "URL must start with http:// or https://"})


# --------------------------------------------------------------------------- #
# ActionItem
# --------------------------------------------------------------------------- #
class ActionItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        SKIPPED = "skipped", "Skipped"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="action_items"
    )
    title = models.CharField(max_length=400)
    rationale = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    ai_generated = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "-created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return self.title

    def mark_done(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def reopen(self):
        self.status = self.Status.PENDING
        self.completed_at = None
        self.save(update_fields=["status", "completed_at", "updated_at"])


# --------------------------------------------------------------------------- #
# AIAnalysis (cached structured output)
# --------------------------------------------------------------------------- #
class AIAnalysis(models.Model):
    class Kind(models.TextChoices):
        GOAL = "goal", "Inferred goal"
        SUMMARY = "summary", "Summary"
        ACTIONS = "actions", "Generated actions"
        COMPARISON = "comparison", "Comparison"
        GROUPING = "grouping", "Grouping suggestion"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="analyses"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    payload = models.JSONField(default=dict)
    provider = models.CharField(max_length=60, default="demo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "kind", "-created_at"]),
        ]
        ordering = ["-created_at"]
        get_latest_by = "created_at"

    def __str__(self):
        return f"{self.project.title} · {self.kind}"
