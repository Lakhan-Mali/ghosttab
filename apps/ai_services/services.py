"""
Provider-agnostic AI service layer.

Public entrypoints (no LLM provider knowledge leaks into views):

    group_pages(pages)            -> grouping suggestions
    infer_project_goal(pages)     -> a goal sentence
    summarize_research(project)   -> research summary
    generate_next_actions(pages)  -> list of ActionItem dicts
    compare_products(pages)       -> comparison table

When ``AI_PROVIDER`` is ``demo`` (the default), every call returns a
deterministic, opinionated result so the product is fully explorable without
an API key. When set to ``openai`` or ``zai``, real API calls are made and
all failures degrade gracefully to the deterministic fallback with a clear
``provider`` flag on the resulting ``AIAnalysis``.
"""
from __future__ import annotations
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from apps.projects.models import Project, SavedPage, AIAnalysis

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def group_pages(pages: List[SavedPage]) -> Dict[str, Any]:
    """Cluster pages into suggested project groupings.

    Returns: ``{"groups": [{"label": str, "page_ids": [int], "rationale": str}], "provider": str}``
    """
    try:
        if _use_live_provider():
            return _provider_group_pages(pages)
    except AIServiceError as e:
        logger.warning("group_pages fell back to demo: %s", e)
    return _demo_group_pages(pages)


def infer_project_goal(project: Project) -> Dict[str, Any]:
    """Infer (or refresh) the project goal from its saved pages."""
    try:
        if _use_live_provider():
            return _provider_infer_goal(project)
    except AIServiceError as e:
        logger.warning("infer_project_goal fell back to demo: %s", e)
    return _demo_infer_goal(project)


def summarize_research(project: Project) -> Dict[str, Any]:
    """Generate or refresh a research summary."""
    try:
        if _use_live_provider():
            return _provider_summarize(project)
    except AIServiceError as e:
        logger.warning("summarize_research fell back to demo: %s", e)
    return _demo_summarize(project)


def generate_next_actions(project: Project) -> Dict[str, Any]:
    """Generate a fresh list of suggested actions based on saved pages."""
    try:
        if _use_live_provider():
            return _provider_generate_actions(project)
    except AIServiceError as e:
        logger.warning("generate_next_actions fell back to demo: %s", e)
    return _demo_generate_actions(project)


def compare_products(project: Project) -> Dict[str, Any]:
    """Build a comparison table from saved pages."""
    try:
        if _use_live_provider():
            return _provider_compare(project)
    except AIServiceError as e:
        logger.warning("compare_products fell back to demo: %s", e)
    return _demo_compare(project)


# --------------------------------------------------------------------------- #
# Provider dispatch
# --------------------------------------------------------------------------- #
def _use_live_provider() -> bool:
    return (
        getattr(settings, "AI_PROVIDER", "demo") in ("openai", "zai")
        and bool(getattr(settings, "AI_API_KEY", ""))
    )


def _provider_infer_goal(project: Project) -> Dict[str, Any]:
    prompt = _build_prompt(
        "infer_goal",
        project,
        extra_instruction="Return JSON: {\"goal\": string, \"confidence\": 0..1}. Be specific.",
    )
    raw = _call_llm(prompt, expect_json=True)
    payload = _coerce_payload(raw, required_keys=["goal"], fallback=_demo_infer_goal(project))
    _persist_analysis(project, AIAnalysis.Kind.GOAL, payload, provider=settings.AI_PROVIDER)
    return payload


def _provider_summarize(project: Project) -> Dict[str, Any]:
    prompt = _build_prompt(
        "summarize",
        project,
        extra_instruction=(
            "Return JSON: {\"summary\": string, \"key_findings\": [string], "
            "\"open_questions\": [string]}. Do not invent facts. If information "
            "is missing, list it under open_questions."
        ),
    )
    raw = _call_llm(prompt, expect_json=True)
    payload = _coerce_payload(raw, required_keys=["summary"], fallback=_demo_summarize(project))
    _persist_analysis(project, AIAnalysis.Kind.SUMMARY, payload, provider=settings.AI_PROVIDER)
    return payload


