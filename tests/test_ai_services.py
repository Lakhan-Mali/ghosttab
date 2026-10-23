"""Tests for the AI service layer (deterministic demo mode)."""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from apps.projects.models import Project, SavedPage, ActionItem, AIAnalysis
from apps.ai_services import services

User = get_user_model()


@override_settings(AI_PROVIDER="demo")
class DemoServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="svc@example.com", password="Test12345!")
        self.project = Project.objects.create(user=self.user, title="Find a 14-inch laptop for design")
        for url, title, domain in [
            ("https://example.com/a", "A", "example.com"),
            ("https://example.com/b", "B", "example.com"),
            ("https://other.com/c", "C", "other.com"),
        ]:
            SavedPage.objects.create(project=self.project, url=url, title=title, domain=domain)

    def test_infer_goal_returns_goal_string(self):
        result = services.infer_project_goal(self.project)
        self.assertIn("goal", result)
        self.assertTrue(result["goal"])
        self.assertEqual(result["provider"], "demo")
        # Persisted
        self.assertTrue(AIAnalysis.objects.filter(project=self.project, kind="goal").exists())

    def test_summarize_returns_summary_and_findings(self):
        result = services.summarize_research(self.project)
        self.assertIn("summary", result)
        self.assertIn("key_findings", result)
        self.assertIn("open_questions", result)
        self.assertGreater(len(result["key_findings"]), 0)

    def test_generate_actions_creates_action_items(self):
        result = services.generate_next_actions(self.project)
        self.assertIn("actions", result)
        self.assertGreater(len(result["actions"]), 0)
        self.assertTrue(all("title" in a and "rationale" in a for a in result["actions"]))

    def test_compare_returns_table_shape(self):
        result = services.compare_products(self.project)
        self.assertIn("columns", result)
        self.assertIn("rows", result)
        self.assertEqual(len(result["columns"]), 4)
        self.assertEqual(len(result["rows"]), 3)

    def test_group_pages_clusters_by_domain(self):
        pages = list(self.project.pages.all())
        result = services.group_pages(pages)
        self.assertEqual(result["provider"], "demo")
        self.assertEqual(len(result["groups"]), 2)  # example.com + other.com

    def test_summarize_empty_project_returns_helpful_message(self):
        empty = Project.objects.create(user=self.user, title="Empty")
        result = services.summarize_research(empty)
        self.assertIn("summary", result)
        self.assertIn("No saved pages", result["summary"])

    def test_generate_actions_empty_project_returns_seed_action(self):
        empty = Project.objects.create(user=self.user, title="Empty")
        result = services.generate_next_actions(empty)
        self.assertGreater(len(result["actions"]), 0)
        self.assertIn("first", result["actions"][0]["title"].lower())


@override_settings(AI_PROVIDER="demo")
class ServicePersistenceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="persist@example.com", password="Test12345!")
        self.project = Project.objects.create(user=self.user, title="P")
        SavedPage.objects.create(project=self.project, url="https://x.com", domain="x.com")

    def test_infer_goal_persists_and_can_be_replayed(self):
        services.infer_project_goal(self.project)
        services.infer_project_goal(self.project)
        self.assertEqual(
            AIAnalysis.objects.filter(project=self.project, kind="goal").count(), 2,
            "Each call should persist a new AIAnalysis record."
        )

    def test_compare_works_with_single_page(self):
        result = services.compare_products(self.project)
        self.assertEqual(result["provider"], "demo")
        self.assertEqual(len(result["rows"]), 1)


@override_settings(AI_PROVIDER="openai", AI_API_KEY="")
class NoKeyTests(TestCase):
    """When provider is set but no key, fall back to demo."""

    def test_falls_back_when_no_key(self):
        user = User.objects.create_user(email="nokey@example.com", password="Test12345!")
        project = Project.objects.create(user=user, title="P")
        SavedPage.objects.create(project=project, url="https://x.com", domain="x.com")
        result = services.summarize_research(project)
        # No key -> use_live_provider returns False -> demo path
        self.assertEqual(result["provider"], "demo")
