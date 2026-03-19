/**
 * Support page - Personal, direct contact
 * Terracotta design system
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { authService, type AuthState } from '../services/auth';

@customElement('support-page')
export class SupportPage extends LitElement {
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

    .header-logo {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.25rem;
      font-weight: 500;
      text-decoration: none;
      color: var(--text, #3d2f2a);
    }

    .header-logo img {
      height: 20px;
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

    .mobile-menu a {
      color: var(--text, #3d2f2a);
      text-decoration: none;
      padding: 0.75rem 0;
      font-size: 1rem;
      border-bottom: 1px solid var(--border, #e8dfd9);
    }

    .mobile-menu a:last-child {
      border-bottom: none;
    }

    /* Main content */
    .container {
      max-width: 700px;
      margin: 0 auto;
      padding: 5rem 2rem;
    }

    h1 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 3rem;
      font-weight: 400;
      line-height: 1.15;
      letter-spacing: -0.02em;
      margin: 0 0 1.25rem 0;
      color: var(--text, #3d2f2a);
    }

    .subtitle {
      font-size: 1.0625rem;
      color: var(--text-secondary, #6b574f);
      margin: 0 0 3rem 0;
      line-height: 1.7;
    }

    .contact-card {
      background: var(--bg-card, #ffffff);
      border: 1px solid var(--border, #e8dfd9);
      border-radius: 8px;
      padding: 2.5rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      margin-bottom: 2rem;
    }

    .contact-card h2 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0 0 1rem 0;
      color: var(--text, #3d2f2a);
    }

    .contact-card p {
      font-size: 1rem;
      line-height: 1.7;
      color: var(--text-secondary, #6b574f);
      margin: 0 0 1.5rem 0;
    }

    .contact-card p:last-child {
      margin-bottom: 0;
    }

    .email-link {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--accent-warm, #a64b2d);
      background: var(--accent-light, #fce9e2);
      padding: 0.875rem 1.5rem;
      border-radius: 6px;
      text-decoration: none;
      transition: all 0.15s;
      margin-top: 0.5rem;
    }

    .email-link:hover {
      background: #f8ddd2;
      transform: translateY(-1px);
    }

    .email-link svg {
      width: 20px;
      height: 20px;
    }

    .info-box {
      background: var(--bg-warm, #f9f3ef);
      border: 1px solid var(--border, #e8dfd9);
      border-radius: 8px;
      padding: 2rem;
      margin-bottom: 2rem;
    }

    .info-box h3 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.125rem;
      font-weight: 600;
      margin: 0 0 0.75rem 0;
      color: var(--text, #3d2f2a);
    }

    .info-box p {
      font-size: 0.9375rem;
      line-height: 1.7;
      color: var(--text-secondary, #6b574f);
      margin: 0;
    }

    .info-box ul {
      margin: 1rem 0 0 0;
      padding-left: 1.5rem;
      list-style: none;
    }

    .info-box li {
      font-size: 0.9375rem;
      line-height: 1.7;
      color: var(--text-secondary, #6b574f);
      margin-bottom: 0.5rem;
      position: relative;
    }

    .info-box li::before {
      content: "→";
      position: absolute;
      left: -1.5rem;
      color: var(--accent, #c45d3a);
      font-weight: 600;
    }

    .personal-note {
      font-style: italic;
      color: var(--text-secondary, #6b574f);
      border-left: 3px solid var(--accent, #c45d3a);
      padding-left: 1.5rem;
      margin: 2rem 0;
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

    /* Responsive */
    @media (max-width: 900px) {
      nav {
        display: none;
      }

      .hamburger {
        display: block;
      }
    }

    @media (max-width: 480px) {
      .header-inner {
        padding: 0.75rem 1rem;
      }

      .container {
        padding: 3rem 1.5rem;
      }

      h1 {
        font-size: 2.25rem;
      }

      .contact-card {
        padding: 2rem 1.5rem;
      }

      .info-box {
        padding: 1.5rem;
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
          <a href="/manifesto" @click=${() => this.menuOpen = false}>Manifesto</a>
          <a href="/pricing" @click=${() => this.menuOpen = false}>Pricing</a>
          <a href="/" @click=${() => this.menuOpen = false}>Open App</a>
        </div>
      `;
    }

    return html`
      <div class="mobile-menu ${this.menuOpen ? 'open' : ''}">
        <a href="/" @click=${() => this.menuOpen = false}>Home</a>
        <a href="/manifesto" @click=${() => this.menuOpen = false}>Manifesto</a>
        <a href="/pricing" @click=${() => this.menuOpen = false}>Pricing</a>
      </div>
    `;
  }

  private renderHeaderCTA() {
    const { isAuthenticated } = this.authState;

    if (isAuthenticated) {
      return html`<a href="/" class="btn btn-primary">Open App</a>`;
    }

    return html`<a href="/auth?mode=signup" class="btn btn-primary">Get Started</a>`;
  }

  render() {
    return html`
      <header>
        <div class="header-inner">
          <a href="/" class="header-logo"><img src="/logo_small.png?v=2" alt="Scholia" />Scholia.fyi</a>
          <nav>
            <a href="/">Home</a>
            <a href="/manifesto">Manifesto</a>
            <a href="/pricing">Pricing</a>
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

      <div class="container">
        <h1>Support</h1>
        <p class="subtitle">
          I'm building Scholia to help researchers think more <em>critically</em> about their work.
          Your feedback helps make it better.
        </p>

        <div class="contact-card">
          <h2>Get in Touch</h2>
          <p>
            Scholia is built and maintained by me, Bennett. I'm committed to creating
            the best possible tool for researchers who want to engage deeply with academic literature.
          </p>
          <p>
            Whether you've found a bug, have a feature request, or just want to share how
            you're using Scholia—I'd love to hear from you.
          </p>
          <a href="https://github.com/bwaxse/scholia-oss/issues" class="email-link" target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
            </svg>
            Open an issue on GitHub
          </a>
        </div>

        <div class="info-box">
          <h3>What to Include</h3>
          <p>To help me assist you faster, please include:</p>
          <ul>
            <li>A clear description of the issue or suggestion</li>
            <li>Steps to reproduce (if reporting a bug)</li>
            <li>Your browser and operating system</li>
            <li>Screenshots if relevant</li>
          </ul>
        </div>

        <div class="personal-note">
          <p>
            I aim to respond to all inquiries within 1-2 business days.
            For urgent issues affecting your work, please mention that in your subject line.
          </p>
        </div>
      </div>

      <footer>
        <p>
          <a href="/">Home</a> · <a href="/manifesto">Manifesto</a> · <a href="/pricing">Pricing</a> · Built for researchers who think deeply.
        </p>
      </footer>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'support-page': SupportPage;
  }
}
