# Backend Context

> See also: [Root CLAUDE.md](../CLAUDE.md) for overall architecture

## Stack

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Server**: Uvicorn
- **Database**: PostgreSQL (asyncpg driver)
- **PDF Processing**: PyMuPDF
- **HTTP Client**: httpx, aiohttp

## Directory Structure

```
web/
├── api/
│   ├── main.py           # FastAPI app entry point
│   ├── routes/           # API endpoint modules
│   │   ├── auth.py       # OAuth login/logout (Google, GitHub)
│   │   ├── sessions.py   # Paper session management
│   │   ├── queries.py    # Chat queries
│   │   ├── subscriptions.py  # Subscription management
│   │   ├── credits.py    # Credit management
│   │   ├── webhooks.py   # Stripe webhooks
│   │   ├── zotero.py     # Zotero integration
│   │   ├── notion.py     # Notion integration
│   │   ├── metadata.py   # Paper metadata
│   │   └── admin.py      # Admin endpoints
│   └── models/           # Pydantic request/response models
├── core/
│   ├── config.py         # Settings (pydantic-settings)
│   ├── database.py       # PostgreSQL connection pool
│   ├── claude.py         # Anthropic Claude API client
│   ├── gemini.py         # Google Gemini API client
│   ├── pdf_processor.py  # PDF text extraction
│   └── stripe_client.py  # Stripe API wrapper
├── services/
│   ├── session_manager.py      # Session CRUD operations
│   ├── query_service.py        # Query processing
│   ├── credit_service.py       # Credit management
│   ├── subscription_service.py # Subscription management
│   ├── zotero_service.py       # Zotero API client
│   ├── notion_client.py        # Notion OAuth client
│   ├── notion_exporter.py      # Export to Notion
│   ├── linkedin_generator.py   # LinkedIn post generation
│   ├── auth_service.py         # OAuth flow handling
│   └── usage_tracker.py        # Token usage tracking
└── db/
    ├── schema.sql        # Complete database schema
    └── migrations/       # Historical schema changes
```

## Key Patterns

### Service Layer Pattern

All business logic lives in services with singleton pattern:

```python
from web.services import get_credit_service

# In route handler
credit_service = get_credit_service()
balance = await credit_service.get_credit_balance(user_id)
```

### Database Access

Use asyncpg with raw SQL (not ORM):

```python
from web.core.database import get_db_manager

db_manager = get_db_manager()

# Simple query
rows = await db_manager.execute_query(
    "SELECT * FROM users WHERE id = $1",
    user_id
)

# Transaction
async with db_manager.transaction() as conn:
    await conn.execute("UPDATE users SET ... WHERE id = $1", user_id)
    await conn.execute("INSERT INTO logs ...")
```

### Authentication

Use dependency injection for auth:

```python
from web.api.routes.auth import require_active, require_admin

@router.get("/protected")
async def protected_route(user: Dict = Depends(require_active)):
    user_id = user["id"]
    is_admin = user.get("is_admin", False)
    ...
```

**Auth dependencies:**
- `require_active`: Requires authenticated user (not banned)
- `require_admin`: Requires admin user (`is_admin=True`)

**Admin Exemptions:**
- Admins bypass credit checks and model restrictions
- Check with: `if not user.get("is_admin"):`

### Credit Enforcement

Always check credits before expensive operations:

```python
from web.services.credit_service import get_credit_service

credit_service = get_credit_service()

# Skip for admins
if not user.get("is_admin"):
    can_perform, reason, required = await credit_service.check_can_perform_operation(
        user_id, "paper_analysis"
    )
    if not can_perform:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # Deduct after success
    await credit_service.deduct_credits(
        user_id=user_id,
        amount=required,
        operation_type="paper_analysis",
        session_id=session_id
    )
```

### Configuration

All settings via environment variables:

```python
from web.core.config import get_settings

settings = get_settings()
api_key = settings.anthropic_api_key
stripe_key = settings.stripe_secret_key
```

