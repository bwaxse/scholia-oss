# Claude Code Context

## Project: Scholia (Paper Companion)

AI-powered research paper analysis tool with Zotero and Notion integration.

## Additional Context Files

For detailed information about specific parts of the codebase, see:

- **[frontend/CLAUDE.md](frontend/CLAUDE.md)** - Frontend architecture, component patterns, and design system
- **[web/CLAUDE.md](web/CLAUDE.md)** - Backend API, services, database patterns, and integrations
- **[tests/CLAUDE.md](tests/CLAUDE.md)** - Testing patterns, fixtures, and mocking strategies
- **[docs/CLAUDE.md](docs/CLAUDE.md)** - Documentation guidelines and maintenance workflow

This file provides the overall project overview and cross-cutting concerns.

## Agent Usage

When working with this project:
- Use `augment-context-engine` when searching for information about the project

## Production

- **Domain:** https://scholia.fyi
- **Support Email:** support@scholia.fyi
- **Hosting:** Render (web service + PostgreSQL)
- **Repository:** https://github.com/bwaxse/scholia

## Architecture

- **Backend:** FastAPI (Python) - serves API and static frontend
- **Frontend:** Lit + TypeScript (built to `frontend/dist/`)
- **Database:** PostgreSQL (Render managed)
- **AI:** Anthropic Claude (Haiku for analysis, Sonnet for queries) and Google Gemini (optional)

## Architecture Overview

Directory structure:
```
scholia/
├── frontend/           # Lit + TypeScript (Vite build)
│   ├── src/
│   │   ├── components/ # Web components
│   │   ├── pages/      # Page-level components
│   │   ├── services/   # API client
│   │   └── styles/     # CSS and theme
│   └── dist/           # Built frontend (served by backend)
├── web/                # FastAPI Python backend
│   ├── api/
│   │   ├── main.py     # FastAPI app entry
│   │   ├── routes/     # API endpoints
│   │   └── models/     # Pydantic models
│   ├── core/           # Core services (Claude, Gemini, DB, PDF)
│   ├── services/       # Business logic
│   └── db/             # Database schema
├── tests/              # Python tests (pytest)
├── migrations/         # Database migrations
└── docs/               # Documentation
```

## Key Integrations

### Google OAuth
- Multi-user authentication via Google
- App-wide OAuth credentials: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- Provider credentials stored in `user_providers` table
- Login flow: `/api/auth/login?provider=google`
- Callback URL: `https://scholia.fyi/api/auth/callback`

### GitHub OAuth
- Multi-user authentication via GitHub
- App-wide OAuth credentials: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`
- Provider credentials stored in `user_providers` table
- Login flow: `/api/auth/login?provider=github`
- Callback URL: `https://scholia.fyi/api/auth/callback`

### Zotero
- Per-user credentials stored in `user_zotero_credentials` table
- Users configure in Settings page
- No global/environment Zotero credentials
- Requires user API key and library ID

### Notion
- OAuth flow for multi-user support
- App-wide OAuth credentials: `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI`
- User access tokens stored in `user_notion_credentials` table
- Callback URL: `https://scholia.fyi/api/notion/callback`

## Environment Variables (Production)

Required:
- `ANTHROPIC_API_KEY` - Claude API key
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET_KEY` - For secure session cookies
- `GOOGLE_API_KEY` - Google Gemini API key (required for Gemini functionality)
- `GOOGLE_OAUTH_CLIENT_ID` - Google OAuth app ID (required for authentication)
- `GOOGLE_OAUTH_CLIENT_SECRET` - Google OAuth app secret (required for authentication)
- `GITHUB_OAUTH_CLIENT_ID` - GitHub OAuth app ID (required for authentication)
- `GITHUB_OAUTH_CLIENT_SECRET` - GitHub OAuth app secret (required for authentication)
- `NOTION_CLIENT_ID` - Notion OAuth app ID (required for Notion integration)
- `NOTION_CLIENT_SECRET` - Notion OAuth app secret (required for Notion integration)
- `NOTION_REDIRECT_URI` - `https://scholia.fyi/api/notion/callback` (required for Notion OAuth)

