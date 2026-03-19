# Scholia Web Backend

AI-powered academic paper analysis and conversation system built with FastAPI.

## Features

- **PDF Upload & Analysis**: Upload papers, get instant AI-powered critical appraisal
- **Conversational Q&A**: Ask questions about papers with full context retention
- **Session Management**: Persistent sessions with conversation history
- **Zotero Integration**:
  - Search library, retrieve papers, save insights as notes
  - Auto-redownload PDFs when missing or stale
  - Upload supplemental PDFs to Zotero library
  - Smart supplement detection (excludes main PDF)
  - Manual refresh to get latest highlights
- **Insight Extraction**: Automatic thematic organization of paper analysis
- **REST API**: Complete OpenAPI-documented REST endpoints

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key
- (Optional) Zotero API credentials for library integration

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements-web.txt
   ```

2. **Set environment variables:**
   ```bash
   # Required
   export ANTHROPIC_API_KEY="your-api-key"

   # Optional (for Zotero integration)
   export ZOTERO_API_KEY="your-zotero-key"
   export ZOTERO_LIBRARY_ID="your-library-id"

   # Optional (defaults to ./paper_companion.db)
   export DATABASE_PATH="./data/paper_companion.db"
   ```

   Or create a `.env` file:
   ```env
   ANTHROPIC_API_KEY=your-api-key
   ZOTERO_API_KEY=your-zotero-key
   ZOTERO_LIBRARY_ID=12345
   DATABASE_PATH=./data/paper_companion.db
   ```

3. **Run the server:**
   ```bash
   uvicorn web.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## Usage Examples

### Upload and Analyze a Paper

```bash
curl -X POST http://localhost:8000/sessions/new \
  -F "file=@paper.pdf" \
  | jq
```

Response:
```json
{
  "session_id": "abc123def456",
  "filename": "paper.pdf",
  "initial_analysis": "This paper introduces...",
  "created_at": "2025-01-15T10:00:00",
  "page_count": 12
}
```

### Ask Questions

```bash
curl -X POST http://localhost:8000/sessions/abc123def456/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main contribution of this paper?",
    "use_sonnet": true
  }' | jq
```

Response:
```json
{
  "exchange_id": 1,
  "response": "The main contribution is...",
  "model_used": "claude-sonnet-4-6",
  "usage": {
    "input_tokens": 2000,
    "output_tokens": 150
  }
}
```

### Flag Important Exchanges

```bash
curl -X POST http://localhost:8000/sessions/abc123def456/exchanges/1/flag \
  -H "Content-Type: application/json" \
  -d '{"note": "Key architectural insight"}' | jq
```

### Add Highlights

```bash
curl -X POST http://localhost:8000/sessions/abc123def456/highlights \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Novel multi-head attention mechanism",
    "page_number": 5,
    "exchange_id": 1
  }' | jq
```

### Search Zotero Library

```bash
curl "http://localhost:8000/zotero/search?query=attention+mechanisms&limit=10" | jq
```

### Save Insights to Zotero

```bash
curl -X POST http://localhost:8000/zotero/save-insights \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123def456",
    "parent_item_key": "ZOTERO_KEY",
    "tags": ["claude-analyzed", "critical-appraisal"]
  }' | jq
```

## API Endpoints

### Sessions

- `POST /sessions/new` - Create session from PDF or Zotero
- `GET /sessions` - List all sessions (paginated)
- `GET /sessions/{id}` - Get session with conversation history
- `DELETE /sessions/{id}` - Delete session
- `GET /sessions/{id}/export` - Export session as markdown

### Queries

- `POST /sessions/{id}/query` - Ask question about paper
- `POST /sessions/{id}/exchanges/{eid}/flag` - Flag exchange
- `DELETE /sessions/{id}/exchanges/{eid}/flag` - Unflag exchange
- `GET /sessions/{id}/highlights` - List all highlights
- `POST /sessions/{id}/highlights` - Add highlight
- `DELETE /sessions/{id}/highlights/{hid}` - Delete highlight

### Zotero

- `GET /zotero/search` - Search Zotero library
- `GET /zotero/recent` - List recent papers
- `GET /zotero/paper/{key}` - Get paper details
- `POST /zotero/save-insights` - Save insights as note
- `GET /zotero/related` - Find related papers by tags

## Architecture

```
web/
├── api/
│   ├── main.py              # FastAPI app with middleware
│   ├── routes/              # REST endpoints
│   │   ├── sessions.py      # Session CRUD
│   │   ├── queries.py       # Q&A, flags, highlights
│   │   └── zotero.py        # Zotero integration
│   └── models/              # Pydantic models
│       ├── session.py
│       ├── query.py
│       └── zotero.py
├── core/
│   ├── config.py            # Settings management
│   ├── database.py          # Async SQLite
│   ├── claude.py            # Claude API wrapper
│   └── pdf_processor.py    # PDF extraction
└── services/
    ├── session_manager.py   # Session business logic
    ├── query_service.py     # Query handling
    ├── zotero_service.py    # Zotero operations
    └── insight_extractor.py # Insight extraction
```

## Development

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_sessions_routes.py

# With coverage
pytest --cov=web --cov-report=html

# Verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black web/ tests/

# Lint
ruff check web/ tests/

# Type checking
mypy web/
```

### Database

The application uses SQLite with async operations via aiosqlite.

**Schema:**
- `sessions` - Paper analysis sessions
- `exchanges` - Conversation messages
- `flags` - Flagged exchanges
- `highlights` - Text highlights

**Migrations:** Schema is automatically initialized on startup.

**Inspect database:**
```bash
sqlite3 paper_companion.db
.tables
.schema sessions
SELECT * FROM sessions LIMIT 5;
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key for Claude |
| `ZOTERO_API_KEY` | No | - | Zotero API key (for library integration) |
| `ZOTERO_LIBRARY_ID` | No | - | Zotero library ID |
| `ZOTERO_LIBRARY_TYPE` | No | `user` | Library type (`user` or `group`) |
| `DATABASE_PATH` | No | `./paper_companion.db` | SQLite database path (use `:memory:` for in-memory) |

### CORS

CORS is configured to allow all origins by default. For production:

Edit `web/api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],       # Specific methods
    allow_headers=["*"],
)
```

## Deployment

### Production Server

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn web.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY web/ web/
COPY core/ core/

ENV ANTHROPIC_API_KEY=""
ENV DATABASE_PATH="/data/paper_companion.db"

VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t paper-companion .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY="your-key" \
  -v $(pwd)/data:/data \
  paper-companion
```

## Monitoring

### Logs

Application logs include:
- Request/response logging with timing
- Error tracking with stack traces
- Database operation logs

Configure log level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)  # More verbose
logging.basicConfig(level=logging.WARNING)  # Less verbose
```

### Health Checks

```bash
# Simple health check
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/
```

## Troubleshooting

### Common Issues

**Database locked:**
- SQLite doesn't handle high concurrency well
- Solution: Use connection pooling or switch to PostgreSQL

**PDF extraction fails:**
- Ensure PDF is valid and not encrypted
- Check file permissions
- Try with a different PDF

**Zotero connection fails:**
- Verify API key and library ID
- Check network connectivity
- Ensure library is accessible

**Claude API errors:**
- Check API key is valid
- Verify API quota
- Check for rate limiting

### Debug Mode

```bash
# Run with debug logging
PYTHONPATH=. uvicorn web.api.main:app --log-level debug
```

## License

See LICENSE file in repository root.

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/wiki
