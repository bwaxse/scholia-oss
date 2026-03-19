# Architecture

This document describes the high-level system architecture, data flow, and component relationships for Scholia.

## System Overview

Scholia is an AI-powered research paper analysis tool with three main layers:

1. **Frontend**: Lit web components with client-side routing (TypeScript + Vite)
2. **Backend**: FastAPI REST API serving both the API and static frontend (Python)
3. **Database**: PostgreSQL for persistent storage (users, sessions, conversations, credentials)

**External integrations:**
- Anthropic Claude (Haiku for analysis, Sonnet for queries)
- Google Gemini (optional, some features)
- Zotero (per-user API keys for library access)
- Notion (OAuth for exporting insights)
- Google OAuth (authentication)
- GitHub OAuth (authentication)
- Stripe (subscription and credit top-up payment processing)

## Data Flow

### Paper Upload and Analysis
```
User uploads PDF
         ↓
Frontend: app-upload-modal.ts validates file (max 50MB, .pdf)
         ↓
POST /sessions/upload (multipart/form-data)
         ↓
Backend: session_manager.py creates session record
         ↓
pdf_processor.py extracts text with PyMuPDF
         ↓
claude.py (Haiku 4.5) generates initial analysis
         ↓
insight_extractor.py extracts key insights (cached)
         ↓
Session data stored in PostgreSQL (sessions, metadata, insights tables)
         ↓
Frontend: redirects to /session/{session_id}
```

### Query/Chat Flow
```
User types question in chat interface
         ↓
Frontend: app-chat-panel.ts sends message
         ↓
POST /sessions/{session_id}/queries
         ↓
Backend: query_service.py processes query
         ↓
claude.py (Sonnet 4.5) generates response using:
  - Full paper text
  - Previous conversation history
  - Extracted insights (if available)
         ↓
Response stored in conversations table
         ↓
Frontend: displays message with streaming support
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
User uploads PDF with Zotero key field filled
         ↓
zotero_service.py fetches metadata from Zotero API
         ↓
Enriched metadata stored in sessions table
         ↓
Frontend displays Zotero metadata in session view
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

### Subscription and Credit Flow

**Free Tier Signup (Automatic):**
```
New user completes OAuth signup
         ↓
Backend: get_or_create_user() detects new user
         ↓
Free tier subscription created automatically
         ↓
CreditService grants 5 monthly credits
         ↓
Credits recorded in credit_transactions table
         ↓
User redirected to /onboarding (sees credit balance)
```

**Paid Tier Upgrade:**
```
User initiates subscription upgrade
         ↓
GET /api/subscriptions/tiers (list available tiers)
         ↓
POST /api/subscriptions/checkout (create Stripe checkout)
         ↓
Backend: SubscriptionService.create_checkout()
         ↓
Stripe API returns checkout session URL
         ↓
User redirects to Stripe Checkout
         ↓
User completes payment
         ↓
POST /api/webhooks/stripe (Stripe sends webhook event)
         ↓
Backend: verify webhook signature (idempotency check)
         ↓
SubscriptionService processes subscription created/updated event
         ↓
CreditService grants monthly credits to user
         ↓
User subscription active, credits available

---

User initiates credit top-up purchase
         ↓
GET /api/credits/packages (list credit packages)
         ↓
POST /api/credits/checkout (create Stripe checkout)
         ↓
Backend: SubscriptionService.create_topup_checkout()
         ↓
User completes payment → Stripe webhook
         ↓
CreditService.grant_credits() adds credits to top-up pool
         ↓
Credits available for use

---

User analyzes paper or sends query
         ↓
POST /sessions/new or POST /sessions/{id}/query
         ↓
Backend: check credit balance (CreditService.get_balance())
         ↓
If insufficient credits: return 402 (Payment Required)
         ↓
Process request and deduct credits (CreditService.deduct_credits())
         ↓
Deduction priority: monthly → rollover → top_up
         ↓