def _provider_generate_actions(project: Project) -> Dict[str, Any]:
    prompt = _build_prompt(
        "actions",
        project,
        extra_instruction=(
            "Return JSON: {\"actions\": [{\"title\": string, \"rationale\": string}]}. "
            "Maximum 5 actions. Each title must be a concrete next step."
        ),
    )
    raw = _call_llm(prompt, expect_json=True)
    payload = _coerce_payload(raw, required_keys=["actions"], fallback=_demo_generate_actions(project))
    _persist_analysis(project, AIAnalysis.Kind.ACTIONS, payload, provider=settings.AI_PROVIDER)
    return payload


def _provider_compare(project: Project) -> Dict[str, Any]:
    prompt = _build_prompt(
        "compare",
        project,
        extra_instruction=(
            "Return JSON: {\"columns\": [string], \"rows\": [{\"name\": string, "
            "\"values\": [string]}]}. Build a comparison table. Do not invent "
            "values; mark missing values as 'Unknown'."
        ),
    )
    raw = _call_llm(prompt, expect_json=True)
    payload = _coerce_payload(raw, required_keys=["columns", "rows"], fallback=_demo_compare(project))
    _persist_analysis(project, AIAnalysis.Kind.COMPARISON, payload, provider=settings.AI_PROVIDER)
    return payload


def _provider_group_pages(pages: List[SavedPage]) -> Dict[str, Any]:
    if len(pages) < 2:
        return _demo_group_pages(pages)
    pages_payload = [_page_to_dict(p, include_text=True) for p in pages][: settings.AI_MAX_PAGES_PER_REQUEST]
    prompt = {
        "task": "group_pages",
        "instruction": (
            "Cluster the provided pages into 1-5 groups. Return JSON: "
            "{\"groups\": [{\"label\": string, \"page_urls\": [string], \"rationale\": string}]}."
        ),
        "pages": pages_payload,
    }
    raw = _call_llm(prompt, expect_json=True)
    payload = _coerce_payload(raw, required_keys=["groups"], fallback=_demo_group_pages(pages))
    # Map URLs back to ids
    url_to_id = {p.url: p.id for p in pages}
    for g in payload["groups"]:
        g["page_ids"] = [url_to_id[u] for u in g.get("page_urls", []) if u in url_to_id]
        g.pop("page_urls", None)
    payload["provider"] = settings.AI_PROVIDER
    return payload


# --------------------------------------------------------------------------- #
# Demo (deterministic) implementations
# --------------------------------------------------------------------------- #
def _demo_infer_goal(project: Project) -> Dict[str, Any]:
    domains = _top_domains(project)
    title_hint = project.title.lower()
    if any(kw in title_hint for kw in ("laptop", "phone", "headphone", "monitor", "buy", "purchase")):
        goal = "Compare options and pick the best product for your needs, then decide on a purchase."
    elif any(kw in title_hint for kw in ("apartment", "rent", "house", "lease")):
        goal = "Shortlist candidates within budget, verify lease terms, and schedule tours."
    elif any(kw in title_hint for kw in ("learn", "course", "study", "tutorial")):
        goal = "Build a structured learning path and work through it week by week."
    elif any(kw in title_hint for kw in ("trip", "travel", "vacation", "flight")):
        goal = "Decide on destination, dates, and book transport and lodging."
    elif any(kw in title_hint for kw in ("job", "career", "interview", "resume")):
        goal = "Tailor your application materials and apply to a focused shortlist of roles."
    else:
        goal = f"Organize research on {', '.join(domains[:3]) or 'this topic'} and produce a clear next step."
    payload = {"goal": goal, "confidence": 0.78, "provider": "demo"}
    _persist_analysis(project, AIAnalysis.Kind.GOAL, payload, provider="demo")
    return payload


