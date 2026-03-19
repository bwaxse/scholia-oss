import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('loading-spinner')
export class LoadingSpinner extends LitElement {
  @property({ type: String }) message = 'Loading...';
  @property({ type: String }) size = 'medium'; // 'small' | 'medium' | 'large'
  @property({ type: Boolean }) light = false; // Use light text for dark backgrounds

  static styles = css`
    :host {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }

    .spinner {
      border: 3px solid rgba(26, 115, 232, 0.1);
      border-top-color: #3d2f2a;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .spinner.small {
      width: 20px;
      height: 20px;
      border-width: 2px;
    }

    .spinner.medium {
      width: 32px;
      height: 32px;
      border-width: 3px;
    }

    .spinner.large {
      width: 48px;
      height: 48px;
      border-width: 4px;
    }

    .message {
      color: #666;
      font-size: 14px;
    }

    .message.light {
      color: white;
    }

    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
  `;

  render() {
    return html`
      <div class="spinner ${this.size}"></div>
      ${this.message ? html`<div class="message ${this.light ? 'light' : ''}">${this.message}</div>` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'loading-spinner': LoadingSpinner;
  }
}