Request completed, credits updated
```

## Component Architecture

### Frontend Components

**Core Application:**
- `app-root.ts` - Main application shell, routing, session management
- `router.ts` - Client-side routing with @lit-labs/router

**Pages:**
- `app-home.ts` - Landing page with session list
- `app-session-view.ts` - Session detail page with PDF + chat
- `app-settings.ts` - User settings (Zotero, Notion, account)
- `app-login.ts` - OAuth login page
- `onboarding-page.ts` - New user welcome page (shows credits, account info, feature overview)

**Session Components:**
- `app-upload-modal.ts` - PDF upload dialog
- `app-session-card.ts` - Session preview card
- `pdf-viewer.ts` - PDF rendering with pdf.js
- `left-panel.ts` - Sidebar with session list and credit balance badge showing remaining credits (auto-refreshes after queries)

**Chat Components:**
- `app-chat-panel.ts` - Chat interface
- `app-chat-message.ts` - Individual message display
- `app-prompt-suggestions.ts` - Suggested queries

**Settings Components:**
- `app-zotero-settings.ts` - Zotero credentials form
- `app-notion-settings.ts` - Notion OAuth connection

**Services:**
- `api-client.ts` - Centralized API client with fetch wrappers

### Backend API Layer

**Main Application:**
- `main.py` - FastAPI app initialization, CORS, static file serving

**API Routes:**
- `sessions.py` - Session CRUD, upload, list endpoints
- `queries.py` - Query/chat endpoints
- `zotero.py` - Zotero credentials and metadata fetching
- `notion.py` - Notion OAuth and export endpoints
- `auth.py` - OAuth login/logout/callback (Google, GitHub)
- `metadata.py` - Paper metadata enrichment
- `linkedin.py` - LinkedIn post generation
- `insights.py` - Extract and cache paper insights
- `subscriptions.py` - Subscription checkout and tier listing
- `credits.py` - Credit balance, packages, and top-up checkout
- `webhooks.py` - Stripe webhook event processing
- `health.py` - Health check endpoint

**Pydantic Models:**
- `session.py` - Session request/response models
- `query.py` - Query request/response models
- `zotero.py` - Zotero credentials models
- `notion.py` - Notion credentials and export models
- `metadata.py` - Paper metadata models

### Core Services Layer

**AI Clients:**
- `claude.py` - Anthropic Claude API client (Haiku 4.5, Sonnet 4.5)
- `gemini.py` - Google Gemini API client (optional)
- `prompts.py` - AI prompt templates (system prompts, task prompts)

**Infrastructure:**
- `config.py` - Settings management with pydantic-settings
- `database.py` - PostgreSQL connection pool management
- `pdf_processor.py` - PDF text extraction with PyMuPDF

### Business Logic Layer

**Session Management:**
- `session_manager.py` - Session CRUD, upload handling
- `query_service.py` - Query processing and response generation
- `insight_extractor.py` - Extract and cache key insights
- `metadata_service.py` - Metadata enrichment

**Subscription & Billing:**
- `credit_service.py` - Credit balance management, deductions, grants, monthly refresh
- `subscription_service.py` - Stripe subscription checkout, tier management, webhook processing
- `stripe_client.py` - Stripe API wrapper with retry logic for customers, subscriptions, checkouts, and GDPR-compliant customer anonymization

**External Integrations:**
- `zotero_service.py` - Zotero API client
- `notion_client.py` - Notion OAuth and API client
- `notion_exporter.py` - Export insights to Notion

**Content Generation:**
- `linkedin_generator.py` - Generate LinkedIn posts from papers

**User Management:**
- `auth_service.py` - OAuth flow handling (Google, GitHub)
- `user_anonymization_service.py` - GDPR-compliant account deletion with soft delete and anonymization
- `usage_tracker.py` - Track AI token usage

### Database Schema

**Users & Authentication:**
- `users` - OAuth authenticated users (Google, GitHub) with banning and soft delete support (`deleted_at`, `deletion_type` columns)
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

**Subscriptions & Billing:**
- `subscription_tiers` - Available subscription tier definitions
- `user_subscriptions` - Active user subscriptions with tier and renewal dates
- `credit_balances` - User credit balances across 4 pools (monthly, rollover, top_up, bonus) stored as NUMERIC(10,2) for precise fractional deductions
- `credit_transactions` - Audit log of all credit additions and deductions
- `credit_top_ups` - User credit purchase history via Stripe
- `stripe_webhook_events` - Webhook event log for idempotency and debugging (stores metadata only: event_type, customer_id, subscription_id, invoice_id, amount_cents; full payloads are not stored)

**External Integrations:**
- `notion_project_cache` - Cached Notion project context

**Usage Tracking:**
- `token_usage` - AI API token consumption
- `user_events` - User activity tracking

## Technology Stack

### Frontend
- **Framework**: Lit 3.1 (web components)
- **Language**: TypeScript 5.3 (strict mode)
- **Build Tool**: Vite 5.0
- **Routing**: @lit-labs/router
- **PDF Rendering**: pdf.js 3.11
- **Styling**: Custom CSS with design tokens (see DESIGN_SYSTEM.md)

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Server**: Uvicorn
- **Database**: PostgreSQL (asyncpg driver)
- **PDF Processing**: PyMuPDF
- **HTTP Client**: httpx, aiohttp
- **Retry Logic**: tenacity (exponential backoff for Stripe API)

### AI & External APIs
- **AI Models**:
  - Anthropic Claude Haiku 4.5 (initial analysis)
  - Anthropic Claude Sonnet 4.5 (queries, Notion export)
  - Google Gemini (optional, some features)
- **Integrations**:
  - Zotero API (pyzotero)
  - Notion API (notion-client)
  - Google OAuth (authlib)
  - GitHub OAuth (authlib)
  - Stripe API (stripe Python SDK)

### Infrastructure
- **Hosting**: Render
  - Web service (free tier)
  - PostgreSQL database (free tier)
- **Build**: bash build script (`build.sh`)
- **Deployment**: Automatic on push to `main` branch

## Authentication Flow

### OAuth Login (Google or GitHub)

1. User clicks "Sign in with Google" or "Sign in with GitHub"
2. Frontend redirects to `/api/auth/login?provider={google|github}`
3. Backend generates OAuth authorization URL with state token
4. User redirects to OAuth provider (Google/GitHub)
5. User authorizes app
6. OAuth provider redirects to `/api/auth/callback?code=...&state=...`
7. Backend:
   - Validates state token
   - Exchanges code for access_token
   - Fetches user profile from provider
   - Creates or updates user in `users` table
   - Creates/updates entry in `user_providers` table
   - Detects if this is a new user account
   - Creates session cookie (httponly, secure)
8. **New users**: Redirects to `/onboarding` page with welcome message and available credits
9. **Existing users**: Redirects to frontend home page (`/`)
10. Frontend fetches `/api/auth/me` to get user info

### Onboarding Flow (New Users)

1. User completes OAuth signup
2. Backend detects new user and redirects to `/onboarding`
3. Onboarding page displays:
   - Welcome message
   - Account information (email, plan tier)
   - Available credit balance (auto-populated)
   - Feature list for free tier
   - CTAs to start analyzing or view pricing
4. User can navigate to home page or pricing from onboarding

### Session Management

- **Session Cookie**: httponly, secure, signed with `SESSION_SECRET_KEY`
- **Expiration**: 30 days (configurable)
- **User Info Endpoint**: `/api/auth/me` returns current user or 401
- **Logout**: `/api/auth/logout` clears session cookie

## Security Considerations

1. **API Keys**: Never exposed to frontend
   - `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` - server-side only
   - OAuth secrets (`*_CLIENT_SECRET`) - server-side only

2. **User Credentials**: Stored per-user in database
   - Zotero API keys encrypted at rest (database-level encryption)
   - Notion access tokens encrypted at rest

3. **Input Validation**:
   - File uploads: max 50MB, .pdf only
   - User input: sanitized before AI queries
   - Database queries: parameterized (SQL injection prevention)

4. **CORS**: Configured for production domain only (`https://scholia.fyi`)

