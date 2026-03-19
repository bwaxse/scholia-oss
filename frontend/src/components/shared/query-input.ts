import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import type { ModelType } from '../../types/query';

@customElement('query-input')
export class QueryInput extends LitElement {
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;
  @property({ type: Boolean }) disabled = false;
  @property({ type: Boolean }) loading = false;
  @property({ type: Boolean }) insufficientCredits = false;  // When true, button stays enabled for modal
  @property({ type: String }) selectedModel: ModelType = 'sonnet';
  @property({ type: Boolean }) geminiAvailable = false;
  @property({ type: Object }) modelAccess = { haiku: true, flash: true, sonnet: false, gemini_pro: false };

  @state() private queryText = '';

  @query('textarea') private textarea!: HTMLTextAreaElement;

  static styles = css`
    :host {
      display: block;
      background: white;
      border-top: 1px solid #e8dfd9;
      padding: 16px;
    }

    .selected-text-preview {
      background: rgba(255, 235, 59, 0.4);
      border: 1px solid #ffc107;
      border-radius: 4px;
      padding: 8px 12px;
      margin-bottom: 12px;
      font-size: 13px;
      color: #5d4e00;
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 8px;
    }

    .preview-content {
      flex: 1;
      line-height: 1.4;
    }

    .preview-label {
      font-weight: 500;
      margin-bottom: 4px;
    }

    .preview-text {
      font-style: italic;
      max-height: 60px;
      overflow-y: auto;
    }

    .clear-selection {
      background: none;
      border: none;
      color: #5d4e00;
      cursor: pointer;
      font-size: 18px;
      padding: 0;
      opacity: 0.6;
      line-height: 1;
    }

    .clear-selection:hover {
      opacity: 1;
    }

    .input-area {
      position: relative;
    }

    textarea {
      width: 100%;
      min-height: 80px;
      max-height: 200px;
      padding: 12px;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      font-size: 12px;
      font-family: inherit;
      resize: vertical;
      box-sizing: border-box;
    }

    textarea:focus {
      outline: none;
      border-color: #3d2f2a;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
    }

    textarea:disabled {
      background: #f5f5f5;
      cursor: not-allowed;
    }

    .footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
    }

    .hint {
      font-size: 12px;
      color: #999;
    }

    .actions {
      display: flex;
      gap: 8px;
    }

    .submit-btn {
      padding: 8px 20px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .submit-btn:hover:not(:disabled) {
      background: #1557b0;
    }

    .submit-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .submit-btn.loading {
      display: flex;
      align-items: center;
      gap: 8px;
      justify-content: center;
    }

    .spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .model-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #666;
    }

    .model-toggle input {
      cursor: pointer;
    }

    .char-count {
      font-size: 12px;
      color: #999;
    }

    .char-count.warning {
      color: #f4b400;
    }

    /* Mobile-only model toggle and thinking */
    .mobile-model-toggle {
      display: none; /* Hidden on desktop */
    }


    .hint-break {
      display: none; /* Hidden on desktop */
    }

    .hint-main,
    .hint-secondary {
      display: inline; /* Inline on desktop */
    }

    .hint-secondary::before {
      content: ' · '; /* Separator on desktop */
    }

    .hint-disclaimer {
      display: inline;
    }

    .hint-disclaimer::before {
      content: ' · ';
    }

    @media (max-width: 768px) {
      .hint-break {
        display: block; /* Show line break on mobile */
      }

      .hint-main {
        display: inline; /* Keep Enter to send inline */
      }

      .hint-secondary {
        display: block; /* Put Shift+Enter on new line */
        margin-top: 2px;
      }

      .hint-secondary::before {
        content: ''; /* Remove separator on mobile */
      }

      .hint-disclaimer {
        display: none; /* Hide on mobile to keep footer clean */
      }
      .mobile-model-toggle {
        display: flex;
        margin-right: 8px;
      }

      .model-select {
        padding: 6px 10px;
        font-size: 12px;
        border: 1px solid #e8dfd9;
        border-radius: 4px;
        background: white;
        color: #333;
        cursor: pointer;
        font-weight: 500;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M3 4.5l3 3 3-3'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 6px center;
        padding-right: 24px;
      }

      .model-select:focus {
        outline: none;
        border-color: #3d2f2a;
      }

      .model-select:disabled {
        background-color: #f5f5f5;
        cursor: not-allowed;
      }

      .hint {
        font-size: 11px;
        line-height: 1.5;
      }

      .footer {
        /* Keep hint and actions side-by-side on mobile */
        align-items: flex-start;
      }

      .actions {
        flex-shrink: 0;
      }

      .submit-btn {
        /* Keep original button size on mobile */
      }
    }
  `;

