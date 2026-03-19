/**
 * Welcome/Landing page - public entry point
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { authService, type AuthState } from '../services/auth';

@customElement('welcome-page')
export class WelcomePage extends LitElement {
  @state() private authState: AuthState = {
    isAuthenticated: false,
    isLoading: true,
    user: null
  };

  @state() private menuOpen = false;
  @state() private authError = '';

  private static readonly ERROR_MESSAGES: Record<string, string> = {
    account_deleted: 'This account has been deleted. Please open an issue on GitHub if you believe this is an error.',
    auth_failed: 'Sign-in failed. Please try again.',
    missing_user_info: 'Sign-in failed: could not retrieve your account information.',
    oauth_not_configured: 'Sign-in is currently unavailable. Please try again later.',
  };

  connectedCallback() {
    super.connectedCallback();
    authService.subscribe((state) => {
      this.authState = state;
    });

    const params = new URLSearchParams(window.location.search);
    const error = params.get('error') ?? '';
    this.authError = WelcomePage.ERROR_MESSAGES[error] ?? (error ? 'Sign-in failed. Please try again.' : '');
    // Clear the error param so stale bookmarks or back-nav don't re-show the banner
    if (error) {
      window.history.replaceState({}, '', window.location.pathname);
    }
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: #fdfaf8;
      color: #3d2f2a;
      font-family: 'Lora', Georgia, serif;
    }

    /* Header - Glassmorphism */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.875rem 2rem;
      background: rgba(253, 250, 248, 0.9);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid #e8dfd9;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .header-logo {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      font-family: Georgia, 'Times New Roman', serif;
      color: #3d2f2a;
      font-size: 1.25rem;
      font-weight: 500;
    }

    .header-logo img {
      height: 20px;
      width: auto;
    }


    .header-actions {
      display: flex;
      gap: 1.75rem;
      align-items: center;
    }

    .header-link {
      color: #6b574f;
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      transition: color 0.15s;
    }

    .header-link:hover {
      color: #3d2f2a;
    }

    .header-btn {
      background: #3d2f2a;
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      text-decoration: none;
      font-size: 0.8125rem;
      font-weight: 600;
      transition: all 0.15s;
    }

    .header-btn:hover {
      background: #2d211c;
    }

    .header-status {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .user-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      object-fit: cover;
    }

    /* Mobile menu */
    .hamburger {
      display: none;
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      color: #3d2f2a;
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
      background: white;
      border-bottom: 1px solid #e8dfd9;
      padding: 16px 24px;
      flex-direction: column;
      gap: 12px;
      z-index: 99;
      box-shadow: 0 4px 12px rgba(61, 47, 42, 0.1);
    }

    .mobile-menu.open {
      display: flex;
    }

    .mobile-menu a,
    .mobile-menu span {
      color: #3d2f2a;
      text-decoration: none;
      padding: 12px 0;
      font-size: 16px;
      border-bottom: 1px solid #f9f3ef;
    }

    .mobile-menu a:last-child {
      border-bottom: none;
    }

    .auth-error-banner {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      max-width: 1000px;
      margin: 1rem auto 0;
      padding: 0.75rem 1rem;
      background: white;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #991b1b;
      font-size: 0.875rem;
      font-family: 'Lora', Georgia, serif;
    }

    .auth-error-banner svg {
      flex-shrink: 0;
    }

    /* Hero Section */
    .hero-section {
      background: white;
      border-bottom: 1px solid #e8dfd9;
    }

    .hero {
      max-width: 1200px;
      margin: 0 auto;
      padding: 6rem 2rem 5rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4rem;
      align-items: center;
    }

    .hero-content {
      max-width: 520px;
    }

    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #a64b2d;
      background: #fce9e2;
      padding: 0.375rem 0.75rem;
      border-radius: 100px;
      margin-bottom: 1.5rem;
    }

    .hero h1 {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 3.5rem;
      font-weight: 400;
      margin: 0 0 1.5rem 0;
      color: #3d2f2a;
      letter-spacing: -0.02em;
      line-height: 1.1;
    }

    .hero h1 em {
      font-style: italic;
      font-weight: 500;
      color: #a64b2d;
    }

    .hero .subtitle {
      font-size: 1.125rem;
      color: #6b574f;
      margin: 0 0 2rem 0;
      line-height: 1.7;
    }

    .hero-ctas {
      display: flex;
      gap: 1rem;
    }

    .hero-visual {
      background: white;
      border: 1px solid #e8dfd9;
      border-radius: 16px;
      padding: 2rem;
      box-shadow: 0 4px 24px rgba(61, 47, 42, 0.04);
    }

    .visual-header {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.5rem;
    }

    .visual-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #e8dfd9;
    }

    .visual-content {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .visual-line {
      height: 12px;
      background: #f9f3ef;
      border-radius: 6px;
    }

    .visual-line.short { width: 60%; }
    .visual-line.medium { width: 80%; }
    .visual-line.highlight {
      background: #fce9e2;
      border-left: 3px solid #c45d3a;
    }

    .btn {
      padding: 0.75rem 1.5rem;
      border-radius: 6px;
      font-size: 0.9375rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: none;
      font-family: inherit;
    }

    .btn-primary {
      background: #3d2f2a;
      color: white;
    }

    .btn-primary:hover {
      background: #2d211c;
      transform: translateY(-1px);
    }

    .btn-secondary {
      background: white;
      color: #3d2f2a;
      border: 1px solid #e8dfd9;
    }

    .btn-secondary:hover {
      background: #f9f3ef;
      border-color: #a08a80;
    }

    /* Three Pillars Section */
    .pillars {
      padding: 4rem 2rem;
      /* Uses page background #fdfaf8 for contrast with white hero */
    }

    .pillars-inner {
      max-width: 1000px;
      margin: 0 auto;
    }

    .section-title {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 1.875rem;
      font-weight: 400;
      text-align: center;
      margin: 0 0 16px 0;
      color: #3d2f2a;
    }

    .section-subtitle {
      text-align: center;
      color: #6b574f;
      font-size: 1.0625rem;
      margin: 0 0 48px 0;
      line-height: 1.7;
    }

    .pillars-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.5rem;
    }

    .pillar {
      background: white;
      border: 1px solid #e8dfd9;
      border-radius: 8px;
      padding: 1.5rem;
      transition: box-shadow 0.2s;
    }

    .pillar:hover {
      box-shadow: 0 8px 24px rgba(61, 47, 42, 0.08);
    }

    .pillar-icon {
      font-size: 32px;
      margin-bottom: 16px;
    }

    .pillar-label {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #a08a80;
      margin-bottom: 8px;
    }

    .pillar h3 {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 1.125rem;
      font-weight: 500;
      margin: 0 0 12px 0;
      color: #3d2f2a;
    }

    .pillar p {
      color: #6b574f;
      line-height: 1.6;
      margin: 0;
      font-size: 0.9375rem;
    }

    /* Method Section */
    .method {
      background: #f9f3ef;
      padding: 4rem 2rem;
    }

    .method-container {
      max-width: 800px;
      margin: 0 auto;
    }

    .method-steps {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .method-step {
      display: flex;
      gap: 24px;
      align-items: flex-start;
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      border: 1px solid #e8dfd9;
    }

    .step-number {
      width: 48px;
      height: 48px;
      background: #3d2f2a;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 600;
      flex-shrink: 0;
    }

    .step-content h3 {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 1.125rem;
      font-weight: 500;
      margin: 0 0 8px 0;
      color: #3d2f2a;
    }

    .step-content p {
      color: #6b574f;
      margin: 0;
      line-height: 1.6;
    }

    /* Examples Section */
    .examples {
      padding: 4rem 2rem;
      background: white;
      border-top: 1px solid #e8dfd9;
      border-bottom: 1px solid #e8dfd9;
    }

    .examples-inner {
      max-width: 800px;
      margin: 0 auto;
    }

    .example-cards {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .example-card {
      background: white;
      border: 1px solid #e8dfd9;
      border-radius: 8px;
      padding: 1.5rem;
    }

    .example-prompt {
      font-family: 'SF Mono', Monaco, monospace;
      font-size: 14px;
      color: #a64b2d;
      background: #fce9e2;
      padding: 12px 16px;
      border-radius: 6px;
      margin-bottom: 12px;
    }

    .example-description {
      color: #6b574f;
      font-size: 14px;
      font-style: italic;
    }

    /* Trust Section */
    .trust {
      background: #3d2f2a;
      color: white;
      padding: 4rem 2rem;
      text-align: center;
    }

    .trust h2 {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 1.875rem;
      font-weight: 400;
      margin: 0 0 16px 0;
    }

    .trust p {
      max-width: 700px;
      margin: 0 auto;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.7;
      font-size: 1rem;
    }

    /* Footer CTA */
    .footer-cta {
      text-align: center;
      padding: 4rem 2rem;
      background: white;
    }

    .footer-cta h2 {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 1.875rem;
      font-weight: 400;
      margin: 0 0 24px 0;
      color: #3d2f2a;
    }

    /* Footer */
    footer {
      padding: 1.5rem 2rem;
      text-align: center;
      font-size: 0.8125rem;
      color: #a08a80;
      border-top: 1px solid #e8dfd9;
    }

    footer a {
      color: #6b574f;
      text-decoration: none;
    }

    footer a:hover {
      color: #a64b2d;
    }

    footer .tagline {
      display: inline;
    }

    /* Responsive */
    @media (max-width: 900px) {
      .header-actions {
        display: none;
      }

      .hamburger {
        display: block;
      }

      .hero {
        grid-template-columns: 1fr;
        padding: 4rem 1.5rem 3rem;
        text-align: center;
      }

      .hero-content {
        max-width: 100%;
      }

      .hero-badge {
        margin-left: auto;
        margin-right: auto;
      }

      .hero h1 {
        font-size: 2.5rem;
      }

      .hero-ctas {
        justify-content: center;
      }

      .hero-visual {
        display: none;
      }

      .pillars-grid {
        grid-template-columns: 1fr;
      }

      .method-step {
        flex-direction: column;
        text-align: center;
      }

      .step-number {
        margin: 0 auto;
      }
    }

    @media (max-width: 480px) {
      header {
        padding: 0.75rem 1rem;
      }

      .header-logo span {
        display: none;
      }

      .user-avatar {
        width: 24px;
        height: 24px;
      }

      .hero {
        padding: 2.5rem 1rem 2rem;
      }

      .hero h1 {
        font-size: 2rem;
      }

      .hero-ctas {
        flex-direction: column;
      }

      .btn {
        width: 100%;
        justify-content: center;
        font-size: 15px;
        padding: 12px 20px;
      }

      footer .tagline {
        display: block;
        margin-top: 8px;
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
          <a href="/manifesto" @click=${() => this.menuOpen = false}>Manifesto</a>
          
          <a href="/" @click=${() => this.menuOpen = false}>Open App</a>
        </div>
      `;
    }

    return html`
      <div class="mobile-menu ${this.menuOpen ? 'open' : ''}">
        <a href="/manifesto" @click=${() => this.menuOpen = false}>Manifesto</a>
        
        
        
      </div>
    `;
  }

  private renderHeaderActions() {
    const { isAuthenticated, isLoading, user } = this.authState;

    if (isLoading) {
      return html`<span class="header-link">Loading...</span>`;
    }

    if (isAuthenticated && user) {
      return html`
        <a href="/manifesto" class="header-link">Manifesto</a>
        <div class="header-status">
          <a href="/" class="header-btn">Open App</a>
        </div>
      `;
    }

    return html`
      <a href="/manifesto" class="header-link">Manifesto</a>
      <a href="/" class="header-btn">Open App</a>
    `;
  }

  private renderHeroCTA(includeSecondary = true) {
    const { isAuthenticated } = this.authState;

    if (isAuthenticated) {
      return html`
        <a href="/" class="btn btn-primary">Open App</a>
        ${includeSecondary ? html`<a href="/manifesto" class="btn btn-secondary">Read Manifesto</a>` : ''}
      `;
    }

    return html`
      <a href="/" class="btn btn-primary">Open App</a>
      ${includeSecondary ? html`<a href="/manifesto" class="btn btn-secondary">Read Manifesto</a>` : ''}
    `;
  }

  render() {
    return html`
      <header>
        <a href="/" class="header-logo">
          <img src="/logo_small.png?v=2" alt="Scholia" />
          Scholia.fyi
        </a>
        <div class="header-actions">
          ${this.renderHeaderActions()}
        </div>
        <button class="hamburger" @click=${this.toggleMenu}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12h18M3 6h18M3 18h18"/>
          </svg>
        </button>
      </header>

      ${this.renderMobileMenu()}

      ${this.authError ? html`
        <div class="auth-error-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          ${this.authError}
        </div>
      ` : ''}

      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero">
          <div class="hero-content">
            <span class="hero-badge">AI-Powered Research</span>
            <h1>Read <em>critically.</em></h1>
            <p class="subtitle">
              Scholia uses AI to accelerate research appraisal and capture insights in the margins. Move beyond skimming to true critical engagement.
            </p>
            <div class="hero-ctas">
              ${this.renderHeroCTA()}
            </div>
          </div>
          <div class="hero-visual">
            <div class="visual-header">
              <span class="visual-dot"></span>
              <span class="visual-dot"></span>
              <span class="visual-dot"></span>
            </div>
            <div class="visual-content">
              <div class="visual-line medium"></div>
              <div class="visual-line"></div>
              <div class="visual-line highlight"></div>
              <div class="visual-line short"></div>
              <div class="visual-line medium"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- Three Pillars Section -->
      <section class="pillars">
        <div class="pillars-inner">
          <h2 class="section-title">The Three Pillars of Appraisal</h2>
          <p class="section-subtitle">Move beyond skimming to true critical engagement</p>

          <div class="pillars-grid">
            <div class="pillar">
              <div class="pillar-label">Sift</div>
              <h3>Instant Structural Analysis</h3>
              <p>Claude or Gemini identify the core thesis, methodology, and evidence gaps in seconds. No more "skimming" to find the results.</p>
            </div>

            <div class="pillar">
              <div class="pillar-label">Scrutinize</div>
              <h3>Dialectical Margins</h3>
              <p>Highlight any claim to see the counter-arguments, related citations, or potential biases. Don't just read the text; challenge it.</p>
            </div>

            <div class="pillar">
              <div class="pillar-label">Synthesize</div>
              <h3>Evidence Capture</h3>
              <p>Automatically export appraisals into a structured "Scholium"--perfect for literature reviews or Zotero libraries.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Method Section -->
      <section class="method">
        <div class="method-container">
          <h2 class="section-title">The Scholia Method</h2>
          <p class="section-subtitle">Human insight, AI-accelerated</p>

          <div class="method-steps">
            <div class="method-step">
              <div class="step-number">1</div>
              <div class="step-content">
                <h3>Ingest</h3>
                <p>Load a PDF from Zotero, or drop in a PDF directly. Your paper is ready for analysis in seconds.</p>
              </div>
            </div>

            <div class="method-step">
              <div class="step-number">2</div>
              <div class="step-content">
                <h3>Appraise</h3>
                <p>Use AI-powered shortcuts like "Analyze the methodological rigor" or "Summarize the limitations the authors omitted."</p>
              </div>
            </div>

            <div class="method-step">
              <div class="step-number">3</div>
              <div class="step-content">
                <h3>Note</h3>
                <p>Save the insights from your conversation, and upload to Zotero, Notion, or Google Drive.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Examples Section -->
      <section class="examples">
        <div class="examples-inner">
          <h2 class="section-title">Appraisal in Action</h2>
          <p class="section-subtitle">See how fast critical analysis becomes</p>

          <div class="example-cards">
            <div class="example-card">
              <div class="example-prompt">"Check for Overstatement"</div>
              <p class="example-description">Does the conclusion go beyond what the data support?</p>
            </div>

            <div class="example-card">
              <div class="example-prompt">"Verify Methodology"</div>
              <p class="example-description">Is the sample size sufficient for these findings?</p>
            </div>

            <div class="example-card">
              <div class="example-prompt">"Find the Friction"</div>
              <p class="example-description">Where does this paper disagree with current consensus?</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Trust Section -->
      <section class="trust">
        <h2>Grounded in the Source.</h2>
        <p>
          Scholia.fyi is designed for accuracy. Every insight Claude provides is cross-referenced with the text.
          We don't "read between the lines" to invent meaning; Scholia contextualizes the lines to find the truth.
        </p>
      </section>

      <!-- Footer CTA -->
      <section class="footer-cta">
        <h2>Stop skimming. Start appraising.</h2>
        ${this.renderHeroCTA(false)}
      </section>

      <footer>
        <p>
          <a href="/manifesto">Manifesto</a> |
          <span class="tagline">Built for researchers who think deeply about what they read.</span>
        </p>
      </footer>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'welcome-page': WelcomePage;
  }
}
