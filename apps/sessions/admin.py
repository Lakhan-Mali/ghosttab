from django.contrib import admin
from .models import BrowserSession


@admin.register(BrowserSession)
class BrowserSessionAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "source", "page_count", "created_at")
    list_filter = ("source",)
    search_fields = ("label", "user__email")
