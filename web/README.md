# Scholia Backend

FastAPI backend for Scholia. Serves the REST API and static frontend.

## Development

**Prerequisites:** Python 3.11+, PostgreSQL 16+

```bash
pip install -r requirements-web.txt
uvicorn web.api.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs

## Structure

```
web/
├── api/
│   ├── main.py           # FastAPI app, middleware, static file serving
│   ├── routes/
│   │   ├── auth.py       # Local auth stub (hardcoded single user)
│   │   ├── sessions.py   # Session CRUD, PDF upload, Zotero import
│   │   ├── queries.py    # Chat queries, flags, highlights, evaluations
│   │   ├── zotero.py     # Zotero credentials and library access
│   │   ├── notion.py     # Notion OAuth and export
│   │   ├── metadata.py   # Paper metadata enrichment
│   │   └── settings.py   # User settings
│   └── models/           # Pydantic request/response models
├── core/
│   ├── config.py         # Settings (pydantic-settings, reads .env)
│   ├── database.py       # PostgreSQL connection pool (asyncpg)
│   ├── claude.py         # Anthropic API client
│   ├── gemini.py         # Google Gemini client (optional)
│   ├── pdf_processor.py  # PDF text extraction (PyMuPDF)
│   └── prompts.py        # AI prompt templates
├── services/
│   ├── session_manager.py    # Session CRUD and PDF processing
│   ├── query_service.py      # Query handling and response generation
│   ├── insight_extractor.py  # Extract and cache insights
│   ├── metadata_service.py   # Metadata enrichment (CrossRef, PubMed)
│   ├── zotero_service.py     # Zotero API client
│   ├── notion_client.py      # Notion OAuth client
│   ├── notion_exporter.py    # Export insights to Notion
│   └── usage_tracker.py      # AI token usage tracking
└── db/
    ├── schema.sql            # Full database schema (applied on startup)
    └── migrations/           # Historical migrations (reference only)
```

## Configuration

Copy `.env.example` from the repo root and fill in your values:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `DATABASE_URL` | No | PostgreSQL URL (defaults to `postgresql://scholia:scholia@localhost:5432/scholia`) |
| `GOOGLE_API_KEY` | No | Google Gemini API key |
| `NOTION_CLIENT_ID` | No | Notion OAuth app ID |
| `NOTION_CLIENT_SECRET` | No | Notion OAuth app secret |
| `NOTION_REDIRECT_URI` | No | Notion callback URL (default: `http://localhost:8000/api/notion/callback`) |

## API Endpoints

### Sessions
- `POST /sessions/new` — Create session from PDF upload or Zotero key
- `GET /sessions` — List sessions (paginated)
- `GET /sessions/{id}` — Get session with conversation history
- `DELETE /sessions/{id}` — Delete session

### Queries
- `POST /sessions/{id}/query` — Ask a question about the paper
- `POST /sessions/{id}/exchanges/{eid}/flag` — Flag an exchange
- `DELETE /sessions/{id}/exchanges/{eid}/flag` — Unflag
- `POST /sessions/{id}/highlights` — Add a text highlight
- `GET /sessions/{id}/highlights` — List highlights
- `DELETE /sessions/{id}/highlights/{hid}` — Delete highlight

### Insights
- `GET /sessions/{id}/concepts` — Get extracted insights (cached)

### Zotero
- `GET /api/zotero/credentials` — Get saved credentials
- `POST /api/zotero/credentials` — Save credentials
- `DELETE /api/zotero/credentials` — Remove credentials
- `GET /zotero/search` — Search library
- `GET /zotero/recent` — List recent items

### Notion
- `GET /api/notion/auth` — Start Notion OAuth flow
- `GET /api/notion/callback` — OAuth callback
- `POST /api/notion/export` — Export insights to Notion

### Misc
- `GET /health` — Health check
- `GET /api/auth/me` — Current user (always returns local user)
- `GET /api/config` — App config (Gemini availability, etc.)

## Authentication

No real authentication — all routes return a hardcoded local user. The `require_active` and `require_admin` FastAPI dependencies both return:

```python
{"id": "local-user", "email": "local@localhost", "name": "Local User", "is_admin": True}
```

This user is pre-seeded in the database by `schema.sql`.

## Testing

```bash
pytest tests/
pytest tests/test_sessions_routes.py  # specific file
pytest -v                              # verbose
```
