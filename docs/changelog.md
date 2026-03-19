# Changelog

All notable changes to Scholia will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-03-19

Initial open-source release. Scholia is now a local-first, single-user tool — no accounts, no billing, bring your own API key.

### Added
- **Docker Compose setup** — `docker-compose up` starts PostgreSQL and the app; no manual database configuration needed
- **`.env.example`** — template for required environment variables (`ANTHROPIC_API_KEY`, optional Gemini and Notion keys)

### Changed
- **No authentication required** — app runs as a hardcoded local user; no OAuth, no login page
- **No credits or subscriptions** — all AI models available without restrictions; no credit checks on paper uploads or queries
- **Default database URL** — `DATABASE_URL` defaults to `postgresql://scholia:scholia@localhost:5432/scholia` for zero-config local use
- **All models unlocked** — Haiku, Sonnet, Gemini Flash, and Gemini Pro all available (Gemini requires `GOOGLE_API_KEY`)

### Removed
- Google and GitHub OAuth authentication
- Stripe subscription and credit system
- Admin, credits, subscriptions, and webhooks API routes
- Onboarding and pricing pages
- Credit badge and balance display in UI
- Session middleware (no longer needed without OAuth state)
- `authlib`, `itsdangerous`, `stripe` Python dependencies

### Features included in this release
- PDF upload and text extraction (PyMuPDF)
- AI-powered initial paper analysis (Claude Haiku)
- Interactive chat with full paper context (Claude Sonnet)
- Zotero library integration (configure API key in Settings)
- Notion export with project context awareness (configure OAuth in Settings)
- Conversation history across sessions
- Text highlights and flagged exchanges
- Extracted insights view (Concepts tab)
- PDF outline navigation
- Message thumbs up/down feedback
- Session labels for organizing multiple analyses of the same paper
- Optional Gemini Flash/Pro models