5. **Session Security**:
   - httponly cookies (no JavaScript access)
   - secure flag (HTTPS only)
   - signed with secret key (tamper-proof)

## Performance Optimizations

1. **Caching**:
   - Extracted insights cached in `insights` table (reduces AI calls)
   - Notion project context cached in `notion_project_cache` table

2. **AI Model Selection**:
   - Haiku 4.5 for initial analysis (fast, cost-effective)
   - Sonnet 4.5 for complex queries (higher quality)

3. **Frontend**:
   - Lazy loading of PDF pages
   - Virtualized chat message rendering
   - Code splitting with Vite

4. **Database**:
   - Connection pooling (asyncpg)
   - Indexed columns: `user_id`, `session_id`, `created_at`
   - Soft delete for conversations (preserves history)

## Deployment

### Production Deployment (Render)

1. Push to `main` branch
2. Render automatically:
   - Runs `build.sh` (installs Python deps, builds frontend)
   - Starts service with `uvicorn web.api.main:app --host 0.0.0.0 --port $PORT`
3. Database migrations run manually:
   ```bash
   psql $DATABASE_URL < migrations/001_add_session_label.sql
   ```

### Local Development

**Backend:**
```bash
# Install dependencies
pip install -r requirements-web.txt

# Run development server
uvicorn web.api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

**Database:**
- Use local PostgreSQL or connect to Render database
- Run schema: `psql $DATABASE_URL < web/db/schema.sql`

## Testing

- **Backend Testing**: pytest with unit and integration tests
  - CreditService tests (balance calculations, permissions, deductions, grants)
  - Stripe webhook integration tests (signature verification, idempotency, event routing)
- **Frontend Testing**: Manual testing via development server
- **Local Development**: `pytest tests/` to run backend test suite

## Future Enhancements

- **Email Notifications**: Implement email alerts for:
  - Low credit warnings (when balance < 10 credits)
  - Payment failure notifications
  - Monthly billing receipts and renewal confirmations
  - Subscription upgrade/downgrade confirmations
  - See TESTING_TODO.md for email notification test cases
- **Linting**: Configure black, ruff, mypy for backend
- **Frontend Testing**: Add unit tests for components
- **CI/CD**: Add GitHub Actions for automated testing and deployment
- **Monitoring**: Add error tracking (Sentry) and analytics
- **Annual Billing**: Add yearly subscription discount option (e.g., $100/year vs $144/year)
- **Enterprise Tier**: Add unlimited tier for team/enterprise customers
- **Credit Gifting**: Allow users to gift credits to other users
- **Usage Analytics Dashboard**: User-facing analytics showing credit usage patterns
