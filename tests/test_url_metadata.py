"""Tests for the URL metadata fetcher SSRF defenses."""
from django.test import TestCase, override_settings
from apps.sessions.url_metadata import _ip_is_safe, fetch_metadata_enabled


class IpSafetyTests(TestCase):

    def test_loopback_unsafe(self):
        self.assertFalse(_ip_is_safe("127.0.0.1"))
        self.assertFalse(_ip_is_safe("::1"))

    def test_private_unsafe(self):
        self.assertFalse(_ip_is_safe("10.0.0.1"))
        self.assertFalse(_ip_is_safe("172.16.0.1"))
        self.assertFalse(_ip_is_safe("192.168.1.1"))

    def test_link_local_unsafe(self):
        self.assertFalse(_ip_is_safe("169.254.1.1"))

    def test_public_safe(self):
        self.assertTrue(_ip_is_safe("8.8.8.8"))
        self.assertTrue(_ip_is_safe("1.1.1.1"))


class FetchToggleTests(TestCase):

    def test_disabled_by_default(self):
        self.assertFalse(fetch_metadata_enabled())
