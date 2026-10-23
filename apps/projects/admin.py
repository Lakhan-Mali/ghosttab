"""Project, SavedPage, ActionItem admin."""
from django.contrib import admin
from .models import Project, SavedPage, ActionItem, AIAnalysis


class SavedPageInline(admin.TabularInline):
    model = SavedPage
    extra = 0
    readonly_fields = ("created_at",)


class ActionItemInline(admin.TabularInline):
    model = ActionItem
    extra = 0
    readonly_fields = ("created_at", "updated_at", "completed_at")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "is_demo", "updated_at")
    list_filter = ("status", "is_demo")
    search_fields = ("title", "user__email")
    inlines = [SavedPageInline, ActionItemInline]


@admin.register(SavedPage)
class SavedPageAdmin(admin.ModelAdmin):
    list_display = ("title", "domain", "project", "source", "created_at")
    list_filter = ("source",)
    search_fields = ("title", "url", "domain")


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "ai_generated", "created_at")
    list_filter = ("status", "ai_generated")
    search_fields = ("title", "project__title")


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ("project", "kind", "provider", "created_at")
    list_filter = ("kind", "provider")