  private handleClearSelection() {
    this.dispatchEvent(
      new CustomEvent('clear-selection', {
        bubbles: true,
        composed: true
      })
    );
  }

  private handleModelChange(model: ModelType) {
    this.dispatchEvent(
      new CustomEvent('model-change', {
        detail: { model },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleModelSelectChange(e: Event) {
    const select = e.target as HTMLSelectElement;
    const model = select.value as ModelType;
    // Prevent selection of restricted models
    if (model === 'sonnet' && !this.modelAccess.sonnet) {
      select.value = this.selectedModel;
      return;
    }
    if (model === 'gemini-pro' && !this.modelAccess.gemini_pro) {
      select.value = this.selectedModel;
      return;
    }
    this.handleModelChange(model);
  }

  private handleSubmit() {
    const query = this.queryText.trim();
    if (!query) return;

    this.dispatchEvent(
      new CustomEvent('submit-query', {
        detail: {
          query,
          highlighted_text: this.selectedText || undefined,
          page: this.selectedPage
        },
        bubbles: true,
        composed: true
      })
    );

    this.queryText = '';
    if (this.textarea) {
      this.textarea.style.height = 'auto';
    }

    // Clear selected text after submitting
    if (this.selectedText) {
      this.dispatchEvent(
        new CustomEvent('clear-selection', {
          bubbles: true,
          composed: true
        })
      );
    }
  }

  private handleKeyDown(e: KeyboardEvent) {
    // Submit on Enter (without Shift for new line)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.handleSubmit();
    }
  }

  private handleInput(e: Event) {
    const target = e.target as HTMLTextAreaElement;
    this.queryText = target.value;

    // Auto-resize textarea
    target.style.height = 'auto';
    target.style.height = target.scrollHeight + 'px';
  }

  render() {
    const charCount = this.queryText.length;
    const showWarning = charCount > 500;

    return html`
      ${this.selectedText
        ? html`
            <div class="selected-text-preview">
              <div class="preview-content">
                <div class="preview-label">
                  Selected text${this.selectedPage ? ` (Page ${this.selectedPage})` : ''}:
                </div>
                <div class="preview-text">"${this.selectedText}"</div>
              </div>
              <button
                class="clear-selection"
                @click=${this.handleClearSelection}
                title="Clear selection"
              >
                ×
              </button>
            </div>
          `
        : ''}

      <div class="input-area">
        <textarea
          placeholder="Ask a question..."
          .value=${this.queryText}
          @input=${this.handleInput}
          @keydown=${this.handleKeyDown}
          ?disabled=${this.disabled || this.loading}
        ></textarea>
      </div>

      <div class="footer">
        <div class="hint">
          <span class="hint-main">Enter to send</span>
          <br class="hint-break" />
          <span class="hint-secondary">Shift+Enter for new line</span>
          <span class="hint-disclaimer">AI responses may contain errors</span>
          ${charCount > 0
            ? html`
                <span class="char-count ${showWarning ? 'warning' : ''}">
                  · ${charCount} chars
                </span>
              `
            : ''}
        </div>
        <div class="actions">
          <!-- Mobile-only model toggle (hidden on desktop) -->
          <div class="mobile-model-toggle">
            <select
              class="model-select"
              .value=${this.selectedModel}
              @change=${this.handleModelSelectChange}
              ?disabled=${this.disabled || this.loading}
            >
              <optgroup label="Claude">
                <option value="sonnet" ?disabled=${!this.modelAccess.sonnet}>
                  Sonnet${!this.modelAccess.sonnet ? ' (Pro)' : ''}
                </option>
                <option value="haiku">Haiku</option>
              </optgroup>
              ${this.geminiAvailable ? html`
                <optgroup label="Gemini">
                  <option value="gemini-flash">Flash</option>
                  <option value="gemini-pro" ?disabled=${!this.modelAccess.gemini_pro}>
                    Pro${!this.modelAccess.gemini_pro ? ' (Max)' : ''}
                  </option>
                </optgroup>
              ` : ''}
            </select>
          </div>
          <button
            class="submit-btn ${this.loading ? 'loading' : ''}"
            @click=${this.handleSubmit}
            ?disabled=${this.disabled || this.loading || (!this.insufficientCredits && !this.queryText.trim())}
          >
            ${this.loading
              ? html`<div class="spinner"></div>Thinking...`
              : 'Ask'}
          </button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'query-input': QueryInput;
  }
}
