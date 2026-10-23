"""Hardened URL metadata fetcher.

NOTE: By default this module is OFF — GhostTab AI does not fetch arbitrary
URLs from the backend. The operator must explicitly enable it by setting
``GTAB_FETCH_METADATA=1`` in the environment. When enabled, the fetcher
applies SSRF defenses:

- Only http(s) schemes are allowed.
- DNS resolution must NOT land on private / loopback / link-local ranges.
- A strict redirect cap is enforced (max 3 hops).
- Response size is capped (default 256 KiB).
- Timeouts are short.
- Content-Type must be HTML.
"""
from __future__ import annotations
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


class MetadataFetchError(Exception):
    pass


@dataclass
class PageMetadata:
    title: str
    domain: str
    favicon_url: str


def fetch_metadata_enabled() -> bool:
    return getattr(settings, "GTAB_FETCH_METADATA", False) and \
        str(getattr(settings, "GTAB_FETCH_METADATA", "")).lower() in ("1", "true", "yes")


def _ip_is_safe(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return False
    for net in _PRIVATE_NETWORKS:
        if ip in net:
            return False
    return True


def _resolve_safe(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise MetadataFetchError(f"DNS resolution failed for {host}: {e}")
    for info in infos:
        ip = info[4][0]
        if not _ip_is_safe(ip):
            raise MetadataFetchError(f"Refusing to fetch private/loopback IP {ip} for {host}.")


def fetch_metadata(url: str, *, timeout: float = 6.0, max_size: int = 262144) -> Optional[PageMetadata]:
    """Fetch title/favicon for a URL. Returns None if disabled or anything looks unsafe."""
    if not fetch_metadata_enabled():
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise MetadataFetchError("Only http(s) URLs are allowed.")
    if not parsed.netloc:
        raise MetadataFetchError("URL must include a domain.")
    _resolve_safe(parsed.hostname)

    try:
        # allow_redirects=False to enforce our own redirect cap with safety checks
        resp = requests.get(url, timeout=timeout, allow_redirects=False, stream=True,
                            headers={"User-Agent": "GhostTabAI-Metadata/1.0"})
        hops = 0
        while resp.is_redirect and hops < 3:
            hops += 1
            next_url = urljoin(url, resp.headers.get("Location", ""))
            np = urlparse(next_url)
            if np.scheme not in ("http", "https") or not np.netloc:
                raise MetadataFetchError("Redirect to invalid URL.")
            _resolve_safe(np.hostname)
            resp = requests.get(next_url, timeout=timeout, allow_redirects=False, stream=True,
                                headers={"User-Agent": "GhostTabAI-Metadata/1.0"})
        if resp.status_code >= 400:
            raise MetadataFetchError(f"Upstream returned {resp.status_code}.")
        ctype = resp.headers.get("Content-Type", "").lower()
        if "html" not in ctype:
            raise MetadataFetchError(f"Non-HTML Content-Type: {ctype}")
        size = 0
        chunks = []
        for chunk in resp.iter_content(chunk_size=8192, decode_unicode=False):
            size += len(chunk)
            if size > max_size:
                raise MetadataFetchError("Response too large.")
            chunks.append(chunk)
        body = b"".join(chunks).decode("utf-8", errors="ignore")
    except requests.RequestException as e:
        raise MetadataFetchError(f"Request error: {e}") from e

    title = _extract_title(body) or parsed.netloc
    favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
    return PageMetadata(title=title[:400], domain=parsed.netloc, favicon_url=favicon_url)


def _extract_title(html: str) -> Optional[str]:
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()
