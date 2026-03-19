# Architecture

This document describes the high-level system architecture, data flow, and component relationships for Scholia.

## System Overview

Scholia is a local-first, single-user AI research paper analysis tool with three layers:

1. **Frontend**: Lit web components with client-side routing (TypeScript + Vite)
2. **Backend**: FastAPI REST API serving both the API and static frontend (Python)
3. **Database**: PostgreSQL for persistent storage (sessions, conversations, credentials)

**External integrations:**
- Anthropic Claude (Haiku for analysis, Sonnet for queries)
- Google Gemini (optional)
- Zotero (per-user API keys for library access)
- Notion (OAuth for exporting insights)

No authentication, billing, or user accounts — the app runs as a single local user.

## Data Flow

### Paper Upload and Analysis
```
User uploads PDF
         ↓
Frontend validates file (.pdf only)
         ↓
POST /sessions/new (multipart/form-data)
         ↓
Backend: session_manager.py creates session record
         ↓
pdf_processor.py extracts text with PyMuPDF
         ↓
claude.py (Haiku) generates initial analysis
         ↓
Session data stored in PostgreSQL (sessions, metadata tables)
         ↓
Frontend: redirects to /session/{session_id}
```

### Query/Chat Flow
```
User types question in chat interface
         ↓
Frontend: ask-tab.ts sends message
         ↓
POST /sessions/{session_id}/query
         ↓
Backend: query_service.py processes query
         ↓
claude.py (Sonnet) generates response using:
  - Full paper text
  - Previous conversation history
         ↓
Response stored in conversations table
         ↓
Frontend: displays message
         ↓
User can flag, highlight, or rate message
```

### Zotero Integration Flow
```
User configures Zotero credentials in Settings
         ↓
POST /api/zotero/credentials (api_key, library_id)
         ↓
Stored in user_zotero_credentials table
         ↓
User selects paper from Zotero picker
         ↓
zotero_service.py fetches PDF and metadata from Zotero API
         ↓
Session created with enriched metadata
```

### Notion Export Flow
```
User clicks "Connect Notion" in Settings
         ↓
GET /api/notion/auth (redirects to Notion OAuth)
         ↓
User authorizes in Notion
         ↓
GET /api/notion/callback (receives OAuth code)
         ↓
notion_client.py exchanges code for access_token
         ↓
Token stored in user_notion_credentials table
         ↓
User selects insights to export
         ↓
POST /api/notion/export
         ↓
notion_exporter.py:
  1. Fetches Notion project context (if available)
  2. Generates relevance analysis (Claude Sonnet)
  3. Formats insights for Notion
  4. Creates blocks in Notion database
         ↓
Export confirmation shown to user
```

## Component Architecture

### Frontend Components

**Core Application:**
- `app-root.ts` - Application root
- `router.ts` - Client-side routing

**Pages:**
- `app-shell.ts` - Main app with session list and paper viewer
- `settings-page.ts` - Settings (Zotero, Notion)
- `welcome-page.ts` - Landing/about page
- `manifesto-page.ts` - Manifesto
- `support-page.ts` - Support info

**Session Components:**
- `session-list.ts` - List of paper sessions
- `pdf-viewer.ts` - PDF rendering with pdf.js
- `left-panel.ts` - Sidebar with chat, concepts, outline tabs

**Chat Components:**
- `ask-tab.ts` - Chat interface and query input
- `concepts-tab.ts` - Extracted insights view
- `outline-tab.ts` - PDF table of contents

**Shared Components:**
- `conversation-item.ts` - Individual Q&A message
- `query-input.ts` - Text input with submit
- `loading-spinner.ts` - Loading state
- `feedback-modal.ts` - Thumbs up/down feedback

**Services:**
- `api.ts` - Centralized API client
- `auth.ts` - Local auth stub (always authenticated)
- `session-storage.ts` - Local session persistence

### Backend API Layer

**Main Application:**
- `main.py` - FastAPI app initialization, CORS, static file serving

**API Routes:**
- `sessions.py` - Session CRUD, upload, list endpoints
- `queries.py` - Query/chat endpoints
- `zotero.py` - Zotero credentials and metadata fetching
- `notion.py` - Notion OAuth and export endpoints
- `auth.py` - Local auth stub (returns hardcoded local user)
- `metadata.py` - Paper metadata enrichment
- `settings.py` - User settings endpoints

**Pydantic Models:**
- `session.py` - Session request/response models
- `query.py` - Query request/response models
- `zotero.py` - Zotero credentials models
- `notion.py` - Notion credentials and export models
- `metadata.py` - Paper metadata models

### Core Services Layer

