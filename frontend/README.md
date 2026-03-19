# Scholia Frontend

Lit + TypeScript frontend for Scholia, built with Vite.

## Development

**Prerequisites:** Node.js 20+, backend running on `http://localhost:8000`

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # production build → dist/
```

The Vite dev server proxies `/sessions/*`, `/api/*`, etc. to the backend automatically.

## Structure

```
src/
├── components/
│   ├── app-root.ts               # Application root
│   ├── left-panel/
│   │   ├── left-panel.ts         # Sidebar shell
│   │   ├── ask-tab.ts            # Chat interface
│   │   ├── concepts-tab.ts       # Extracted insights
│   │   └── outline-tab.ts        # PDF outline/TOC
│   ├── pdf-viewer/
│   │   └── pdf-viewer.ts         # Multi-page PDF renderer (pdf.js)
│   ├── session-picker/
│   │   └── session-list.ts       # Session list and picker
│   ├── zotero-picker/
│   │   └── zotero-picker.ts      # Zotero library browser
│   └── shared/
│       ├── conversation-item.ts  # Q&A message display
│       ├── query-input.ts        # Auto-resizing input
│       ├── feedback-modal.ts     # Thumbs up/down feedback
│       ├── loading-spinner.ts
│       └── error-message.ts
├── pages/
│   ├── app-shell.ts              # Main app (session list + paper view)
│   ├── settings-page.ts          # Zotero + Notion configuration
│   ├── welcome-page.ts           # Landing / about page
│   ├── manifesto-page.ts
│   └── support-page.ts
├── services/
│   ├── api.ts                    # Backend API client
│   ├── auth.ts                   # Local auth stub (always authenticated)
│   └── session-storage.ts        # Local session persistence
├── types/                        # TypeScript type definitions
└── styles/
    ├── global.css
    └── theme.ts                  # Design tokens
```

## Key Patterns

**Components** use LitElement with `@customElement`, `@property`, `@state`:

```typescript
@customElement('my-component')
export class MyComponent extends LitElement {
  @property({ type: String }) title = '';
  @state() private loading = false;
}
```

**API calls** go through `services/api.ts`:

```typescript
import { api } from '../services/api';
const session = await api.post('/sessions/new', formData);
```

**Auth** is always satisfied — `authService.getState()` returns a hardcoded local user. No login checks needed.

## Tech Stack

- **Lit 3.1** — web components
- **TypeScript 5.3** — strict mode
- **Vite 5** — build tool and dev server
- **pdf.js 3.11** — PDF rendering
