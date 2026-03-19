# Paper Companion Frontend

Modern web frontend for Paper Companion built with Lit + TypeScript + PDF.js.

## Features

**✅ Full-Featured Paper Analysis App!**

### Core Features
- **Multi-page PDF Viewer** - Render PDFs with virtualized scrolling for performance
- **Text Selection** - Select and highlight text from PDF pages
- **AI-Powered Q&A** - Ask questions about papers with Claude as a senior researcher mentor
- **Conversation UI** - Clean chat interface with history
- **Flag Important Exchanges** - Mark key insights
- **Zoom Controls** - Zoom in/out and reset view
- **Page Navigation** - Navigate between pages with prev/next buttons

### Zotero Integration
- **Load from Zotero** - Browse and load papers from your library
- **Smart Supplement Detection** - Auto-check for supplemental PDFs
- **Supplement Count Display** - Shows "Add Supplement (2)" or "No Supplemental PDFs Available"
- **Upload to Zotero** - Add supplemental PDFs directly to your library
- **Auto-refresh** - Get latest version with your highlights from Zotero

### Session Management
- **Persistent Sessions** - Resume conversations from previous sessions
- **Session List** - Browse and restore past paper analyses
- **Loading & Error States** - Polished UX throughout

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (required)

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Opens at `http://localhost:5173`

**Important:** Make sure the backend is running first:
```bash
cd web
uvicorn api.main:app --reload
```

### Build

```bash
npm run build
```

Output in `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── app-root.ts                    # Main app orchestrator
│   │   ├── pdf-viewer/
│   │   │   └── pdf-viewer.ts              # Multi-page PDF viewer
│   │   ├── left-panel/
│   │   │   └── ask-tab.ts                 # Q&A conversation UI
│   │   └── shared/
│   │       ├── conversation-item.ts       # Message display
│   │       ├── query-input.ts             # Question input
│   │       ├── loading-spinner.ts         # Loading states
│   │       └── error-message.ts           # Error handling
│   ├── services/
│   │   └── api.ts                         # Backend API client
│   ├── types/
│   │   ├── session.ts                     # Session & conversation types
│   │   ├── query.ts                       # Query request/response types
│   │   └── pdf.ts                         # PDF-related types
│   └── styles/
│       ├── global.css                     # Global styles
│       └── theme.ts                       # Design tokens
├── index.html                             # Entry point
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Components

### `<app-root>`

Main application shell that orchestrates the entire app.

**Features:**
- File upload handling
- Session management
- State coordination between PDF viewer and Ask tab
- Loading and error screens

### `<pdf-viewer>`

Multi-page PDF viewer with text layer for selection.

**Properties:**
- `pdfUrl` (string) - URL or blob URL of PDF to display
- `scale` (number) - Zoom level (default: 1.5)

**Events:**
- `text-selected` - Emitted when user selects text
  - `detail.text` - Selected text
  - `detail.page` - Page number

**Methods:**
- `zoomIn()` - Increase zoom
- `zoomOut()` - Decrease zoom
- `resetZoom()` - Reset to default zoom
- `goToPage(page: number)` - Navigate to specific page
- `nextPage()` - Go to next page
- `prevPage()` - Go to previous page

### `<ask-tab>`

Complete conversation interface for asking questions.

**Properties:**
- `sessionId` (string) - Current session ID
- `conversation` (ConversationMessage[]) - Message history
- `flags` (number[]) - Flagged exchange IDs
- `selectedText` (string) - Currently selected text
- `selectedPage` (number) - Page of selection

**Events:**
- `clear-selection` - Clear text selection

**Features:**
- Displays initial analysis
- Shows conversation history
- Query input with selected text context
- Flag/unflag responses
- Auto-scroll to latest message
- Loading states during queries

### `<conversation-item>`

Individual message display (user query or assistant response).

**Properties:**
- `message` (ConversationMessage) - Message data
- `flagged` (boolean) - Whether exchange is flagged

**Events:**
- `flag-toggle` - Toggle flag on this exchange

**Features:**
- Shows highlighted text context
- Model badge (Haiku/Sonnet)
- Timestamp
- Copy response button
- Flag button

### `<query-input>`

Text input for asking questions with keyboard shortcuts.

**Properties:**
- `selectedText` (string) - Highlighted text from PDF
- `selectedPage` (number) - Page of selection
- `disabled` (boolean) - Disable input
- `loading` (boolean) - Show loading state

**Events:**
- `submit-query` - User submitted a question
  - `detail.query` - Question text
  - `detail.highlighted_text` - Selected text (if any)
  - `detail.page` - Page number (if any)
- `clear-selection` - Clear text selection

**Features:**
- Auto-resizing textarea
- Selected text preview
- Cmd+Enter to submit
- Character count
- Disabled during loading

### `<loading-spinner>` & `<error-message>`

Reusable UI state components.

## API Service

The `api.ts` service provides methods for all backend endpoints:

```typescript
import { api } from './services/api';

