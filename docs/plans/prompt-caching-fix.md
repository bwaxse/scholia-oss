# Plan: Prompt Caching Fix

## Context

Prompt caching is already structurally in place (`cache_control: {"type": "ephemeral"}` is set on document blocks in all three Claude methods). However, analysis shows `cache_read_input_tokens` is always 0. The root cause: **the system prompt is passed as a plain string and is not being cached**. Since the system prompt is the first token prefix the model processes, and it's not marked cacheable, the cache key for the document block can never fully benefit from caching. Caching the system prompt fixes this and reduces input token costs for repeated queries within the 5-minute TTL window.

---

## Change: `web/core/claude.py`

For all three methods — `initial_analysis()`, `query()`, `extract_structured()` — change `system=SOME_SYSTEM_PROMPT` (plain string) to a cached list block:

```python
# Before (uncached)
system=QUERY_SYSTEM_PROMPT

# After (cached)
system=[{
    "type": "text",
    "text": QUERY_SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"}
}]
```

Apply this same pattern to all three API calls. The Anthropic SDK accepts `system` as either `str` or `List[dict]` — no other changes to the call signature needed.

The document block `cache_control` entries (lines ~234, ~337, ~479) stay in place. With system prompt cached first, document block caching has a consistent prefix and hits more reliably.

---

## Verifying cache hits in logs

The existing `TokenUsage.add_usage()` already reads `cache_creation_input_tokens` and `cache_read_input_tokens`. The existing log lines already print them. After deploying:

- **First call**: `cache_create` is non-zero, `cache_read` is 0
- **Second call within 5 min**: `cache_read` is large (system prompt + PDF tokens), `cache_create` drops

Optionally add a dedicated log line after each method's existing usage log:

```python
if cache_read > 0:
    logger.info(f"Cache HIT — {cache_read} tokens from cache")
else:
    logger.info(f"Cache MISS — {cache_creation} tokens written")
```

---

## Critical Files

| File | Change |
|------|--------|
| `web/core/claude.py` | Convert `system=str` to `system=[{..., cache_control}]` in `initial_analysis()` (~line 245), `query()` (~line 366), `extract_structured()` (~line 500) |

## Verification

1. Deploy and run two queries on the same session within 5 minutes
2. Check server logs for `cache_read` > 0 on second query
3. Confirm `input_tokens` drops significantly on cache-hit calls