**AI Clients:**
- `claude.py` - Anthropic Claude API client
- `gemini.py` - Google Gemini API client (optional)
- `prompts.py` - AI prompt templates

**Infrastructure:**
- `config.py` - Settings management (pydantic-settings, reads `.env`)
- `database.py` - PostgreSQL connection pool (asyncpg)
- `pdf_processor.py` - PDF text extraction (PyMuPDF)

### Business Logic Layer

**Session Management:**
- `session_manager.py` - Session CRUD, upload handling
- `query_service.py` - Query processing and response generation
- `insight_extractor.py` - Extract and cache key insights
- `metadata_service.py` - Metadata enrichment (CrossRef, PubMed)

**External Integrations:**
- `zotero_service.py` - Zotero API client
- `notion_client.py` - Notion OAuth and API client
- `notion_exporter.py` - Export insights to Notion

**Utilities:**
- `usage_tracker.py` - Track AI token usage per session

### Database Schema

**Users:**
- `users` - Single pre-seeded local user (`id = 'local-user'`)
- `user_zotero_credentials` - Zotero API key and library ID
- `user_notion_credentials` - Notion OAuth access token

**Paper Sessions & Analysis:**
- `sessions` - Paper analysis sessions
- `conversations` - Chat messages (user and assistant)
- `metadata` - Extracted paper metadata
- `insights` - Cached extracted insights (updated on new exchanges)

**User Interactions:**
- `flags` - User-flagged exchanges
- `highlights` - Saved text selections
- `message_evaluations` - Thumbs up/down feedback

**External Integrations:**
- `notion_project_cache` - Cached Notion project context

**Usage Tracking:**
- `token_usage` - AI API token consumption per call
- `user_events` - Session activity log

## Technology Stack

### Frontend
- **Framework**: Lit 3.1 (web components)
- **Language**: TypeScript 5.3 (strict mode)
- **Build Tool**: Vite 5.0
- **PDF Rendering**: pdf.js 3.11
- **Styling**: Custom CSS with design tokens

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Server**: Uvicorn
- **Database**: PostgreSQL (asyncpg driver)
- **PDF Processing**: PyMuPDF
- **HTTP Client**: httpx, aiohttp

### AI & External APIs
- **AI Models**:
  - Anthropic Claude Haiku (initial paper analysis)
  - Anthropic Claude Sonnet (queries, Notion export)
  - Google Gemini Flash/Pro (optional)
- **Integrations**:
  - Zotero API (pyzotero)
  - Notion API (notion-client)

### Infrastructure
- **Local**: Docker Compose (PostgreSQL + app container)
- **Manual**: Python + PostgreSQL + Node.js

## Local User Model

Scholia runs as a single local user — no login required. The backend's `require_active` and `require_admin` dependencies always return a hardcoded user:

```python
LOCAL_USER = {
    "id": "local-user",
    "email": "local@localhost",
    "name": "Local User",
    "is_admin": True,
}
```

This user is pre-seeded in the database on first run. All sessions, conversations, and credentials are stored under this user ID.

## Security Considerations

1. **API Keys**: Never exposed to the frontend
   - `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` — server-side only
   - Notion OAuth secrets — server-side only

2. **Input Validation**:
   - File uploads: `.pdf` only
   - Database queries: parameterized (SQL injection prevention)

3. **Network**: Intended for `localhost` use only; do not expose port 8000 to the public internet without adding authentication

## Performance Optimizations

1. **Caching**:
   - Extracted insights cached in `insights` table (avoids re-extracting on every concepts view)
   - Notion project context cached in `notion_project_cache` table

2. **AI Model Selection**:
   - Haiku for initial analysis (fast)
   - Sonnet for complex queries (higher quality)

3. **Database**:
   - Connection pooling (asyncpg)
   - Indexed columns: `session_id`, `created_at`
   - Soft delete for conversations (preserves history, fast queries with partial index)

## Deployment

### Docker (recommended)

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env
docker-compose up
# App available at http://localhost:8000
```

The `docker-compose.yml` starts PostgreSQL and the app container. The database schema is applied automatically on first run.

### Manual

```bash
# 1. Start PostgreSQL and apply schema
createdb scholia
psql scholia < web/db/schema.sql

# 2. Install Python dependencies
pip install -r requirements-web.txt

# 3. Build frontend
cd frontend && npm install && npm run build && cd ..

# 4. Set environment variables
cp .env.example .env  # fill in ANTHROPIC_API_KEY

# 5. Start server
uvicorn web.api.main:app --reload --port 8000
```

## Testing

```bash
pytest tests/
```

Tests cover session management, query routing, Zotero routes, and core models.
