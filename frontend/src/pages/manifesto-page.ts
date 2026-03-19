/**
 * Manifesto page - "Recovering the Deep Read" - Terracotta design system
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { authService, type AuthState } from '../services/auth';

@customElement('manifesto-page')
export class ManifestoPage extends LitElement {
  @state() private authState: AuthState = {
    isAuthenticated: false,
    isLoading: true,
    user: null
  };

  @state() private menuOpen = false;

  connectedCallback() {
    super.connectedCallback();
    authService.subscribe((state) => {
      this.authState = state;
    });
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--bg, #fdfaf8);
      color: var(--text, #3d2f2a);
      font-family: var(--sans, 'Lora', Georgia, serif);
    }

    /* Header - Glassmorphism */
    header {
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(253, 250, 248, 0.9);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border, #e8dfd9);
    }

    .header-inner {
      max-width: 1000px;
      margin: 0 auto;
      padding: 0.875rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.25rem;
      font-weight: 500;
      text-decoration: none;
      color: var(--text, #3d2f2a);
    }

    .logo img {
      height: 20px;
      width: auto;
    }

    nav {
      display: flex;
      align-items: center;
      gap: 1.75rem;
    }

    nav a {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary, #6b574f);
      text-decoration: none;
      transition: color 0.15s;
    }

    nav a:hover {
      color: var(--text, #3d2f2a);
    }

    .btn {
      font-size: 0.8125rem;
      font-weight: 600;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      text-decoration: none;
      transition: all 0.15s;
      border: none;
      cursor: pointer;
    }

    .btn-primary {
      background: var(--text, #3d2f2a);
      color: white;
    }

    .btn-primary:hover {
      background: #2d211c;
    }

    .btn-pending {
      background: var(--accent-light, #fce9e2);
      color: var(--accent-warm, #a64b2d);
    }

    /* Mobile menu */
    .hamburger {
      display: none;
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      color: var(--text, #3d2f2a);
    }

    .hamburger svg {
      width: 24px;
      height: 24px;
    }

    .mobile-menu {
      display: none;
      position: fixed;
      top: 57px;
      left: 0;
      right: 0;
      background: var(--bg-card, #ffffff);
      border-bottom: 1px solid var(--border, #e8dfd9);
      padding: 1rem 2rem;
      flex-direction: column;
      gap: 0.75rem;
      z-index: 99;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .mobile-menu.open {
      display: flex;
    }

    .mobile-menu a,
    .mobile-menu span {
      color: var(--text, #3d2f2a);
      text-decoration: none;
      padding: 0.75rem 0;
      font-size: 1rem;
      border-bottom: 1px solid var(--border, #e8dfd9);
    }

    .mobile-menu a:last-child,
    .mobile-menu span:last-child {
      border-bottom: none;
    }

    .mobile-menu .pending-badge {
      display: inline-block;
      width: fit-content;
      background: var(--accent-light, #fce9e2);
      color: var(--accent-warm, #a64b2d);
      padding: 0.375rem 0.75rem;
      border-radius: 4px;
      font-size: 0.8125rem;
      font-weight: 500;
    }

    /* Article */
    article {
      max-width: 700px;
      margin: 0 auto;
      padding: 5rem 2rem;
    }

    .article-header {
      text-align: center;
      margin-bottom: 3.5rem;
    }

    h1 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 3rem;
      font-weight: 400;
      line-height: 1.15;
      letter-spacing: -0.02em;
      margin: 0 0 1rem 0;
      color: var(--text, #3d2f2a);
    }

    .article-header .subtitle {
      font-size: 1.125rem;
      color: var(--text-secondary, #6b574f);
      font-style: italic;
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
    }

    h2 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.5rem;
      font-weight: 500;
      margin: 3rem 0 1.25rem 0;
      color: var(--text, #3d2f2a);
    }

    p {
      font-size: 1.0625rem;
      line-height: 1.8;
      color: var(--text, #3d2f2a);
      margin: 0 0 1.5rem 0;
    }

    .lead {
      font-size: 1.25rem;
      line-height: 1.7;
      color: var(--text, #3d2f2a);
    }

    /* Principle list */
    .principles {
      margin: 2rem 0;
      padding-left: 0;
      list-style: none;
    }

    .principles li {
      font-size: 1.0625rem;
      line-height: 1.6;
      color: var(--text, #3d2f2a);
      margin-bottom: 0.75rem;
      padding-left: 1.5rem;
      position: relative;
    }

    .principles li::before {
      content: '';
      position: absolute;
      left: 0;
      top: 10px;
      width: 6px;
      height: 6px;
      background: var(--accent, #c45d3a);
      border-radius: 50%;
    }

    .emphasis {
      font-weight: 600;
      color: var(--accent-warm, #a64b2d);
    }

    /* Quote/callout */
    .callout {
      background: var(--bg-warm, #f9f3ef);
      border-left: 3px solid var(--accent, #c45d3a);
      padding: 1.5rem 2rem;
      margin: 2.5rem 0;
      font-size: 1.125rem;
      font-style: italic;
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      color: var(--text, #3d2f2a);
      border-radius: 0 8px 8px 0;
    }

    /* Signature */
    .signature {
      margin-top: 3.5rem;
      padding-top: 2.5rem;
      border-top: 1px solid var(--border, #e8dfd9);
      text-align: center;
    }

    .signature-tagline {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.875rem;
      font-weight: 400;
      margin: 0 0 1.5rem 0;
      color: var(--text, #3d2f2a);
    }

    .author {
      font-size: 1rem;
      color: var(--text-secondary, #6b574f);
      margin: 2rem 0;
      font-style: italic;
    }

    .cta-btn {
      display: inline-block;
      padding: 0.875rem 1.75rem;
      border-radius: 6px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      text-decoration: none;
      background: var(--text, #3d2f2a);
      color: white;
      border: none;
    }

    .cta-btn:hover {
      background: #2d211c;
    }

    .cta-btn.pending {
      background: var(--accent-light, #fce9e2);
      color: var(--accent-warm, #a64b2d);
      cursor: default;
    }

    .cta-btn.pending:hover {
      background: var(--accent-light, #fce9e2);
    }

    /* Footer */
    footer {
      padding: 1.5rem 2rem;
      text-align: center;
      border-top: 1px solid var(--border, #e8dfd9);
    }

    footer p {
      font-size: 0.8125rem;
      color: var(--text-muted, #a08a80);
      margin: 0;
    }

    footer a {
      color: var(--text-secondary, #6b574f);
      text-decoration: none;
    }

    footer a:hover {
      color: var(--accent-warm, #a64b2d);
    }

    footer .tagline {
      display: inline;
    }

    /* Responsive */
    @media (max-width: 900px) {
      nav {
        display: none;
      }

      .hamburger {
        display: block;
      }

      article {
        padding: 3.5rem 1.5rem;
      }

      h1 {
        font-size: 2.25rem;
      }

      h2 {
        font-size: 1.25rem;
      }

      p, .principles li {
        font-size: 1rem;
      }

      .lead {
        font-size: 1.125rem;
      }

      .callout {
        font-size: 1rem;
        padding: 1.25rem 1.5rem;
      }

      .signature-tagline {
        font-size: 1.5rem;
      }
    }

    @media (max-width: 480px) {
      .header-inner {
        padding: 0.75rem 1rem;
      }

      article {
        padding: 2.5rem 1rem;
      }

      h1 {
        font-size: 1.875rem;
      }

      footer .tagline {
        display: block;
        margin-top: 0.5rem;
      }
    }
  `;

  private toggleMenu() {
    this.menuOpen = !this.menuOpen;
  }

  private renderMobileMenu() {
    const { isAuthenticated } = this.authState;

    if (isAuthenticated) {
      return html`
        <div class="mobile-menu ${this.menuOpen ? 'open' : ''}">
          <a href="/" @click=${() => this.menuOpen = false}>Home</a>
          
          <a href="/" @click=${() => this.menuOpen = false}>Open App</a>
        </div>
      `;
    }

    return html`
      <div class="mobile-menu ${this.menuOpen ? 'open' : ''}">
        <a href="/" @click=${() => this.menuOpen = false}>Home</a>
        
        
        
      </div>
    `;
  }

  private renderHeaderCTA() {
    const { isAuthenticated } = this.authState;

    if (isAuthenticated) {
      return html`<a href="/" class="btn btn-primary">Open App</a>`;
    }

    return html`<a href="/" class="btn btn-primary">Open App</a>`;
  }

  private renderSignatureCTA() {
    return html`<a href="/" class="cta-btn">Open App</a>`;
  }

  render() {
    return html`
      <header>
        <div class="header-inner">
          <a href="/" class="logo"><img src="/logo_small.png?v=2" alt="Scholia" />Scholia.fyi</a>
          <nav>
            <a href="/">Home</a>
            ${this.renderHeaderCTA()}
          </nav>
          <button class="hamburger" @click=${this.toggleMenu}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
          </button>
        </div>
      </header>

      ${this.renderMobileMenu()}

      <article>
        <div class="article-header">
          <h1>Recovering the Deep Read</h1>
          <p class="subtitle">A manifesto for critical appraisal</p>
        </div>

        <p class="lead">
          This is an era of unprecedented scientific output. Thousands of papers published daily,
          but our capacity to process them hasn't changed. In the rush to keep up, we've degraded
          the most vital skill of the researcher: critical appraisal.
        </p>

        <p>
          When overwhelmed, we stop reading and start skimming. Abstract, conclusion, move on.
          But the truth of a paper isn't in the abstract—it's in the methods, the limitations,
          the gap between data and claims.
        </p>

        <h2>Scholia: Margins Revived</h2>

        <p>
          Centuries ago, scholars practiced <span class="emphasis">scholia</span>—writing complex,
          critical commentary in the margins of texts. Not summaries. Conversations with the author.
          Living sites of inquiry.
        </p>

        <p>
          Scholia.fyi brings that practice into the present.
        </p>

        <h2>AI as Intellectual Lever</h2>

        <p>
          There are a lot of tools that tell you what's in a PDF, but I don't believe AI should read for you. I believe it should help you read better.
        </p>

        <p>
          Most AI tools are designed to give you "the gist." But the gist is the enemy of critical
          thinking. Scholia.fyi uses Claude and Gemini not to replace your judgment, but to sharpen it:
        </p>

        <ul class="principles">
          <li><span class="emphasis">Scrutinize</span>, don't summarize</li>
          <li><span class="emphasis">Appraise</span>, don't store</li>
          <li><span class="emphasis">Connect</span>, don't capture</li>
        </ul>

        <h2>Rigor, Accelerated</h2>

        <p>
          By leveraging AI reasoning capabilities, Scholia.fyi lets you interrogate a paper's logic
          at the speed of thought. Check for statistical overreach. Identify conflicts of interest.
          We provide the insights in the margins that move you from passive reader to critical appraiser.
        </p>

        <div class="callout">
          The mission is simple: In an age of infinite information, preserve the ability to think for ourselves.
        </div>

        <p class="author">Bennett Waxse<br><em>December 21, 2025</em></p>

        <div class="signature">
          <p class="signature-tagline">Ready to Read Critically?</p>
          ${this.renderSignatureCTA()}
        </div>
      </article>

      <footer>
        <p>
          <a href="/">Home</a> · Built for researchers who think deeply.
        </p>
      </footer>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'manifesto-page': ManifestoPage;
  }
}