def _demo_summarize(project: Project) -> Dict[str, Any]:
    pages = list(project.pages.all())
    if not pages:
        payload = {"summary": "No saved pages yet. Add URLs to begin research.", "key_findings": [], "open_questions": [], "provider": "demo"}
        _persist_analysis(project, AIAnalysis.Kind.SUMMARY, payload, provider="demo")
        return payload
    domains = _top_domains(project)
    summary = (
        f"This project has {len(pages)} saved page(s) from "
        f"{', '.join(domains[:3])}. Group them around the project goal, "
        f"identify the strongest candidate, and verify the missing facts before deciding."
    )
    findings = [
        f"{pages[0].title or pages[0].domain}: primary source.",
        f"{len(pages)} pages collected across {len(set(p.domain for p in pages))} domain(s).",
    ]
    if len(pages) > 2:
        findings.append("Multiple sources suggest active comparison; cross-check claims.")
    open_q = ["Which page best addresses the project goal?"] + (
        ["What facts are missing before a decision can be made?"] if len(pages) > 1 else []
    )
    payload = {"summary": summary, "key_findings": findings, "open_questions": open_q, "provider": "demo"}
    _persist_analysis(project, AIAnalysis.Kind.SUMMARY, payload, provider="demo")
    return payload


def _demo_generate_actions(project: Project) -> Dict[str, Any]:
    pages = list(project.pages.all())
    actions: List[Dict[str, Any]] = []
    if not pages:
        actions.append({
            "title": "Save your first 2-3 URLs to seed the project",
            "rationale": "AI suggestions need source material to work from.",
        })
    else:
        actions.append({
            "title": f"Review all {len(pages)} saved pages and tag the strongest 2",
            "rationale": "A short list of finalists focuses the next decision.",
        })
        if len(pages) >= 3:
            actions.append({
                "title": "Build a quick comparison table from the top candidates",
                "rationale": "Side-by-side comparison surfaces the right next step.",
            })
        actions.append({
            "title": "Identify the single missing fact that blocks the decision",
            "rationale": "Most stalled projects are missing one specific datapoint.",
        })
        actions.append({
            "title": "Decide and act before more tabs accumulate",
            "rationale": "Each new tab makes the project harder to finish; ship the decision.",
        })
    payload = {"actions": actions, "provider": "demo"}
    _persist_analysis(project, AIAnalysis.Kind.ACTIONS, payload, provider="demo")
    return payload


def _demo_compare(project: Project) -> Dict[str, Any]:
    pages = list(project.pages.all())
    if len(pages) < 2:
        payload = {
            "columns": ["Source", "Domain", "Note"],
            "rows": [
                {"name": p.title or p.domain or "Untitled", "values": [p.url, p.domain, p.note or "—"]}
                for p in pages
            ] or [{"name": "—", "values": ["Add at least two pages", "—", "—"]}],
            "provider": "demo",
        }
        _persist_analysis(project, AIAnalysis.Kind.COMPARISON, payload, provider="demo")
        return payload
    columns = ["Source", "Domain", "Note", "Saved on"]
    rows = [
        {
            "name": (p.title or p.domain or "Untitled")[:80],
            "values": [
                p.url,
                p.domain,
                (p.note or "—")[:140],
                p.created_at.strftime("%Y-%m-%d"),
            ],
        }
        for p in pages
    ]
    payload = {"columns": columns, "rows": rows, "provider": "demo"}
    _persist_analysis(project, AIAnalysis.Kind.COMPARISON, payload, provider="demo")
    return payload


def _demo_group_pages(pages: List[SavedPage]) -> Dict[str, Any]:
    """Group pages by top-level domain — a simple, deterministic heuristic."""
    if not pages:
        return {"groups": [], "provider": "demo"}
    clusters: Dict[str, List[SavedPage]] = {}
    for p in pages:
        clusters.setdefault(p.domain or "other", []).append(p)
    groups = [
        {
            "label": f"Pages from {domain}",
            "page_ids": [p.id for p in bucket],
            "rationale": f"{len(bucket)} page(s) share the {domain} domain.",
        }
        for domain, bucket in clusters.items()
    ]
    return {"groups": groups, "provider": "demo"}


# --------------------------------------------------------------------------- #
# LLM client + helpers
# --------------------------------------------------------------------------- #
class AIServiceError(Exception):
    """Raised when the AI provider call fails or returns unusable output."""


