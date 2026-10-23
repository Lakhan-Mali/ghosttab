"""Tests for accounts, projects, ownership, and permissions."""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.projects.models import Project, SavedPage, ActionItem, AIAnalysis
from apps.accounts.models import UserProfile

User = get_user_model()


def _make_user(email, password="Test12345!"):
    return User.objects.create_user(email=email, password=password)


@override_settings(AI_PROVIDER="demo")
class ProjectOwnershipTests(TestCase):
    """The most important tests in the app: a user must never see another user's data."""

    def setUp(self):
        self.alice = _make_user("alice@example.com")
        self.bob = _make_user("bob@example.com")
        self.alice_project = Project.objects.create(user=self.alice, title="Alice's project")
        self.bob_project = Project.objects.create(user=self.bob, title="Bob's project")
        SavedPage.objects.create(
            project=self.alice_project,
            url="https://example.com/a",
            title="A",
            domain="example.com",
        )
        ActionItem.objects.create(project=self.alice_project, title="Alice's action")
        self.c = Client()

    def test_user_cannot_view_others_project(self):
        self.c.login(email="bob@example.com", password="Test12345!")
        r = self.c.get(f"/app/{self.alice_project.id}/")
        self.assertEqual(r.status_code, 404, "Bob should not see Alice's project.")

    def test_user_cannot_delete_others_project(self):
        self.c.login(email="bob@example.com", password="Test12345!")
        r = self.c.post(f"/app/{self.alice_project.id}/delete/")
        # Either 404 or 302 — never success on someone else's project
        self.assertIn(r.status_code, (404, 302))
        self.assertTrue(Project.objects.filter(id=self.alice_project.id).exists(),
                        "Alice's project should still exist after Bob tried to delete it.")

    def test_user_cannot_toggle_others_action(self):
        action = ActionItem.objects.create(project=self.bob_project, title="Bob's action")
        self.c.login(email="alice@example.com", password="Test12345!")
        r = self.c.post(f"/app/{self.bob_project.id}/actions/{action.id}/toggle/?json=1")
        self.assertIn(r.status_code, (404, 403))
        action.refresh_from_db()
        self.assertEqual(action.status, ActionItem.Status.PENDING)

    def test_ai_endpoints_require_ownership(self):
        self.c.login(email="bob@example.com", password="Test12345!")
        for endpoint in ["summarize", "actions", "compare", "goal"]:
            r = self.c.post(f"/api/ai/{endpoint}/{self.alice_project.id}/")
            self.assertEqual(r.status_code, 404, f"{endpoint} should 404 for non-owner.")

    def test_dashboard_only_lists_own_projects(self):
        self.c.login(email="alice@example.com", password="Test12345!")
        r = self.c.get("/app/")
        # Alice's project title contains an apostrophe which gets HTML-escaped.
        self.assertContains(r, "Alice")
        self.assertContains(r, "/app/1/")
        self.assertNotContains(r, "Bob")
        self.assertNotContains(r, "/app/2/")


@override_settings(AI_PROVIDER="demo")
class ProjectCRUDTests(TestCase):

    def setUp(self):
        self.user = _make_user("carol@example.com")
        self.c = Client()
        self.c.login(email="carol@example.com", password="Test12345!")

    def test_create_project_via_post(self):
        r = self.c.post("/app/new/", {"title": "New project", "goal": "", "status": "new"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Project.objects.filter(user=self.user, title="New project").exists())

    def test_add_page_validates_url_scheme(self):
        project = Project.objects.create(user=self.user, title="P")
        # Invalid scheme
        r = self.c.post(f"/app/{project.id}/pages/add/", {
            "url": "javascript:alert(1)", "title": "", "note": "", "raw_text": "",
        })
        self.assertEqual(r.status_code, 302)  # redirects back
        self.assertEqual(project.pages.count(), 0, "Invalid URL should not create a page.")

    def test_add_page_validates_url(self):
        project = Project.objects.create(user=self.user, title="P")
        r = self.c.post(f"/app/{project.id}/pages/add/", {
            "url": "https://example.com/article", "title": "Article", "note": "", "raw_text": "",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(project.pages.count(), 1)

    def test_bulk_import_dedupes(self):
        project = Project.objects.create(user=self.user, title="P")
        urls = "https://example.com/1\nhttps://example.com/1\nhttps://example.com/2"
        r = self.c.post(f"/app/{project.id}/pages/bulk/", {"urls": urls, "project_id": project.id})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(project.pages.count(), 2, "Bulk import should dedupe by URL.")

    def test_action_toggle_marks_done_and_reopens(self):
        project = Project.objects.create(user=self.user, title="P")
        action = ActionItem.objects.create(project=project, title="Do thing")
        r = self.c.post(f"/app/{project.id}/actions/{action.id}/toggle/?json=1")
        self.assertEqual(r.status_code, 200)
        action.refresh_from_db()
        self.assertEqual(action.status, ActionItem.Status.DONE)
        self.assertIsNotNone(action.completed_at)
        # Reopen
        self.c.post(f"/app/{project.id}/actions/{action.id}/toggle/?json=1")
        action.refresh_from_db()
        self.assertEqual(action.status, ActionItem.Status.PENDING)
        self.assertIsNone(action.completed_at)

    def test_delete_project_cascades(self):
        project = Project.objects.create(user=self.user, title="P")
        SavedPage.objects.create(project=project, url="https://example.com", domain="example.com")
        ActionItem.objects.create(project=project, title="A")
        AIAnalysis.objects.create(project=project, kind="summary", payload={})
        project_id = project.id
        r = self.c.post(f"/app/{project_id}/delete/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Project.objects.filter(id=project_id).exists())
        self.assertEqual(SavedPage.objects.filter(project_id=project_id).count(), 0)
        self.assertEqual(ActionItem.objects.filter(project_id=project_id).count(), 0)
        self.assertEqual(AIAnalysis.objects.filter(project_id=project_id).count(), 0)


@override_settings(AI_PROVIDER="demo")
class AuthTests(TestCase):

    def test_signup_creates_user_and_profile(self):
        c = Client()
        r = c.post("/auth/signup/", {
            "email": "newbie@example.com",
            "display_name": "Newbie",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(email="newbie@example.com").exists())
        self.assertTrue(UserProfile.objects.filter(user__email="newbie@example.com").exists())

    def test_duplicate_email_rejected(self):
        _make_user("dupe@example.com")
        c = Client()
        r = c.post("/auth/signup/", {
            "email": "dupe@example.com",
            "display_name": "",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        # Form re-renders with errors
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already exists")

    def test_login_redirects_anonymous_from_dashboard(self):
        r = Client().get("/app/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/auth/login/", r.url)
