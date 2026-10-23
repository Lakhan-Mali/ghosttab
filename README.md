# GhostTab AI

> Pick up where your mind left off.

GhostTab AI turns scattered browser tabs into organized projects with clear next actions, AI-generated summaries and comparisons, and a resumable workspace. Built with Django, Tailwind CSS, vanilla JavaScript, and a provider-agnostic AI service layer.

![Stack](https://img.shields.io/badge/stack-Django%20%2B%20Tailwind%20%2B%20vanilla%20JS-8a5cf6)

## What's inside

- **Marketing landing page** with an animated, interactive hero preview that shows scattered tabs transforming into grouped projects with AI goals and next actions.
- **Authenticated dashboard** with collapsible sidebar, search, status filters, project cards, recent activity, and a quick-add URL action.
- **Project detail workspace** — a 3-column layout (project navigation · main content · AI insights panel) with:
  - Editable title and goal.
  - Saved pages with favicon-color, title, domain, note, paste-text context, edit and remove.
  - AI-generated research summary with key findings and open questions.
  - Pending and completed action items with toggle, delete, and custom add.
  - Auto-built comparison tables.
  - Working AI buttons: Summarize, Generate actions, Compare, Infer goal.
- **AI service layer** — provider-agnostic (`demo` / `openai` / `zai`). Falls back to a deterministic demo mode when no API key is configured so the product is fully explorable offline.
- **Browser extension** — Chrome Manifest V3, reads only selected tabs on explicit user action, sends them to the GhostTab AI API.
- **Ownership enforcement** — every user-scoped view checks `project.user == request.user`. Users cannot read, edit, or delete another user's data by guessing IDs.
- **Privacy-first** — no silent history access, no automatic backend URL fetching unless the operator explicitly enables a hardened SSRF-defended metadata fetcher.
- **33 passing tests** covering ownership, CRUD, AI services, extension API, and SSRF defenses.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, Django 6, Django REST Framework |
| Frontend | Django templates, HTML5, Tailwind CSS 3 (build-pipeline, **not** Play CDN), vanilla ES6 JavaScript |
| Icons | Lucide |
| Database | SQLite (dev), PostgreSQL-ready |
| AI | Provider-agnostic service layer; OpenAI-compatible API or Z.ai |
| Extension | Chrome Manifest V3 |

No React. No Next.js. No frontend framework.

## Quickstart

```bash
# 1. Create a virtualenv & install deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Copy environment template
cp .env.example .env
# Edit .env if you want to enable a real LLM provider. Otherwise the app
# runs in deterministic demo mode and needs no external API.

# 3. Run migrations and create an admin user
python manage.py migrate
python manage.py createsuperuser

# 4. (Optional) Build the Tailwind CSS bundle
#    The repo ships with a prebuilt static/css/dist.css — only rebuild if
#    you changed templates or tailwind.config.js.
npm install
npm run build:css

# 5. Start the dev server
python manage.py runserver
```

Open <http://localhost:8000/>.

### Demo account

For convenience, create a user through the signup form, then visit `/app/` and click **Import sample workspace** to load three realistic demo projects (laptop research, apartment hunt, PostgreSQL study path).

## Environment variables

See `.env.example` for the full list. The defaults work for local development without an AI provider.

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev key | Set to a real secret in production. |
| `DJANGO_DEBUG` | True | Set False in production. |
| `DJANGO_ALLOWED_HOSTS` | localhost,127.0.0.1,0.0.0.0,testserver | Comma-separated list. |
| `AI_PROVIDER` | demo | `demo`, `openai`, or `zai`. |
| `AI_API_KEY` | (empty) | Required when provider is not `demo`. |
| `AI_API_BASE` | (provider default) | Override endpoint. |
| `AI_MODEL` | gpt-4o-mini | Model name. |
| `AI_TIMEOUT_SECONDS` | 30 | LLM call timeout. |
| `AI_MAX_PAGES_PER_REQUEST` | 30 | Hard cap on pages per AI call. |
| `AI_RATE_LIMIT_PER_HOUR` | 60 | Per-user rate limit on AI endpoints. |
| `GTAB_FETCH_METADATA` | 0 | Set to `1` to enable the SSRF-defended URL metadata fetcher. |
| `GHOSTTAB_EXTENSION_TOKEN` | (empty) | Optional shared token for extension auth. |

## Architecture

```
ghosttab/
├── config/                  Django project settings, URLs, WSGI/ASGI
├── apps/
│   ├── accounts/            Custom User (email-based), UserProfile, auth
│   ├── projects/            Project, SavedPage, ActionItem, AIAnalysis
│   ├── sessions/            BrowserSession, extension API, URL metadata fetcher
│   ├── actions/             Cross-project action queue view
│   ├── ai_services/         Provider-agnostic AI service layer + demo data
│   └── core/                Landing page, context processors, ownership helpers
├── templates/
│   ├── base.html
│   ├── partials/            nav, footer, sidebar
│   ├── landing/             index, demo, privacy
│   ├── accounts/            login, signup, settings
│   ├── projects/            dashboard, project_detail, project_form, page_edit
│   ├── sessions/            session_list
│   └── actions/             queue
├── static/
│   ├── css/
│   │   ├── design-system.css    Custom CSS variables + component classes
│   │   ├── tailwind-input.css   @tailwind base/components/utilities
│   │   ├── dist.css             Built Tailwind output (commit this)
│   │   └── extras.css           Small page-specific overrides
│   └── js/
│       └── app.js           Toasts, modals, CSRF helper, reveal-on-scroll
├── extension/               Chrome Manifest V3 extension (separate deliverable)
├── tests/                   33 tests across ownership, CRUD, AI, extension, SSRF
├── tailwind.config.js
├── package.json
├── manage.py
├── requirements.txt
└── .env.example
```

### AI service layer

Every AI feature goes through `apps/ai_services/services.py`. Public functions:

- `group_pages(pages)` — cluster pages into suggested groupings.
- `infer_project_goal(project)` — infer or refresh the project goal.
- `summarize_research(project)` — generate a research summary.
- `generate_next_actions(project)` — produce a fresh list of action items.
- `compare_products(project)` — build a comparison table.

When `AI_PROVIDER=demo` (the default) or when no API key is set, every function returns a deterministic, opinionated result so the product is fully explorable without an API key. When a real provider is configured, calls go to the LLM with strict JSON output validation, timeout handling, rate limiting, and graceful fallback to the demo path on any failure.

### Security model

- **Ownership**: every project-scoped view uses `get_owned_project_or_404(user, project_id)`. Cross-user access returns 404.
- **CSRF**: every POST form and API call is CSRF-protected.
- **URL validation**: `SavedPageForm.clean_url` rejects non-http(s) schemes. The extension API filters `javascript:`, `file:`, etc.
- **SSRF defenses**: `apps/sessions/url_metadata.py` refuses private/loopback/link-local IPs, caps redirects to 3, caps response size at 256 KiB, and is **off by default**.
- **AI input safety**: page content is treated as untrusted text — never executed as instructions.
- **No secret exposure**: no API keys are ever rendered into templates or JS.

## Browser extension

See `extension/README.md` for installation and the permissions policy. In short: the extension reads tabs only when the popup is opened, never in the background, and only sends the ones the user leaves checked.

## Tests

```bash
python manage.py test tests --settings=tests.test_settings
```

33 tests cover:

- Ownership: a user cannot view, edit, or delete another user's project, page, or action.
- CRUD: project create, page add (with URL scheme validation), bulk import (dedup), action toggle (done ↔ pending), project delete (cascades).
- Auth: signup creates user + profile, duplicate email rejected, anonymous redirect from dashboard.
- AI services: every demo function returns the expected shape, persists an `AIAnalysis` record, and handles empty projects gracefully.
- Extension API: health endpoint, login flow, import flow (with `javascript:` URL filtering), page-count limit.
- SSRF: private/loopback/link-local IPs are unsafe; public IPs are safe; fetcher is disabled by default.

## Definition of Done (✅ implemented)

- ✅ Working Django application
- ✅ Polished and animated landing page with interactive hero preview
- ✅ Responsive dashboard with collapsible sidebar, search, filters
- ✅ Project detail workspace (3-column on desktop, single-column on mobile)
- ✅ Manual URL import (single + bulk paste)
- ✅ Real persistence in SQLite
- ✅ Authentication with email-based custom user
- ✅ Ownership checks on every project-scoped endpoint
- ✅ AI integration with deterministic demo fallback (clearly labeled)
- ✅ Search, status filters, task completion, project/page/action deletion
- ✅ Loading (skeleton), empty, success, and error states
- ✅ Setup instructions in this README
- ✅ `.env.example` without real credentials
- ✅ `.gitignore` excluding secrets, venv, databases, generated files
- ✅ Tests for ownership, CRUD, AI services, extension API, SSRF
- ✅ Chrome Manifest V3 extension with manual URL-import fallback

## Known limitations

- Extension auth uses Django session cookies in this first iteration. For multi-tenant production, switch to a per-user API token model.
- AI rate limiting is in-memory (per-process). Swap for Redis in production.
- No async task queue — AI calls are synchronous. Acceptable for low-volume use; add Celery for production scale.
- No email sending configured beyond Django's console backend.
- The URL metadata fetcher is off by default. Enable it explicitly with `GTAB_FETCH_METADATA=1` only if you accept the SSRF surface.

## License

This is a demonstration project. All rights reserved to its author.
