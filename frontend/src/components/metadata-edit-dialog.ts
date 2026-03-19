import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api } from '../services/api';
import type { Metadata, MetadataUpdateRequest } from '../types/metadata';

@customElement('metadata-edit-dialog')
export class MetadataEditDialog extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: Object }) initialMetadata?: Metadata;
  @property({ type: String }) sessionLabel = '';
  @property({ type: Boolean }) open = false;

  @state() private paperTitle = '';
  @state() private paperAuthors = '';
  @state() private paperDoi = '';
  @state() private paperPmid = '';
  @state() private paperJournal = '';
  @state() private paperPublicationDate = '';
  @state() private label = '';
  @state() private loading = false;
  @state() private lookingUp = false;
  @state() private errorMessage = '';

  static styles = css`
    :host {
      display: block;
    }

    .overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      padding: 20px;
    }

    .dialog {
      background: white;
      border-radius: 8px;
      max-width: 600px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }

    .header {
      padding: 20px;
      border-bottom: 1px solid #e0e0e0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 24px;
      color: #666;
      cursor: pointer;
      padding: 0;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .close-btn:hover {
      background: #f5f5f5;
    }

    .content {
      padding: 20px;
      overflow-y: auto;
      flex: 1;
    }

    .lookup-section {
      margin-bottom: 24px;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 6px;
    }

    .lookup-section h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #666;
    }

    .lookup-fields {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 8px;
      align-items: end;
    }

    .field {
      margin-bottom: 16px;
    }

    .field label {
      display: block;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 500;
      color: #555;
    }

    .field input,
    .field textarea {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      font-family: inherit;
      box-sizing: border-box;
    }

    .field input:focus,
    .field textarea:focus {
      outline: none;
      border-color: #3d2f2a;
    }

    .field textarea {
      resize: vertical;
      min-height: 80px;
      font-family: inherit;
    }

    .field-hint {
      margin-top: 4px;
      font-size: 12px;
      color: #666;
    }

    .lookup-btn {
      padding: 8px 16px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 13px;
      cursor: pointer;
      font-weight: 500;
      white-space: nowrap;
      height: 38px;
    }

    .lookup-btn:hover:not(:disabled) {
      background: #1557b0;
    }

    .lookup-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .error {
      padding: 12px;
      background: #fee;
      border: 1px solid #fcc;
      border-radius: 4px;
      color: #c33;
      font-size: 13px;
      margin-bottom: 16px;
    }

    .footer {
      padding: 16px 20px;
      border-top: 1px solid #e0e0e0;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }

    .cancel-btn,
    .save-btn {
      padding: 8px 20px;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
    }

    .cancel-btn {
      background: #f5f5f5;
      color: #666;
    }

    .cancel-btn:hover {
      background: #e0e0e0;
    }

    .save-btn {
      background: #3d2f2a;
      color: white;
    }

    .save-btn:hover:not(:disabled) {
      background: #1557b0;
    }

    .save-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    @media (max-width: 768px) {
      .dialog {
        max-width: 100%;
        max-height: 100%;
        border-radius: 0;
      }

      .lookup-fields {
        grid-template-columns: 1fr;
      }
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (this.initialMetadata) {
      this.populateFromMetadata(this.initialMetadata);
    }
    this.label = this.sessionLabel || '';
  }

  updated(changedProperties: Map<string, any>) {
    if (changedProperties.has('initialMetadata') && this.initialMetadata) {
      this.populateFromMetadata(this.initialMetadata);
    }
    if (changedProperties.has('sessionLabel')) {
      this.label = this.sessionLabel || '';
    }
  }

  private populateFromMetadata(metadata: Metadata) {
    this.paperTitle = metadata.title || '';
    this.paperAuthors = metadata.authors?.join('; ') || '';
    this.paperDoi = metadata.doi || '';
    this.paperPmid = metadata.pmid || '';
    this.paperJournal = metadata.journal || '';
    this.paperPublicationDate = metadata.publication_date || '';
  }

  private async handleLookup() {
    if (!this.paperDoi && !this.paperPmid) {
      this.errorMessage = 'Please enter a DOI or PMID';
      return;
    }

    this.lookingUp = true;
    this.errorMessage = '';

    try {
      const metadata = await api.lookupMetadata({
        doi: this.paperDoi || undefined,
        pmid: this.paperPmid || undefined
      });

      // Populate fields from lookup
      if (metadata.title) this.paperTitle = metadata.title;
      if (metadata.authors) this.paperAuthors = metadata.authors.join('; ');
      if (metadata.doi) this.paperDoi = metadata.doi;
      if (metadata.pmid) this.paperPmid = metadata.pmid;
      if (metadata.journal) this.paperJournal = metadata.journal;
      if (metadata.publication_date) this.paperPublicationDate = metadata.publication_date;

    } catch (err: any) {
      this.errorMessage = err.message || 'Failed to lookup metadata';
    } finally {
      this.lookingUp = false;
    }
  }

  private async handleSave() {
    this.loading = true;
    this.errorMessage = '';

    try {
      const request: MetadataUpdateRequest = {
        title: this.paperTitle || undefined,
        authors: this.paperAuthors ? this.paperAuthors.split(';').map(a => a.trim()).filter(a => a) : undefined,
        doi: this.paperDoi || undefined,
        pmid: this.paperPmid || undefined,
        journal: this.paperJournal || undefined,
        publication_date: this.paperPublicationDate || undefined,
        label: this.label || undefined
      };

      const response = await api.updateMetadata(this.sessionId, request);

      if (response.success) {
        this.dispatchEvent(new CustomEvent('metadata-updated', {
          detail: response.metadata,
          bubbles: true,
          composed: true
        }));
        this.handleClose();
      }
    } catch (err: any) {
      this.errorMessage = err.message || 'Failed to update metadata';
    } finally {
      this.loading = false;
    }
  }

  private handleClose() {
    this.open = false;
    this.dispatchEvent(new CustomEvent('close', {
      bubbles: true,
      composed: true
    }));
  }

  render() {
    if (!this.open) return null;

    return html`
      <div class="overlay" @click=${(e: Event) => e.target === e.currentTarget && this.handleClose()}>
        <div class="dialog">
          <div class="header">
            <h2>Edit Paper Metadata</h2>
            <button class="close-btn" @click=${this.handleClose}>×</button>
          </div>

          <div class="content">
            ${this.errorMessage ? html`<div class="error">${this.errorMessage}</div>` : ''}

            <div class="lookup-section">
              <h3>Auto-fill from DOI or PMID</h3>
              <div class="lookup-fields">
                <div class="field" style="margin: 0;">
                  <label>DOI</label>
                  <input
                    type="text"
                    .value=${this.paperDoi}
                    @input=${(e: Event) => this.paperDoi = (e.target as HTMLInputElement).value}
                    placeholder="10.1234/example"
                  />
                </div>
                <div class="field" style="margin: 0;">
                  <label>PMID</label>
                  <input
                    type="text"
                    .value=${this.paperPmid}
                    @input=${(e: Event) => this.paperPmid = (e.target as HTMLInputElement).value}
                    placeholder="12345678"
                  />
                </div>
                <button
                  class="lookup-btn"
                  @click=${this.handleLookup}
                  ?disabled=${this.lookingUp || (!this.paperDoi && !this.paperPmid)}
                >
                  ${this.lookingUp ? 'Looking up...' : 'Look up'}
                </button>
              </div>
            </div>

            <div class="field">
              <label>Session Label (Optional)</label>
              <input
                type="text"
                .value=${this.label}
                @input=${(e: Event) => this.label = (e.target as HTMLInputElement).value}
                placeholder="e.g. First read, Deep dive, etc."
              />
              <div class="field-hint">Optional label to distinguish multiple sessions for the same paper</div>
            </div>

            <div class="field">
              <label>Title</label>
              <input
                type="text"
                .value=${this.paperTitle}
                @input=${(e: Event) => this.paperTitle = (e.target as HTMLInputElement).value}
                placeholder="Paper title"
              />
            </div>

            <div class="field">
              <label>Authors</label>
              <input
                type="text"
                .value=${this.paperAuthors}
                @input=${(e: Event) => this.paperAuthors = (e.target as HTMLInputElement).value}
                placeholder="Last, First; Last, First"
              />
              <div class="field-hint">Separate multiple authors with semicolons</div>
            </div>

            <div class="field">
              <label>Journal</label>
              <input
                type="text"
                .value=${this.paperJournal}
                @input=${(e: Event) => this.paperJournal = (e.target as HTMLInputElement).value}
                placeholder="Journal name"
              />
            </div>

            <div class="field">
              <label>Publication Date</label>
              <input
                type="text"
                .value=${this.paperPublicationDate}
                @input=${(e: Event) => this.paperPublicationDate = (e.target as HTMLInputElement).value}
                placeholder="YYYY-MM-DD"
              />
            </div>

          </div>

          <div class="footer">
            <button class="cancel-btn" @click=${this.handleClose}>Cancel</button>
            <button
              class="save-btn"
              @click=${this.handleSave}
              ?disabled=${this.loading}
            >
              ${this.loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'metadata-edit-dialog': MetadataEditDialog;
  }
}
