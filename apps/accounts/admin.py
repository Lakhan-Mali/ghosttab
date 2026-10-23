"""Admin registration for accounts."""
from django.contrib import admin
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "display_name")
    ordering = ("-date_joined",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "reduced_motion", "auto_group_new_pages")
    search_fields = ("user__email",)
