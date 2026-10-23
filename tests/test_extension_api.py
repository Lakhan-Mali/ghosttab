"""Tests for the browser extension API."""
import json
from django.test import TestCase, Client, override_settings

from django.contrib.auth import get_user_model
from apps.projects.models import Project, SavedPage
from apps.sessions.models import BrowserSession

User = get_user_model()


@override_settings(AI_PROVIDER="demo")
class ExtensionAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="ext@example.com", password="Test12345!")
        self.c = Client()

    def test_health_endpoint(self):
        r = self.c.get("/api/extension/health/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["service"], "GhostTab AI")
        self.assertFalse(data["authenticated"])

    def test_import_requires_auth(self):
        r = self.c.post("/api/extension/import/", {"pages": [{"url": "https://x.com"}]}, content_type="application/json")
        self.assertEqual(r.status_code, 401)

    def test_login_and_import_flow(self):
        # Login
        r = self.c.post("/api/extension/login/", data=json.dumps({
            "email": "ext@example.com", "password": "Test12345!"
        }), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        # Import
        r = self.c.post("/api/extension/import/", data=json.dumps({
            "project_title": "From extension",
            "pages": [
                {"url": "https://example.com/a", "title": "A"},
                {"url": "https://example.com/b", "title": "B"},
                {"url": "javascript:alert(1)", "title": "Bad"},  # filtered
            ],
            "auto_group": True,
        }), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data["ok"], True)
        self.assertEqual(data["imported"], 2, "javascript: URL should be filtered.")
        proj = Project.objects.get(id=data["project"]["id"])
        self.assertEqual(proj.user, self.user)
        self.assertEqual(proj.pages.count(), 2)
        self.assertTrue(BrowserSession.objects.filter(converted_project=proj).exists())

    def test_too_many_pages_rejected(self):
        self.c.login(email="ext@example.com", password="Test12345!")
        pages = [{"url": f"https://example.com/{i}", "title": str(i)} for i in range(100)]
        r = self.c.post("/api/extension/import/", data=json.dumps({
            "project_title": "Big", "pages": pages,
        }), content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("at most", r.json()["error"].lower())
