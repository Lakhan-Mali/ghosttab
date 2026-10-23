"""
BrowserSession model — a snapshot of selected tabs imported at one moment.

A session is created when the browser extension (or manual bulk paste) sends
a batch of pages to GhostTab AI. Sessions can be converted into Projects,
or kept as recovery records ("resume where I left off").
"""
from django.conf import settings
from django.db import models


class BrowserSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    label = models.CharField(max_length=240, blank=True)
    source = models.CharField(max_length=20, default="extension")  # extension | bulk | manual
    page_count = models.PositiveIntegerField(default=0)
    raw_payload = models.JSONField(default=dict, blank=True)
    converted_project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="source_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label or 'Session'} · {self.page_count} pages"
