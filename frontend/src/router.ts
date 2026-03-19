/**
 * Main application router
 *
 * Routes:
 * - / : App shell (always authenticated locally)
 * - /about : About/landing page
 * - /manifesto : Manifesto page
 * - /support : Support page
 * - /settings : Settings page
 * - /session/:id : View a specific paper session
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';

// Import page components
import './pages/welcome-page';
import './pages/manifesto-page';
import './pages/support-page';
import './pages/settings-page';
import './pages/app-shell';

@customElement('app-router')
export class AppRouter extends LitElement {
  @state() private currentPath: string = window.location.pathname;

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      min-height: 100dvh;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('popstate', this.handlePopState);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('popstate', this.handlePopState);
  }

  private handlePopState = () => {
    this.currentPath = window.location.pathname;
  };

  private renderRoute() {
    const path = this.currentPath;

    // Root path: show app
    if (path === '/' || path === '') {
      return html`<app-shell></app-shell>`;
    }

    if (path === '/about') {
      return html`<welcome-page></welcome-page>`;
    }

    // Redirect legacy /welcome to /about
    if (path === '/welcome') {
      window.history.replaceState({}, '', '/about');
      return html`<welcome-page></welcome-page>`;
    }

    if (path === '/manifesto') {
      return html`<manifesto-page></manifesto-page>`;
    }

    if (path === '/support') {
      return html`<support-page></support-page>`;
    }

    if (path === '/settings') {
      return html`<settings-page></settings-page>`;
    }

    // Session routes
    const sessionMatch = path.match(/^\/session\/(.+)$/);
    if (sessionMatch) {
      return html`<app-shell .sessionId=${sessionMatch[1]}></app-shell>`;
    }

    // Default to welcome page
    return html`<welcome-page></welcome-page>`;
  }

  render() {
    return this.renderRoute();
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-router': AppRouter;
  }
}
