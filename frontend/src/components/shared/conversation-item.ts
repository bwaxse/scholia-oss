import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import type { ConversationMessage, MessageEvaluation } from '../../types/session';
import './feedback-modal';

@customElement('conversation-item')
export class ConversationItem extends LitElement {
  @property({ type: Object }) userMessage!: ConversationMessage;
  @property({ type: Object }) assistantMessage!: ConversationMessage;
  @property({ type: Boolean }) flagged = false;
  @property({ type: Object }) evaluation?: MessageEvaluation;

  @state() private expanded = false;
  @state() private showFeedbackModal = false;

  static styles = css`
    :host {
      display: block;
      margin-bottom: 16px;
    }

    .exchange {
      background: white;
      overflow: hidden;
      border-bottom: 1px solid #e8dfd9;
    }

    .question-section {
      padding: 12px;
      border-bottom: 1px solid #e8e0d0;
    }

    .question-section.claude {
      background: #f5e6d3;
      border-bottom: 1px solid #e8dcc8;
    }

    .question-section.gemini {
      background: #f8f9fa;
      border-bottom: 1px solid #e9ecef;
    }

    .question-label {
      font-weight: 700;
      color: #333;
      font-size: 13px;
      display: block;
      margin-bottom: 4px;
    }

    .question-row {
      margin-bottom: 0;
    }

    .question-content {
      display: inline;
    }

    .highlighted-text {
      background: rgba(255, 235, 59, 0.4);
      padding: 8px;
      border-radius: 4px;
      margin-bottom: 8px;
      font-size: 13px;
      color: #5d4e00;
      border-left: 3px solid #ffc107;
    }

    .highlighted-text::before {
      content: '"';
    }

    .highlighted-text::after {
      content: '"';
    }

    .user-query {
      color: #4a4a4a;
      font-weight: 500;
      font-size: 14px;
      line-height: 1.5;
      display: inline;
    }

    .user-query-block {
      display: block;
    }

    .user-query-preview {
      cursor: pointer;
    }

    .user-query-first-line {
      display: block;
    }

    .user-query-rest {
      display: block;
      color: #6b7280;
      opacity: 0.6;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-weight: 400;
    }

    .user-query-full {
      white-space: pre-wrap;
    }

    .expand-indicator {
      font-size: 12px;
      color: #6b7280;
      cursor: pointer;
      white-space: nowrap;
      margin-left: auto;
    }

    .expand-indicator:hover {
      color: #3d2f2a;
    }

    .page-indicator {
      color: #666;
      font-size: 12px;
      margin-top: 4px;
    }

    .response-section {
      padding: 12px;
    }

    .assistant-response {
      color: #333;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-wrap: break-word;
    }

    .message-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #f0f0f0;
      font-size: 12px;
      color: #999;
    }

    .meta {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .model-badge {
      background: #ede9fe;
      color: #7c4dff;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }

    .timestamp {
      color: #999;
    }

    .actions {
      display: flex;
      gap: 8px;
    }

    .flag-btn,
    .copy-btn,
    .delete-btn {
      background: none;
      border: none;
      cursor: pointer;
      font-size: 16px;
      padding: 4px;
      opacity: 0.6;
      transition: opacity 0.2s;
    }

    .flag-btn:hover,
    .copy-btn:hover,
    .delete-btn:hover {
      opacity: 1;
    }

    .flag-btn.flagged {
      opacity: 1;
      color: #f4b400;
    }

    .copy-btn {
      font-size: 14px;
    }

    .delete-btn {
      font-size: 14px;
      color: #dc2626;
    }

    .delete-btn:hover {
      color: #b91c1c;
    }

    .thumbs-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      opacity: 0.6;
      transition: opacity 0.2s;
    }

    .thumbs-btn:hover {
      opacity: 1;
    }

    .thumbs-btn.active {
      opacity: 1;
    }

    .thumbs-btn.active svg {
      fill: #e5e7eb;
    }
  `;

  private handleFlag() {
    this.dispatchEvent(
      new CustomEvent('flag-toggle', {
        detail: { exchangeId: this.assistantMessage.exchange_id },
        bubbles: true,
        composed: true
      })
    );
  }