// Create session from PDF
const session = await api.createSession(file);

// Query the paper
const response = await api.query(sessionId, {
  query: "What is the main contribution?",
  highlighted_text: "transformer architecture",
  page: 3
});

// Toggle flag
await api.toggleFlag(sessionId, exchangeId);

// List sessions
const sessions = await api.listSessions();
```

## User Flow

1. **Upload PDF** → Backend creates session + initial analysis
2. **View PDF** → Multi-page rendering with text selection
3. **Select text** (optional) → Shows in query input
4. **Ask question** → Sent to backend with context
5. **View response** → Displayed in conversation
6. **Flag important** → Mark key insights
7. **Continue conversation** → Full context maintained

## Architecture

Built with:
- **Lit 3.1** - Fast, lightweight web components
- **PDF.js 3.11** - Mozilla's PDF rendering library
- **TypeScript 5.3** - Type safety
- **Vite 5** - Fast builds and dev server

## Performance Optimizations

**PDF Viewer:**
- Virtualized rendering with IntersectionObserver
- Only visible pages rendered (±2 page buffer)
- Lazy loading as you scroll
- Efficient text layer rendering

**General:**
- Component-level state management
- Event-based communication
- No unnecessary re-renders
- Optimized bundle size

## Development Tips

### Adding New Components

1. Create component in appropriate directory
2. Use Lit decorators: `@customElement`, `@property`, `@state`
3. Import and use in parent components
4. Follow existing patterns for events and styling

### TypeScript Configuration

The project uses strict TypeScript with:
- `experimentalDecorators: true` - For Lit decorators
- `useDefineForClassFields: false` - Required for Lit compatibility
- Strict mode enabled

### Vite Proxy Configuration

The Vite dev server proxies API calls to the backend:
- `/sessions/*` → `http://localhost:8000/sessions/*`
- `/zotero/*` → `http://localhost:8000/zotero/*`

This allows the frontend to make relative API calls that are automatically proxied to the backend during development.

## Testing

You can test the complete flow:

1. Start backend: `uvicorn web.api.main:app --reload`
2. Start frontend: `npm run dev`
3. Upload a PDF
4. Wait for initial analysis
5. Select text in PDF
6. Ask a question
7. View response
8. Flag important exchanges

## Next Steps

This MVP has the core flow working. Next features to add:

1. **Outline Tab** - Navigate by document structure
2. **Concepts Tab** - Key terms extraction
3. **Session List** - "Pick up where you left off"
4. **Zotero Integration UI** - Load papers from library
5. **Highlights** - Visual markers on PDF pages
6. **Export** - Save conversations as markdown

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 15+
- Edge 90+

(Requires ES2020 and Web Components support)

## Troubleshooting

**"Failed to create session" error:**
- Make sure backend is running on port 8000
- Check that ANTHROPIC_API_KEY is set in backend

**PDF not rendering:**
- Check browser console for errors
- Ensure PDF is valid and not encrypted
- Try a different PDF

**Text selection not working:**
- Make sure PDF has rendered completely
- Check that text layer is visible (inspect element)

## License

See LICENSE file in repository root.
