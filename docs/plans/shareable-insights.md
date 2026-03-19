# Plan: Shareable Insights

## Context

Users want to share a session's insights (and optionally the conversation transcript) via a public link. The paper PDF is never shared (copyright). No share infrastructure currently exists in the codebase — all routes require `require_active` auth. This is greenfield.

---

## 1. DB Migration

**File**: `web/db/migrations/005_session_shares.sql`

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS session_shares (
    token                TEXT PRIMARY KEY,   -- secrets.token_urlsafe(24), ~32 chars
    session_id           TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    include_conversation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    revoked_at           TIMESTAMPTZ         -- NULL = active
);

CREATE INDEX IF NOT EXISTS idx_session_shares_session ON session_shares(session_id);
CREATE INDEX IF NOT EXISTS idx_session_shares_user    ON session_shares(user_id);
CREATE INDEX IF NOT EXISTS idx_session_shares_active  ON session_shares(token)
    WHERE revoked_at IS NULL;

COMMIT;
```

Notes:
- `ON DELETE CASCADE` on both FKs — deleting a session or user auto-removes shares
- `revoked_at` soft-delete pattern — consistent with `deleted_at` elsewhere in schema
- One share token per call; multiple tokens per session allowed (e.g. one with conversation, one without)

---

## 2. Backend

### 2a. Optional-auth dependency

**File**: `web/api/routes/auth.py` — add alongside `require_active`:

```python
async def optional_auth(request: Request) -> Optional[dict]:
    """Returns user dict if authenticated, None otherwise. Does not raise."""
    return await get_current_user_from_request(request)
```

### 2b. New route file

**File**: `web/api/routes/shares.py` (new)

**Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/shares/{session_id}` | `require_active` | Create share |
| `GET` | `/api/shares/view/{token}` | `optional_auth` | Public view |
| `DELETE` | `/api/shares/{token}` | `require_active` | Revoke share |
| `GET` | `/api/shares/session/{session_id}` | `require_active` | List owner's shares |

**POST /api/shares/{session_id}** — body: `{"include_conversation": bool}`
- Verify session ownership via `SELECT id FROM sessions WHERE id=$1 AND user_id=$2`
- Generate token: `token = secrets.token_urlsafe(24)`
- Insert into `session_shares`
- Return `{token, share_url, include_conversation, created_at}`
- `share_url = f"{settings.base_url}/share/{token}"`

**GET /api/shares/view/{token}** — unauthenticated
- Query: JOIN `session_shares`, `sessions`, `metadata`, `insights`; check `revoked_at IS NULL` and `session.deleted_at IS NULL`
- If `include_conversation = TRUE`: also query `conversations WHERE exchange_id > 0 AND deleted_at IS NULL ORDER BY exchange_id, id`
- Return (never include `pdf_path`, `user_id`, `zotero_key`, `file_size_bytes`):
  ```json
  {
    "token": "...",
    "paper_title": "...",
    "paper_authors": "...",
    "paper_journal": "...",
    "publication_date": "...",
    "initial_analysis": "...",
    "insights": { ... } | null,
    "conversation": [ {exchange_id, role, content, timestamp} ] | null,
    "include_conversation": bool,
    "created_at": "..."
  }
  ```
- `initial_analysis` comes from `conversations WHERE session_id=$1 AND exchange_id=0 AND role='assistant'`

**DELETE /api/shares/{token}**
- `UPDATE session_shares SET revoked_at = NOW() WHERE token=$1 AND user_id=$2 AND revoked_at IS NULL RETURNING token`
- 404 if nothing updated

### 2c. Register router

**File**: `web/api/main.py`

```python
from .routes import shares
app.include_router(shares.router)
```

---

## 3. Frontend

### 3a. Share button

Add to `frontend/src/components/left-panel/concepts-tab.ts` near the existing export controls (LinkedIn, Notion buttons). Show only when insights exist.

### 3b. Share modal component

**File**: `frontend/src/components/shared/share-modal.ts` (new)

State: `includeConversation`, `shareUrl`, `token`, `loading`, `copied`

UI elements:
- Checkbox: "Include conversation"
- Button: "Generate link" → calls `POST /api/shares/{sessionId}`
- Read-only text input with copy-to-clipboard button (show after generation)
- Button: "Revoke link" (show after generation)
- Note: "The PDF itself is not shared."

### 3c. Public share page

**File**: `frontend/src/pages/share-page.ts` (new)

- Reads token from URL: `window.location.pathname.match(/^\/share\/(.+)$/)`
- Calls `GET /api/shares/view/{token}` — no auth required
- Renders: paper metadata, initial analysis (markdown), insights sections, conversation (if present)
- Includes CTA banner: "Analyze your own papers at scholia.fyi"
- No left panel, no PDF viewer — share-only layout

### 3d. Router

**File**: `frontend/src/router.ts`

Add before the SPA catch-all:
```typescript
import './pages/share-page';

// In renderRoute():
const shareMatch = path.match(/^\/share\/(.+)$/);
if (shareMatch) return html`<share-page .token=${shareMatch[1]}></share-page>`;
```

### 3e. API client additions

**File**: `frontend/src/services/api.ts`

```typescript
async createShare(sessionId: string, includeConversation: boolean): Promise<ShareCreateResponse>
async revokeShare(token: string): Promise<void>
async getShareView(token: string): Promise<PublicShareResponse>
```

---

## Critical Files

| File | Change |
|------|--------|
| `web/db/migrations/005_session_shares.sql` | New migration |
| `web/api/routes/auth.py` | Add `optional_auth` dependency |
| `web/api/routes/shares.py` | New route file |
| `web/api/main.py` | Register router |
| `frontend/src/components/left-panel/concepts-tab.ts` | Add share button |
| `frontend/src/components/shared/share-modal.ts` | New component |
| `frontend/src/pages/share-page.ts` | New public page |
| `frontend/src/router.ts` | Add `/share/:token` route |
| `frontend/src/services/api.ts` | Add share API methods |

## Verification

1. Create a session, extract insights, click Share → modal opens
2. Generate link without conversation → open in incognito → insights visible, no conversation
3. Generate link with conversation → open in incognito → insights + conversation visible
4. Revoke link → incognito tab returns 404
5. Delete session → share link returns 404
