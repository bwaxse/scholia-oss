import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('error-message')
export class ErrorMessage extends LitElement {
  @property({ type: String }) message = 'An error occurred';
  @property({ type: Boolean }) dismissible = false;
  @property({ type: String }) actionHref = '';
  @property({ type: String }) actionLabel = 'Go to Settings';

  static styles = css`
    :host {
      display: block;
    }

    .error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 12px 16px;
      color: #991b1b;
      font-size: 14px;
      line-height: 1.5;
      display: flex;
      align-items: start;
      gap: 12px;
    }

    .icon {
      flex-shrink: 0;
      color: #991b1b;
      margin-top: 1px;
    }

    .content {
      flex: 1;
    }

    .action-link {
      display: inline-block;
      margin-top: 6px;
      color: #991b1b;
      font-weight: 600;
      text-decoration: underline;
      cursor: pointer;
    }

    .action-link:hover {
      opacity: 0.8;
    }

    .dismiss {
      background: none;
      border: none;
      color: #991b1b;
      cursor: pointer;
      font-size: 20px;
      padding: 0;
      line-height: 1;
      opacity: 0.6;
    }

    .dismiss:hover {
      opacity: 1;
    }
  `;

  private handleDismiss() {
    this.dispatchEvent(new CustomEvent('dismiss', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="error">
        <div class="icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="content">
          ${this.message}
          ${this.actionHref
            ? html`<br /><a class="action-link" @click=${(e: Event) => {
                e.preventDefault();
                window.history.pushState({}, '', this.actionHref);
                window.dispatchEvent(new PopStateEvent('popstate'));
              }}>${this.actionLabel}</a>`
            : ''}
        </div>
        ${this.dismissible
          ? html`<button class="dismiss" @click=${this.handleDismiss}>×</button>`
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'error-message': ErrorMessage;
  }
}
