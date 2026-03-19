# Scholia

AI-powered research paper companion. Upload PDFs, ask questions, extract insights.

**Local-first**: Bring your own API key. No accounts, no billing, no data sent anywhere except the AI providers you configure.

## Quick Start

### With Docker (recommended)

1. Clone this repo
2. Copy `.env.example` to `.env` and add your API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Start the app:
   ```bash
   docker-compose up
   ```
4. Open http://localhost:8000

### Manual Setup

**Requirements:** Python 3.11+, Node 20+, PostgreSQL 16+

1. Start PostgreSQL and create a database:
   ```bash
   createdb scholia
   ```

2. Install backend dependencies:
   ```bash
   pip install -r requirements-web.txt
   ```

3. Build the frontend:
   ```bash
   cd frontend && npm install && npm run build
   ```

4. Create `.env` from `.env.example` and fill in your keys.

5. Start the server:
   ```bash
   uvicorn web.api.main:app --reload --port 8000
   ```

6. Open http://localhost:8000

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
