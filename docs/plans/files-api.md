# Plan: Files API

## Context

Currently every Claude API call (initial analysis, query, insight extraction) base64-encodes and re-transmits the full PDF bytes. For a 10 MB PDF, that's ~13 MB of JSON payload per call, and the 5-minute ephemeral cache TTL means users who pause between queries pay full cost again. The Anthropic Files API lets you upload a PDF once, store a `file_id`, and reference it in future calls — eliminating repeated transmission and decoupling caching from TTL. Files persist for 30 days.

---

## 1. DB Migration

**File**: `web/db/migrations/006_claude_file_id.sql`

```sql
BEGIN;

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS claude_file_id TEXT;

COMMIT;
```

No data migration — existing rows default to `NULL`, triggering base64 fallback.

---

## 2. ClaudeClient changes (`web/core/claude.py`)

### New static helper: `_build_document_block()`

Centralises "file_id vs base64" selection. Always includes `cache_control`.

```python
@staticmethod
def _build_document_block(pdf_path: str = "", file_id: str = "") -> dict:
    if file_id:
        return {
            "type": "document",
            "source": {"type": "file", "file_id": file_id},
            "cache_control": {"type": "ephemeral"}
        }
    pdf_data = ClaudeClient._encode_pdf(pdf_path)
    return {
        "type": "document",
        "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_data},
        "cache_control": {"type": "ephemeral"}
    }
```

### New method: `upload_pdf_to_files_api()`

```python
async def upload_pdf_to_files_api(self, pdf_path: str) -> str:
    """Upload PDF to Anthropic Files API. Returns file_id. Raises on failure."""
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    def _do_upload():
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()
        response = self.client.beta.files.upload(
            (pdf_file.name, file_bytes, "application/pdf"),
        )
        return response.id

    loop = asyncio.get_event_loop()
    file_id = await loop.run_in_executor(None, _do_upload)
    logger.info(f"Files API upload complete: file_id={file_id}")
    return file_id
```

### Updated method signatures

Add `file_id: str = ""` parameter to all three methods:

- `initial_analysis(self, pdf_path: str, file_id: str = "", ...)`
- `query(self, ..., file_id: str = "")`
- `extract_structured(self, ..., file_id: str = "")`

In each, replace the hardcoded base64 document block with:
```python
doc_block = self._build_document_block(pdf_path=pdf_path, file_id=file_id)
```

When `file_id` is set, add `betas=["files-api-2025-04-14"]` to `api_kwargs`:
```python
if file_id:
    api_kwargs["betas"] = ["files-api-2025-04-14"]
```

### Expiry handling

Files expire after 30 days. In `query_service.py`, if the Files API returns a 404, catch it, re-upload, and update the DB:

```python
try:
    response_text, usage_stats = await self.claude.query(..., file_id=file_id)
except anthropic.NotFoundError:
    logger.warning(f"file_id {file_id} expired, re-uploading")
    file_id = await self.claude.upload_pdf_to_files_api(pdf_path)
    await db.execute("UPDATE sessions SET claude_file_id=$1 WHERE id=$2", file_id, session_id)
    response_text, usage_stats = await self.claude.query(..., file_id=file_id)
```

---

## 3. Session creation: upload on first use

**File**: `web/services/session_manager.py` — in `create_session_from_pdf()` and `create_session_from_zotero()`:

```python
# Upload PDF to Files API (best-effort — fall back to base64 if it fails)
file_id = ""
try:
    file_id = await self.claude.upload_pdf_to_files_api(temp_pdf_path)
except Exception as e:
    logger.warning(f"Files API upload failed, using base64 fallback: {e}")

initial_analysis, usage_stats = await self.claude.initial_analysis(
    pdf_path=temp_pdf_path,
    file_id=file_id
)
```

Include `claude_file_id` in the `INSERT INTO sessions` query:
```sql
INSERT INTO sessions (id, user_id, filename, pdf_path, page_count,
                      file_size_bytes, claude_file_id, ...)
VALUES ($1, $2, $3, $4, $5, $6, $7, ...)
```

---

## 4. Query service: read and use file_id

**File**: `web/services/query_service.py`

Update the session SELECT to include `claude_file_id`:
```sql
SELECT pdf_path, zotero_key, user_id, claude_file_id FROM sessions WHERE id=$1
```

Pass to `claude.query()`:
```python
file_id = row['claude_file_id'] or ""
response_text, usage_stats = await self.claude.query(
    ..., file_id=file_id
)
```

---

## 5. Insight extractor: read and use file_id

**File**: `web/services/insight_extractor.py` (wherever it fetches `pdf_path`)

Same pattern: add `claude_file_id` to the session SELECT, pass `file_id` to `extract_structured()`.

---

## Compatibility with prompt caching (prompt-caching-fix plan)

Both features work together. `_build_document_block()` always includes `cache_control`, so file_id-based calls still benefit from ephemeral caching. With both active:

- System prompt: cached (prompt-caching-fix plan)
- Document: referenced by file_id, no bytes transmitted, also cache_control-tagged
- Net: second query from same user ≈ near-zero PDF cost

---

## Critical Files

| File | Change |
|------|--------|
| `web/db/migrations/006_claude_file_id.sql` | New migration |
| `web/core/claude.py` | `_build_document_block()` helper, `upload_pdf_to_files_api()`, updated signatures for all 3 methods |
| `web/services/session_manager.py` | Upload on session create, pass file_id to initial_analysis, include in INSERT |
| `web/services/query_service.py` | Read claude_file_id from session, pass to query(), handle expiry |
| `web/services/insight_extractor.py` | Read claude_file_id, pass to extract_structured() |

## Verification

1. Create a new session → check logs for `Files API upload complete: file_id=...`
2. Confirm `claude_file_id` is set in DB for the new session
3. Submit a query → logs should show no base64 encoding, `betas=files-api-2025-04-14`
4. Simulate expiry: set `claude_file_id` to a bogus value → query should re-upload and update DB
5. Check token usage: `input_tokens` should drop significantly vs base64 for the same PDF
