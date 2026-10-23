"""Convenience test settings."""
from config.settings import *  # noqa

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
