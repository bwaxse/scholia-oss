# Frontend Context

> See also: [Root CLAUDE.md](../CLAUDE.md) for overall architecture and backend details

## Stack

- **Framework**: Lit 3.1 (web components)
- **Language**: TypeScript 5.3 (strict mode)
- **Build Tool**: Vite 5.0
- **Routing**: @lit-labs/router
- **PDF Rendering**: pdf.js 3.11

## Architecture

### Directory Structure
```
frontend/
├── src/
│   ├── components/     # Reusable web components
│   │   ├── billing/    # Subscription and credit components
│   │   └── shared/     # Shared UI components
│   ├── pages/          # Page-level components (routed)
│   ├── services/       # API client and utilities
│   ├── styles/         # Global CSS and theme
│   └── types/          # TypeScript type definitions
└── dist/               # Built output (served by backend)
```

### Component Patterns

**LitElement Components:**
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('my-component')
export class MyComponent extends LitElement {
  @property({ type: String }) title = '';
  @state() private count = 0;

  static styles = css`
    /* Scoped styles using design system tokens */
    :host {
      --accent-color: var(--accent, #c45d3a);
    }
  `;

  render() {
    return html`<div>${this.title}: ${this.count}</div>`;
  }
}
```

**Key Patterns:**
- Use `@customElement` decorator for component registration
- Use `@property` for public props, `@state` for internal state
- Scope styles with `static styles = css\`...\``
- Always use CSS custom properties from design system

### API Client

Located in `services/api.ts`:
```typescript
import { api } from '../services/api';

// GET request
const data = await api.get('/api/subscriptions/me');

// POST request
const result = await api.post('/api/credits/checkout', { package_id: 'medium' });
```

**Error Handling:**
```typescript
try {
  const result = await api.post('/api/endpoint', data);
} catch (error: any) {
  if (error instanceof ApiError) {
    console.error(error.status, error.message);
  }
}
```

### Routing

Client-side routing using `@lit-labs/router`:
```typescript
import { router } from './router';

// Navigate programmatically
router.navigate('/session/abc123');

// Route definitions in router.ts
```

Routes:
- `/` - Home (session list)
- `/session/:id` - Session detail
- `/settings` - User settings
- `/login` - OAuth login page

---

# Design System

> Based on the "Warm Terracotta" design language — earthy, grounded, scholarly.

## Brand Essence

Scholia is a tool for **critical reading and research appraisal**. The design should feel:
- **Warm and approachable** — not cold or clinical
- **Scholarly but modern** — not stuffy or outdated
- **Grounded and trustworthy** — earthy tones convey reliability
- **Calm and focused** — supports deep reading, not distraction

---

## Color Palette

### Core Colors

```css
:root {
  /* Backgrounds */
  --bg: #fdfaf8;              /* Main page background - warm off-white */
  --bg-card: #ffffff;         /* Card/surface background */
  --bg-warm: #f9f3ef;         /* Warm tinted sections, footer CTAs */

  /* Text */
  --text: #3d2f2a;            /* Primary text - warm dark brown */
  --text-secondary: #6b574f;  /* Secondary text, descriptions */
  --text-muted: #a08a80;      /* Tertiary text, labels, placeholders */

  /* Borders */
  --border: #e8dfd9;          /* Subtle warm gray borders */

  /* Accent - Terracotta */
  --accent: #c45d3a;          /* Primary accent - terracotta */
  --accent-light: #fce9e2;    /* Light accent for backgrounds, badges */
  --accent-warm: #a64b2d;     /* Darker accent for text on light backgrounds */
}
```

### Usage Guidelines

| Element | Color | Notes |
|---------|-------|-------|
| Page background | `--bg` | The warm off-white base |
| Cards, panels | `--bg-card` | Pure white with subtle borders |
| Section alternates | `--bg-warm` | Use for visual rhythm between sections |
| Body text | `--text` | The warm dark brown |
| Supporting text | `--text-secondary` | Descriptions, secondary info |
| Labels, hints | `--text-muted` | Very subtle, tertiary content |
| Buttons (primary) | `--text` background | Dark brown buttons with white text |
| Emphasis text | `--accent-warm` | Use sparingly for key emphasis |
| Badges, highlights | `--accent-light` bg + `--accent-warm` text | |

### Dark Text Colors (not pure black)

Never use pure `#000000`. The design uses warm browns:
- Primary: `#3d2f2a`
- Hover state for buttons: `#2d211c`

---

## Typography

### Font Stack

```css
:root {
  --serif: Georgia, 'Times New Roman', serif;
  --sans: 'Lora', Georgia, serif;
}
```

**Load from Google Fonts:**
```html
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
```

### Type Hierarchy