  private async handleCopy() {
    try {
      await navigator.clipboard.writeText(this.assistantMessage.content);
      // Could show a toast notification here
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }

  private handleDelete() {
    if (confirm('Delete this Q&A exchange? This cannot be undone.')) {
      this.dispatchEvent(
        new CustomEvent('delete-exchange', {
          detail: { exchangeId: this.assistantMessage.exchange_id },
          bubbles: true,
          composed: true
        })
      );
    }
  }

  private handleThumbsUp() {
    // If already positive, toggle off (delete)
    if (this.evaluation?.rating === 'positive') {
      this.dispatchEvent(
        new CustomEvent('delete-evaluation', {
          detail: {
            exchangeId: this.assistantMessage.exchange_id
          },
          bubbles: true,
          composed: true
        })
      );
    } else {
      // Set to positive
      this.dispatchEvent(
        new CustomEvent('evaluate-message', {
          detail: {
            exchangeId: this.assistantMessage.exchange_id,
            rating: 'positive'
          },
          bubbles: true,
          composed: true
        })
      );
    }
  }

  private handleThumbsDown() {
    // If already negative, toggle off (delete)
    if (this.evaluation?.rating === 'negative') {
      this.dispatchEvent(
        new CustomEvent('delete-evaluation', {
          detail: {
            exchangeId: this.assistantMessage.exchange_id
          },
          bubbles: true,
          composed: true
        })
      );
    } else {
      // Show modal to get negative feedback details
      this.showFeedbackModal = true;
    }
  }

  private handleSubmitFeedback(e: CustomEvent) {
    this.showFeedbackModal = false;
    this.dispatchEvent(
      new CustomEvent('evaluate-message', {
        detail: {
          exchangeId: e.detail.exchangeId,
          rating: 'negative',
          reasons: e.detail.reasons,
          feedbackText: e.detail.feedbackText
        },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleCancelFeedback() {
    this.showFeedbackModal = false;
  }

  private formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }

  private getModelName(model?: string): string {
    if (!model) return '';
    if (model.includes('sonnet')) return 'Sonnet';
    if (model.includes('haiku')) return 'Haiku';
    if (model.includes('opus')) return 'Opus';
    if (model.includes('gemini')) {
      if (model.includes('flash')) return 'Flash';
      if (model.includes('pro')) return 'Pro';
      return 'Gemini';
    }
    return 'Claude';
  }

  private getProviderClass(model?: string): string {
    if (!model) return 'claude';
    return model.includes('gemini') ? 'gemini' : 'claude';
  }

  private toggleExpand() {
    this.expanded = !this.expanded;
  }

  private renderMarkdown(text: string): string {
    // Escape HTML to prevent XSS
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');

    // Convert **bold** to <strong>
    const withBold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    return withBold;
  }

  private renderUserQuery() {
    if (!this.userMessage) return '';

    const content = this.userMessage.content;
    const lines = content.split('\n');
    const hasMultipleLines = lines.length > 1 || content.length > 100;

    if (!hasMultipleLines || this.expanded) {
      return html`
        <span class="question-content">
          <span class="user-query user-query-full" @click=${this.toggleExpand}>${content}</span>${hasMultipleLines
            ? html`<span class="expand-indicator" @click=${this.toggleExpand}> [less]</span>`
            : ''}
        </span>
      `;
    }

    // Show preview with first line truncated
    const firstLine = lines[0].length > 80 ? lines[0].substring(0, 80) + '...' : lines[0];

    return html`
      <span class="question-content">
        <span class="user-query user-query-preview" @click=${this.toggleExpand}>${firstLine}</span><span class="expand-indicator" @click=${this.toggleExpand}> [more]</span>
      </span>
    `;
  }

  render() {
    if (!this.userMessage || !this.assistantMessage) {
      return html``;
    }

    return html`
      <div class="exchange">
        <div class="question-section ${this.getProviderClass(this.assistantMessage.model)}">
          ${this.userMessage.highlighted_text
            ? html`
                <div class="highlighted-text">
                  ${this.userMessage.highlighted_text}
                </div>
              `
            : ''}
          <div class="question-row">
            <span class="question-label">Question: </span>${this.renderUserQuery()}
          </div>
          ${this.userMessage.page
            ? html`
                <div class="page-indicator">Page ${this.userMessage.page}</div>
              `
            : ''}
        </div>

        <div class="response-section">
          <div class="assistant-response">${unsafeHTML(this.renderMarkdown(this.assistantMessage.content))}</div>

          <div class="message-footer">
            <div class="meta">
              ${this.assistantMessage.model
                ? html`
                    <span class="model-badge">
                      ${this.getModelName(this.assistantMessage.model)}
                    </span>
                  `
                : ''}
              <span class="timestamp">
                ${this.formatTimestamp(this.assistantMessage.timestamp)}
              </span>
            </div>
            <div class="actions">
              <!-- Thumbs Up -->
              <button
                class="thumbs-btn ${this.evaluation?.rating === 'positive' ? 'active' : ''}"
                @click=${this.handleThumbsUp}
                title="Helpful"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                </svg>
              </button>

              <!-- Thumbs Down -->
              <button
                class="thumbs-btn ${this.evaluation?.rating === 'negative' ? 'active' : ''}"
                @click=${this.handleThumbsDown}
                title="Not helpful"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                </svg>
              </button>

              <button
                class="flag-btn ${this.flagged ? 'flagged' : ''}"
                @click=${this.handleFlag}
                title="${this.flagged ? 'Unflag' : 'Flag important'}"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="${this.flagged ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                  <polygon points="12,2 15,9 22,9 17,14 19,21 12,17 5,21 7,14 2,9 9,9" />
                </svg>
              </button>
              <button
                class="copy-btn"
                @click=${this.handleCopy}
                title="Copy response"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
              <button
                class="delete-btn"
                @click=${this.handleDelete}
                title="Delete this exchange"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Feedback Modal -->
      <feedback-modal
        .visible=${this.showFeedbackModal}
        .exchangeId=${this.assistantMessage.exchange_id}
        @submit-feedback=${this.handleSubmitFeedback}
        @cancel-feedback=${this.handleCancelFeedback}
      ></feedback-modal>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'conversation-item': ConversationItem;
  }
}
