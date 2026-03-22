# Scholia

AI-powered research paper companion. Upload PDFs, ask questions, extract insights.

**Local-first**: Bring your own API key. No accounts, no billing, no data sent anywhere except the AI providers you configure.

## Quick Start

**Requirements:** Python 3.11+, Node 20+, PostgreSQL 16+

1. Clone this repo and start PostgreSQL:
   ```bash
   brew services start postgresql@16
   createdb scholia
   psql postgres -c "CREATE USER scholia WITH PASSWORD 'scholia';"
   psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE scholia TO scholia;"
   psql postgres -c "ALTER DATABASE scholia OWNER TO scholia;"
   ```

2. Install backend dependencies:
   ```bash
   pip install -r requirements-web.txt
   ```

3. Build the frontend:
   ```bash
   cd frontend && npm install && npm run build && cd ..
   ```

4. Copy `.env.example` to `.env` and add your API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

5. Start the server:
   ```bash
   uvicorn web.api.main:app --reload --port 8000
   ```

6. Open http://localhost:8000

### With Docker

If you prefer Docker:
```bash
cp .env.example .env  # add your ANTHROPIC_API_KEY
docker compose up
```

## Features

- Upload PDFs and ask questions about them
- Zotero library integration
- Export insights to Notion
- Conversation history
- Text highlights and flags

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `GOOGLE_API_KEY` | No | Google Gemini API key (for gemini-flash/pro) |
| `DATABASE_URL` | No | PostgreSQL URL (default: localhost) |
| `NOTION_CLIENT_ID` | No | For Notion export integration |
| `NOTION_CLIENT_SECRET` | No | For Notion export integration |

## License

MIT
