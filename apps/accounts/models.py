"""
Custom User model + UserProfile.

- Email-based authentication.
- UserProfile stores privacy and UX preferences.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Email-based user manager."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if not extra.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """User identified by email instead of username."""

    username = None
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=120, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def friendly_name(self):
        return self.display_name or self.email.split("@")[0]


class UserProfile(models.Model):
    """Per-user preferences (privacy, motion, demo data flag)."""

    THEME_CHOICES = [
        ("dark", "Dark"),
        ("midnight", "Midnight"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="dark")
    reduced_motion = models.BooleanField(default=False)
    send_product_updates = models.BooleanField(default=False)
    auto_group_new_pages = models.BooleanField(default=True)
    auto_generate_actions = models.BooleanField(default=True)
    demo_data_imported = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"

    def __str__(self):
        return f"Profile for {self.user.email}"
