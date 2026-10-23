"""
Deterministic demo data used when no AI provider is configured.

This module is the single source of truth for the marketing demo and for
development. It deliberately produces realistic, opinionated output so the
product is explorable end-to-end without an API key.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class DemoPage:
    url: str
    title: str
    domain: str
    note: str = ""
    raw_text: str = ""


@dataclass
class DemoAction:
    title: str
    rationale: str
    status: str = "pending"


@dataclass
class DemoProject:
    title: str
    goal: str
    pages: List[DemoPage]
    actions: List[DemoAction]
    summary: str
    comparison: Dict[str, Any] | None = None
    status: str = "active"


def _build_laptop_project() -> DemoProject:
    return DemoProject(
        title="Find a 14\" laptop for design work",
        goal="Pick a 14-inch laptop under $1,800 with a color-accurate display, 16GB+ RAM, and good Linux compatibility for design tools.",
        pages=[
            DemoPage(
                url="https://www.notebookcheck.net/ThinkPad-T14s-review.html",
                title="Lenovo ThinkPad T14s Gen 4 review – lightweight 14-inch workhorse",
                domain="notebookcheck.net",
                note="Looks rugged, 400 nits, but display gamut only ~62% sRGB.",
                raw_text="14-inch IPS, 1920x1200, 400 nits, 100% sRGB claimed, 16GB soldered RAM, USB4.",
            ),
            DemoPage(
                url="https://frame.work/laptop/en-EN",
                title="Framework Laptop 13 — configurable, repairable",
                domain="frame.work",
                note="Repairable, but the 13.5\" screen is a little small for design.",
                raw_text="13.5-inch 3:2, 2256x1504, user-replaceable mainboard, expansion ports.",
            ),
            DemoPage(
                url="https://www.apple.com/macbook-air/",
                title="MacBook Air 13\" and 15\" — M3 chip",
                domain="apple.com",
                note="M3 is excellent but macOS only — I need Linux for some tools.",
                raw_text="M3 chip, 13.6\" Liquid Retina, P3 wide color, 18-hour battery.",
            ),
            DemoPage(
                url="https://www.dell.com/en-us/shop/dell-laptops/xps-14",
                title="Dell XPS 14 — premium 14\" laptop",
                domain="dell.com",
                note="OLED 3K option looks gorgeous but battery is short.",
                raw_text="14-inch 3.2K OLED, touch, Intel Core Ultra, NVIDIA RTX 4050, 16GB.",
            ),
        ],
        actions=[
            DemoAction(
                title="Shortlist to two finalists: XPS 14 OLED vs. ThinkPad T14s",
                rationale="Both meet the 14-inch + 16GB requirement. Comparing display color accuracy will decide the winner.",
            ),
            DemoAction(
                title="Verify Linux compatibility for the XPS 14's Intel Arc iGPU",
                rationale="Design tools may need specific driver support; check Arch Wiki and Dell's driver matrix.",
            ),
            DemoAction(
                title="Confirm 100% sRGB / DCI-P3 coverage with a third-party review",
                rationale="Manufacturer claims are often best-case; NotebookCheck measures actual gamut.",
            ),
            DemoAction(
                title="Decide and place the order before the current sale ends",
                rationale="The XPS 14 OLED is currently $300 off; sale ends Sunday.",
                status="done",
            ),
        ],
        summary=(
            "You are choosing a 14-inch laptop for design work under $1,800. Four pages are in play: "
            "ThinkPad T14s, Framework 13, MacBook Air M3, and Dell XPS 14 OLED. "
            "Three of four meet your spec; the Framework 13 is undersized for design work. "
            "The XPS 14 OLED and ThinkPad T14s are the strongest candidates. "
            "The display color accuracy question is unresolved and is the key decision factor."
        ),
        comparison={
            "columns": ["Display", "RAM", "OS", "Color gamut", "Battery (hr)", "Price (USD)"],
            "rows": [
                {"name": "ThinkPad T14s", "values": ["14\" IPS 1920x1200", "16GB", "Linux/Win", "~62% sRGB", "12", "$1,499"]},
                {"name": "Framework 13", "values": ["13.5\" 2256x1504", "16GB", "Linux", "Untested", "11", "$1,399"]},
                {"name": "MacBook Air M3", "values": ["13.6\" Retina", "16GB", "macOS", "P3 wide", "18", "$1,299"]},
                {"name": "Dell XPS 14 OLED", "values": ["14\" 3.2K OLED", "16GB", "Linux/Win", "100% DCI-P3", "9", "$1,799"]},
            ],
        },
    )


def _build_apartment_project() -> DemoProject:
    return DemoProject(
        title="Apartment hunt — 2BR near public transit",
        goal="Find a 2-bedroom apartment within 30 minutes of downtown by transit, under $2,400/month, available next month.",
        pages=[
            DemoPage(
                url="https://www.apartments.com/example-1",
                title="Maple Court Apartments — 2BR, 1.5BA, $2,150",
                domain="apartments.com",
                note="Cheaper, but bus is 45 min. Might be worth it.",
            ),
            DemoPage(
                url="https://www.zillow.com/example-2",
                title="Highland Park 2BR — $2,350, near Metro",
                domain="zillow.com",
                note="Strong candidate — 20 min by Metro, in-unit laundry.",
            ),
            DemoPage(
                url="https://www.trulia.com/example-3",
                title="Riverside Lofts 2BR — $2,800",
                domain="trulia.com",
                note="Over budget but the building is gorgeous.",
            ),
        ],
        actions=[
            DemoAction(
                title="Schedule tours for Highland Park and Maple Court",
                rationale="Both are within budget; Highland Park wins on transit time.",
                status="in_progress",
            ),
            DemoAction(
                title="Request lease terms in writing from both landlords",
                rationale="Verify move-in date, security deposit, and pet policy.",
            ),
            DemoAction(
                title="Drop Riverside Lofts unless budget increases",
                rationale="Riverside is $400/month over budget with no transit advantage.",
                status="skipped",
            ),
        ],
        summary=(
            "Three apartments are shortlisted. Highland Park is the strongest candidate (best transit, "
            "in-unit laundry, within budget). Maple Court is cheaper but the bus commute is 45 min. "
            "Riverside Lofts is over budget and was skipped. Next step: schedule tours."
        ),
    )


def _build_learning_project() -> DemoProject:
    return DemoProject(
        title="Learning path: modern PostgreSQL performance",
        goal="Build a structured 4-week self-study path to tune PostgreSQL query performance for a 200GB database.",
        pages=[
            DemoPage(
                url="https://www.postgresql.org/docs/current/performance-tips.html",
                title="PostgreSQL docs: Performance Tips",
                domain="postgresql.org",
                note="Official starting point — EXPLAIN ANALYZE, indexes.",
            ),
            DemoPage(
                url="https://www.cybertec-postgresql.com/en/blog/",
                title="Cybertec blog: EXPLAIN ANALYZE deep dive",
                domain="cybertec-postgresql.com",
                note="Walkthrough of EXPLAIN plans with diagrams.",
            ),
            DemoPage(
                url="https://use-the-index-luke.com/",
                title="Use The Index, Luke!",
                domain="use-the-index-luke.com",
                note="Free book on indexing. Must-read.",
            ),
        ],
        actions=[
            DemoAction(
                title="Read 'Use The Index, Luke!' chapters 1-3 this week",
                rationale="Foundational indexing knowledge before query tuning.",
                status="done",
            ),
            DemoAction(
                title="Replay 5 slowest queries from production using EXPLAIN ANALYZE",
                rationale="Apply indexing concepts to real workload; capture before/after timings.",
            ),
            DemoAction(
                title="Draft a 4-week study summary for the team",
                rationale="Consolidate learnings into a reusable playbook.",
            ),
        ],
        summary=(
            "You are building a 4-week study path on PostgreSQL performance. Three resources are bookmarked: "
            "official docs, Cybertec's blog, and Use The Index, Luke. Indexing fundamentals are already covered. "
            "Next: replay slow production queries and capture before/after metrics."
        ),
    )


DEMO_PROJECTS: List[DemoProject] = [
    _build_laptop_project(),
    _build_apartment_project(),
    _build_learning_project(),
]


def build_demo_workspace() -> Dict[str, Any]:
    """Return a serializable demo workspace for the interactive demo page."""
    return {
        "projects": [
            {
                "id": -i,
                "title": p.title,
                "goal": p.goal,
                "status": p.status,
                "pages": [pg.__dict__ for pg in p.pages],
                "actions": [a.__dict__ for a in p.actions],
                "summary": p.summary,
                "comparison": p.comparison,
            }
            for i, p in enumerate(DEMO_PROJECTS, start=1)
        ]
    }