| Element | Font | Size | Weight | Notes |
|---------|------|------|--------|-------|
| H1 (hero) | Georgia | 3rem (48px) | 700 | Line-height 1.15, letter-spacing -0.02em |
| H2 (section) | Georgia | 1.875rem (30px) | 700 | |
| H3 (card title) | Georgia | 1.125rem (18px) | 600 | |
| Body | Lora | 1rem (16px) | 400 | Line-height 1.6 |
| Subtitle | Lora | 1.0625rem (17px) | 400 | Line-height 1.7, `--text-secondary` |
| Small/labels | Lora | 0.875rem (14px) | 500-600 | |
| Section labels | Lora | 0.6875rem (11px) | 600 | Uppercase, letter-spacing 0.08em |
| Buttons | Lora | 0.8125rem (13px) | 600 | |

### Special Text Treatments

**Italicized emphasis in headings:**
```css
h1 em {
  font-style: italic;
  font-weight: 500;
  color: var(--accent-warm);
}
```

**Section labels (small caps style):**
```css
.section-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}
```

---

## Spacing System

```css
/* Based on 4px grid, with rem equivalents */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.375rem;  /* 6px */
--space-3: 0.5rem;    /* 8px */
--space-4: 0.75rem;   /* 12px */
--space-5: 1rem;      /* 16px */
--space-6: 1.25rem;   /* 20px */
--space-7: 1.5rem;    /* 24px */
--space-8: 1.75rem;   /* 28px */
--space-9: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
```

### Common Spacing Patterns

- **Section padding:** `4rem 2rem` (vertical, horizontal)
- **Container max-width:** `1000px` (content), `800px` (narrow sections)
- **Card padding:** `1.25rem` to `1.5rem`
- **Component gaps:** `0.75rem` to `1.5rem`
- **Header padding:** `0.875rem 2rem`

---

## Components

### Buttons

**Primary Button:**
```css
.btn-primary {
  font-size: 0.8125rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  background: var(--text);      /* Dark brown, not black */
  color: white;
  transition: all 0.15s;
}

.btn-primary:hover {
  background: #2d211c;
}
```

**Secondary Button:**
```css
.btn-secondary {
  font-size: 0.8125rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--bg-warm);
}
```

### Cards

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
```

### Badges

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--accent-warm);
  background: var(--accent-light);
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
}

/* Optional dot indicator */
.badge::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
}
```

### Icons

- Use stroke-based SVG icons (not filled)
- Stroke width: `2`
- Size: `20px` in cards/features, `24px` for larger contexts
- Color: `currentColor` to inherit from parent

**Icon container (in feature cards):**
```css
.icon-container {
  width: 40px;
  height: 40px;
  background: var(--accent-light);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}
```

### Header

```css
header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(253, 250, 248, 0.9);  /* --bg with transparency */
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}

.header-inner {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0.875rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
```

**Logo:**
```css
.logo {
  font-family: var(--serif);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text);
  text-decoration: none;
}
```

**Nav links:**
```css
nav a {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.15s;
}

nav a:hover {
  color: var(--text);
}
```

---

## Layout Patterns

### Hero Section
```css
.hero {
  max-width: 1000px;
  margin: 0 auto;
  padding: 5rem 2rem 4rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem;
  align-items: center;
}
```

### Feature Grid (3 columns)
```css
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

@media (max-width: 900px) {
  .grid-3 {
    grid-template-columns: 1fr;
  }
}
```

### Section with Background Change
```css
.section-alt {
  padding: 4rem 2rem;
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
```

### Narrow Content Section
```css
.section-narrow {
  padding: 4rem 2rem;
  max-width: 800px;
  margin: 0 auto;
}
```

---

## Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 3rem 1.5rem;
  }

  .hero h1 {
    font-size: 2.25rem;
  }

  nav {
    display: none;  /* Use hamburger menu */
  }

  .grid-3 {
    grid-template-columns: 1fr;
  }
}
```

---

## Animation & Transitions

Keep animations subtle and purposeful:

```css
/* Standard transition for interactive elements */
transition: all 0.15s;

/* Or be specific */
transition: color 0.15s;
transition: background 0.15s;
```

Use `ease` or default timing. Avoid bounce or dramatic easings.

---

## Do's and Don'ts

### Do:
- Use the warm terracotta palette consistently
- Pair Georgia (display) with Lora (body)
- Use `--text` (warm brown) for primary buttons instead of pure black
- Add subtle borders (`--border`) to define card edges
- Use `--accent-light` backgrounds for highlight areas
- Keep section padding generous (4rem vertical)

### Don't:
- Use pure black (`#000000`) or pure white (`#ffffff`) for text
- Mix in blues, greens, or other hue families
- Use heavy drop shadows (keep them subtle: `0 1px 3px rgba(0,0,0,0.04)`)
- Overcrowd sections — embrace whitespace
- Use different serif fonts — stick to Lora/Georgia

---

## Build & Development

```bash
# Development server (hot reload)
npm run dev

# Production build
npm run build

# TypeScript check
npm run type-check
```

**Important:**
- Always run `npm run build` before committing to catch TypeScript errors
- Built files go to `dist/` and are served by the backend
- The backend serves `dist/index.html` for all non-API routes (SPA fallback)
