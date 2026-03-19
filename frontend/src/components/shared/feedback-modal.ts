import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('feedback-modal')
export class FeedbackModal extends LitElement {
  @property({ type: Boolean }) visible = false;
  @property({ type: Number }) exchangeId = 0;

  @state() private inaccurate = false;
  @state() private unhelpful = false;
  @state() private offTopic = false;
  @state() private other = false;
  @state() private feedbackText = '';

  static styles = css`
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      align-items: center;
      justify-content: center;
    }

    .modal-overlay.visible {
      display: flex;
    }

    .modal-content {
      background: white;
      border-radius: 8px;
      padding: 24px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }

    .modal-title {
      font-size: 18px;
      font-weight: 600;
      color: #333;
      margin: 0 0 16px 0;
    }

    .checkbox-group {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 16px;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      font-size: 14px;
      color: #333;
    }

    .checkbox-label input[type="checkbox"] {
      cursor: pointer;
      width: 16px;
      height: 16px;
    }

    .feedback-textarea {
      width: 100%;
      min-height: 80px;
      padding: 8px;
      border: 1px solid #e8dfd9;
      border-radius: 4px;
      font-family: inherit;
      font-size: 14px;
      resize: vertical;
      margin-bottom: 16px;
      box-sizing: border-box;
    }

    .feedback-textarea:focus {
      outline: none;
      border-color: #3d2f2a;
    }

    .button-group {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }

    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }

    .btn-cancel {
      background: #f0f0f0;
      color: #333;
    }

    .btn-cancel:hover {
      background: #e0e0e0;
    }

    .btn-submit {
      background: #3d2f2a;
      color: white;
    }

    .btn-submit:hover {
      background: #2d211c;
    }

    .btn-skip {
      background: transparent;
      color: #666;
      text-decoration: underline;
      padding: 8px 12px;
    }

    .btn-skip:hover {
      color: #333;
    }
  `;

  private handleSubmit() {
    this.dispatchEvent(
      new CustomEvent('submit-feedback', {
        detail: {
          exchangeId: this.exchangeId,
          reasons: {
            inaccurate: this.inaccurate,
            unhelpful: this.unhelpful,
            offTopic: this.offTopic,
            other: this.other
          },
          feedbackText: this.feedbackText.trim() || undefined
        },
        bubbles: true,
        composed: true
      })
    );
    this.resetForm();
  }

  private handleSkip() {
    // Just submit with no reasons/text (still saves as negative rating)
    this.dispatchEvent(
      new CustomEvent('submit-feedback', {
        detail: {
          exchangeId: this.exchangeId,
          reasons: {},
          feedbackText: undefined
        },
        bubbles: true,
        composed: true
      })
    );
    this.resetForm();
  }

  private handleCancel() {
    this.dispatchEvent(
      new CustomEvent('cancel-feedback', {
        bubbles: true,
        composed: true
      })
    );
    this.resetForm();
  }

  private resetForm() {
    this.inaccurate = false;
    this.unhelpful = false;
    this.offTopic = false;
    this.other = false;
    this.feedbackText = '';
  }

  render() {
    return html`
      <div class="modal-overlay ${this.visible ? 'visible' : ''}" @click=${this.handleCancel}>
        <div class="modal-content" @click=${(e: Event) => e.stopPropagation()}>
          <h3 class="modal-title">What went wrong?</h3>

          <div class="checkbox-group">
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this.inaccurate}
                @change=${(e: Event) => this.inaccurate = (e.target as HTMLInputElement).checked}
              />
              <span>Inaccurate</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this.unhelpful}
                @change=${(e: Event) => this.unhelpful = (e.target as HTMLInputElement).checked}
              />
              <span>Unhelpful</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this.offTopic}
                @change=${(e: Event) => this.offTopic = (e.target as HTMLInputElement).checked}
              />
              <span>Off-topic</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this.other}
                @change=${(e: Event) => this.other = (e.target as HTMLInputElement).checked}
              />
              <span>Other</span>
            </label>
          </div>

          <textarea
            class="feedback-textarea"
            placeholder="Additional details (optional)"
            .value=${this.feedbackText}
            @input=${(e: Event) => this.feedbackText = (e.target as HTMLTextAreaElement).value}
          ></textarea>

          <div class="button-group">
            <button class="btn btn-skip" @click=${this.handleSkip}>
              Skip
            </button>
            <button class="btn btn-cancel" @click=${this.handleCancel}>
              Cancel
            </button>
            <button class="btn btn-submit" @click=${this.handleSubmit}>
              Submit
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'feedback-modal': FeedbackModal;
  }
}