**Required env vars:**
- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `SESSION_SECRET_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`

## API Design

### Route Organization

Routes are organized by resource:
- `/api/auth/*` - Authentication (login, logout, callback)
- `/sessions/*` - Paper sessions
- `/sessions/{id}/query` - Chat queries
- `/api/subscriptions/*` - Subscription management
- `/api/credits/*` - Credit management
- `/api/webhooks/*` - External webhooks (Stripe)
- `/zotero/*` - Zotero operations
- `/api/notion/*` - Notion operations
- `/metadata/*` - Paper metadata
- `/api/admin/*` - Admin operations

### Response Patterns

**Success:**
```python
return {
    "status": "success",
    "data": {...}
}
```

**Error:**
```python
raise HTTPException(
    status_code=400,
    detail={
        "error": "error_code",
        "message": "Human-readable message",
        "field": "field_name"  # optional
    }
)
```

**Credit errors:**
- `402 Payment Required` - Insufficient credits
- `403 Forbidden` - Model restricted by tier

### Pydantic Models

Located in `web/api/models/`:

```python
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    model: str = "sonnet"
    highlighted_text: Optional[str] = None
```

## Database Schema

See [../docs/architecture.md](../docs/architecture.md#database-schema) for complete table list.

**Key tables:**
- `users` - OAuth authenticated users
- `user_subscriptions` - Subscription tier and status
- `credit_balances` - Current credit balances (4 pools)
- `credit_transactions` - Audit log of credit operations
- `sessions` - Paper analysis sessions
- `conversations` - Chat messages
- `stripe_webhook_events` - Webhook idempotency

## AI Integration

### Claude (Anthropic)

```python
from web.core.claude import get_claude_client

claude = get_claude_client()
response = await claude.generate_response(
    messages=[...],
    model="claude-sonnet-4-6",
    system="You are a research assistant..."
)
```

**Models:**
- `claude-haiku-4-5` - Fast, cheap (paper analysis)
- `claude-sonnet-4-6` - Balanced (queries)
- `claude-opus-4-6` - Best quality (premium tier only)

**Credit costs:**
- Flash: 1 credit
- Haiku: 2 credits
- Sonnet: 8 credits
- Opus: 10 credits
- Paper load: 20 credits

### Gemini (Google)

Optional, used for some features:

```python
from web.core.gemini import get_gemini_client, is_gemini_available

if is_gemini_available():
    gemini = get_gemini_client()
    response = await gemini.generate(...)
```

## Subscription System

### Tiers

- **Free**: 100 credits/month, Haiku/Flash only
- **Pro**: 1,000 credits/month, +Sonnet ($12/month)
- **Max**: 2,400 credits/month, +Opus ($35/month)

### Credit Pools

Credits are tracked in 4 separate pools:
1. **Monthly** - Subscription allocation
2. **Rollover** - Unused from previous month (max 2x monthly)
3. **Top-up** - Purchased credits
4. **Bonus** - Admin grants

Deduction priority: bonus → top_up → rollover → monthly

### Stripe Integration

```python
from web.core.stripe_client import get_stripe_client

stripe_client = get_stripe_client()
checkout = stripe_client.create_subscription_checkout(
    customer_id="cus_...",
    price_id="price_...",
    success_url="...",
    cancel_url="..."
)
```

**Webhook handling:**
- `checkout.session.completed` - Grant credits on purchase
- `invoice.payment_succeeded` - Monthly billing
- `customer.subscription.deleted` - Cancellation

## Error Handling

```python
try:
    result = await service.operation()
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

## Testing

See [../tests/CLAUDE.md](../tests/CLAUDE.md) for testing patterns.

## Development

```bash
# Run development server
uvicorn web.api.main:app --reload --port 8000

# Access API docs
open http://localhost:8000/docs

# Run in production
uvicorn web.api.main:app --host 0.0.0.0 --port 8000
```