Optional:
- `BASE_URL` - Base URL for OAuth callbacks (defaults to `https://scholia.fyi`)

## Database Tables

**Users & Authentication:**
- `users` - OAuth authenticated users (Google, GitHub) with banning support
- `user_providers` - Multiple OAuth providers per user
- `user_sessions` - Login session tracking

**User Credentials (Per-User):**
- `user_zotero_credentials` - Zotero API keys
- `user_notion_credentials` - Notion OAuth access tokens

**Paper Sessions & Analysis:**
- `sessions` - Paper analysis sessions (includes `label` field)
- `conversations` - Chat messages (user and assistant)
- `metadata` - Extracted paper metadata
- `insights` - Cached extracted insights

**User Interactions:**
- `flags` - User-flagged exchanges
- `highlights` - Saved text selections
- `message_evaluations` - Thumbs up/down feedback

**External Integrations:**
- `notion_project_cache` - Cached Notion project context

**Usage Tracking:**
- `token_usage` - AI API token consumption
- `user_events` - User activity tracking

## Development

```bash
# Backend
uvicorn web.api.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

Local URLs:
- Frontend dev: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Repository Etiquette

**Branching:**
- ALWAYS create a feature branch before starting major changes
- NEVER commit directly to `main`
- Branch naming: `feature/description` or `fix/description`

**Git workflow for major changes:**
1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Develop and commit on the feature branch
3. Test locally before pushing:
   - Backend: `uvicorn web.api.main:app --reload --port 8000`
   - Frontend: `cd frontend && npm run dev`
   - Frontend build: `cd frontend && npm run build` (catches TypeScript errors)
4. Push the branch: `git push -u origin feature/your-feature-name`
5. Create a PR to merge into `main`
6. Use the `/update-docs-and-commit` slash command for commits - ensures docs are updated alongside code changes

**Commits:**
- Write clear commit messages describing the change
- Keep commits focused on single changes
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

**Pull Requests:**
- Create PRs for all changes to `main`
- NEVER force push to `main`
- Include description of what changed and why

## Workflow Preferences

- When editing documents, pause after each discrete edit and confirm before proceeding.
- Do not batch-apply multiple edits without review.

**Before pushing:**
1. Run `cd frontend && npm run build` to catch TypeScript errors
2. Test backend endpoints manually or with existing tests

## Constraints & Policies

**Security - MUST follow:**
- NEVER expose `*_API_KEY`, `*_SECRET`, or `*_SECRET_KEY` to the client - server-side only
- ALWAYS use environment variables for secrets
- NEVER commit `.env` or any file with API keys
- Validate and sanitize all user input
- Use parameterized queries for all database operations
- OAuth secrets must remain server-side only

**Code quality:**
- TypeScript strict mode enabled (`frontend/tsconfig.json`)
- Run `cd frontend && npm run build` before committing frontend changes
- No `any` types without justification
- Follow existing code patterns and conventions
- Keep functions focused and modular

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow
- [Changelog](docs/changelog.md) - Version history
- [README](README.md) - Quick start and overview
- [API Reference](web/API.md) - Complete API endpoint documentation
- [Design System](DESIGN_SYSTEM.md) - Visual design guidelines

**Maintenance:**
- Update `docs/architecture.md` after structural changes (new services, tables, integrations)
- Update `docs/changelog.md` after user-facing features, API changes, or bug fixes
- Use the `/update-docs-and-commit` slash command when making git commits

 ## Stripe Integration

- When working with Stripe API objects, always access nested data through `items.data[0]` for subscription details. Never use `.get()` or direct attribute access for period dates.

---

## Prompt and Workflow Coaching Hooks

The user has prompt-type hooks that provide coaching feedback. When any hook output appears in conversation context (from `UserPromptSubmit`, `PreToolUse`, `PostToolUseFailure`, `Notification`, or `TaskCompleted` events), always surface its content to the user verbatim before proceeding. Do NOT silently absorb hook feedback — the user wants to see it. Only suppress if the hook output is a simple "looks good" confirmation (e.g., "✓ Prompt looks clear!", "✓ Safe edit area - proceed!").