import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { OutlineItem } from '../../types/pdf';
import { api } from '../../services/api';
import '../shared/loading-spinner';

@customElement('outline-tab')
export class OutlineTab extends LitElement {
  @property({ type: Array }) outline: OutlineItem[] = [];
  @property({ type: String }) sessionId = '';

  @state() private loading = false;
  @state() private error = '';
  @state() private localOutline: OutlineItem[] = [];

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f8f9fa;
      overflow: hidden;
    }

    .outline-container {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .outline-item {
      padding: 8px 12px;
      cursor: pointer;
      border-radius: 4px;
      transition: background 0.15s;
      font-size: 13px;
      color: #333;
      line-height: 1.4;
    }

    .outline-item:hover {
      background: #e8f0fe;
    }

    .outline-item.level-0 {
      font-weight: 600;
      font-size: 14px;
    }

    .outline-item.level-1 {
      padding-left: 24px;
      font-weight: 500;
    }

    .outline-item.level-2 {
      padding-left: 36px;
      font-size: 12px;
      color: #555;
    }

    .outline-item.level-3 {
      padding-left: 48px;
      font-size: 12px;
      color: #666;
    }

    .page-number {
      float: right;
      color: #888;
      font-size: 11px;
      font-weight: normal;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px;
      text-align: center;
      color: #666;
      height: 100%;
    }

    .empty-state h3 {
      margin: 0 0 8px 0;
      font-size: 16px;
      color: #333;
    }

    .empty-state p {
      margin: 0;
      font-size: 14px;
      line-height: 1.5;
    }

    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
    }

    .error-message {
      padding: 16px;
      margin: 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #dc2626;
      font-size: 13px;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Load outline when component connects if we have a session
    if (this.sessionId && this.outline.length === 0) {
      this.loadOutline();
    }
  }

  updated(changedProperties: Map<string, unknown>) {
    // If outline is provided externally, use it
    if (changedProperties.has('outline') && this.outline.length > 0) {
      this.localOutline = this.outline;
    }
    // If sessionId changes, clear error and load outline if needed
    if (changedProperties.has('sessionId') && this.sessionId) {
      this.error = '';
      if (this.localOutline.length === 0) {
        this.loadOutline();
      }
    }
  }

  private async loadOutline() {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      const outline = await api.getOutline(this.sessionId);
      this.localOutline = outline;
    } catch (err) {
      console.error('Failed to load outline:', err);
      this.error = 'Failed to load document outline';
    } finally {
      this.loading = false;
    }
  }

  private handleItemClick(item: OutlineItem) {
    this.dispatchEvent(
      new CustomEvent('navigate-to-page', {
        detail: { page: item.page },
        bubbles: true,
        composed: true
      })
    );
  }

  private renderOutlineItem(item: OutlineItem): unknown {
    const levelClass = `level-${Math.min(item.level, 3)}`;

    return html`
      <div
        class="outline-item ${levelClass}"
        @click=${() => this.handleItemClick(item)}
      >
        ${item.title}
        <span class="page-number">${item.page}</span>
      </div>
      ${item.children?.map((child) => this.renderOutlineItem(child))}
    `;
  }

  render() {
    if (!this.sessionId) {
      return html`
        <div class="empty-state">
          <h3>No paper loaded</h3>
          <p>Upload a PDF to view its outline.</p>
        </div>
      `;
    }

    if (this.loading) {
      return html`
        <div class="loading-container">
          <loading-spinner message="Loading outline..."></loading-spinner>
        </div>
      `;
    }

    if (this.error) {
      return html`
        <div class="error-message">${this.error}</div>
      `;
    }

    const outlineToRender = this.localOutline.length > 0 ? this.localOutline : this.outline;

    if (outlineToRender.length === 0) {
      return html`
        <div class="empty-state">
          <h3>No outline available</h3>
          <p>This PDF doesn't have a table of contents, or it couldn't be extracted.</p>
        </div>
      `;
    }

    return html`
      <div class="outline-container">
        ${outlineToRender.map((item) => this.renderOutlineItem(item))}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'outline-tab': OutlineTab;
  }
}