def _call_llm(prompt: Dict[str, Any] | str, *, expect_json: bool = True) -> Dict[str, Any] | str:
    """Call the configured LLM provider. Raises AIServiceError on any failure."""
    import requests  # local import to keep startup cheap

    provider = settings.AI_PROVIDER
    if provider == "openai":
        url = (settings.AI_API_BASE or "https://api.openai.com/v1") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": "You are a focused research assistant. Always return strict JSON when asked."},
                {"role": "user", "content": _prompt_to_text(prompt)},
            ],
            "max_tokens": settings.AI_MAX_TOKENS,
            "temperature": 0.3,
        }
    elif provider == "zai":
        url = (settings.AI_API_BASE or "https://api.z.ai/api/paas/v4") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": "You are a focused research assistant. Always return strict JSON when asked."},
                {"role": "user", "content": _prompt_to_text(prompt)},
            ],
            "max_tokens": settings.AI_MAX_TOKENS,
            "temperature": 0.3,
        }
    else:
        raise AIServiceError(f"Unknown provider: {provider}")

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=settings.AI_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise AIServiceError(f"Network error: {e}") from e
    if resp.status_code == 429:
        raise AIServiceError("Rate limited by provider (429).")
    if resp.status_code >= 400:
        raise AIServiceError(f"Provider returned {resp.status_code}: {resp.text[:200]}")
    try:
        data = resp.json()
    except ValueError as e:
        raise AIServiceError(f"Provider returned non-JSON: {e}") from e
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        raise AIServiceError("Provider returned empty content.")
    if expect_json:
        parsed = _extract_json(content)
        if parsed is None:
            raise AIServiceError("Provider did not return parseable JSON.")
        return parsed
    return content


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from an LLM response."""
    import json
    for regex in (_JSON_BLOCK_RE, _JSON_OBJ_RE):
        m = regex.search(text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def _prompt_to_text(prompt: Dict[str, Any] | str) -> str:
    if isinstance(prompt, str):
        return prompt
    parts: List[str] = []
    task = prompt.get("task")
    if task:
        parts.append(f"Task: {task}")
    instr = prompt.get("instruction")
    if instr:
        parts.append(f"Instruction: {instr}")
    pages = prompt.get("pages")
    if pages:
        parts.append("Pages:")
        for i, p in enumerate(pages, 1):
            parts.append(
                f"{i}. {p.get('title','(untitled)')} — {p.get('domain','')} — {p.get('url','')}"
            )
            if p.get("note"):
                parts.append(f"   Note: {p['note']}")
            if p.get("raw_text"):
                parts.append(f"   Text: {p['raw_text'][:settings.AI_MAX_CONTENT_CHARS_PER_PAGE]}")
    return "\n".join(parts)


def _build_prompt(task: str, project: Project, *, extra_instruction: str = "") -> Dict[str, Any]:
    pages = list(project.pages.all())[: settings.AI_MAX_PAGES_PER_REQUEST]
    return {
        "task": task,
        "instruction": extra_instruction,
        "project": {
            "title": project.title,
            "goal": project.goal,
            "status": project.status,
        },
        "pages": [_page_to_dict(p, include_text=True) for p in pages],
    }


def _page_to_dict(p: SavedPage, *, include_text: bool = False) -> Dict[str, Any]:
    out = {
        "id": p.id,
        "url": p.url,
        "title": p.title,
        "domain": p.domain,
        "note": p.note,
    }
    if include_text and p.raw_text:
        out["raw_text"] = p.raw_text[: settings.AI_MAX_CONTENT_CHARS_PER_PAGE]
    return out


def _coerce_payload(raw: Any, *, required_keys: List[str], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Validate provider output. Fall back to deterministic demo on validation failure."""
    if not isinstance(raw, dict):
        logger.warning("Provider output was not a dict; using fallback. Got: %r", raw)
        return fallback
    missing = [k for k in required_keys if k not in raw]
    if missing:
        logger.warning("Provider output missing keys %s; using fallback.", missing)
        return fallback
    raw.setdefault("provider", settings.AI_PROVIDER)
    return raw


def _persist_analysis(project: Project, kind: str, payload: Dict[str, Any], *, provider: str) -> AIAnalysis:
    return AIAnalysis.objects.create(
        project=project, kind=kind, payload=payload, provider=provider,
    )


def _top_domains(project: Project, limit: int = 5) -> List[str]:
    seen = []
    for p in project.pages.all():
        d = p.domain or urlparse(p.url).netloc
        if d and d not in seen:
            seen.append(d)
    return seen[:limit]
