import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { ZoteroItem, DuplicateCheckResponse } from '../../types/session';
import '../shared/loading-spinner';

@customElement('zotero-picker')
export class ZoteroPicker extends LitElement {
  @property({ type: Boolean }) visible = false;
  @property({ type: Array }) preFilteredItems?: ZoteroItem[]; // Pass pre-filtered items (e.g., attachments)
  @property({ type: String }) mode: 'full' | 'supplements' = 'full'; // Mode: 'full' for all papers, 'supplements' for attachments only

  @state() private items: ZoteroItem[] = [];
  @state() private loading = true;
  @state() private error = '';
  @state() private notConfigured = false;
  @state() private searchQuery = '';
  @state() private activeTab: 'recent' | 'search' = 'recent';
  @state() private searching = false;
  @state() private selectingKey?: string;

  // Duplicate session warning state
  @state() private showDuplicateDialog = false;
  @state() private duplicateInfo?: DuplicateCheckResponse;
  @state() private pendingPaper?: ZoteroItem;
  @state() private newSessionLabel = '';
  @state() private checkingDuplicates = false;

  static styles = css`
    :host {
      display: block;
    }

    .zotero-picker {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .picker-content {
      background: white;
      border-radius: 12px;
      width: 90%;
      max-width: 650px;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .picker-header {
      padding: 20px 24px;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .picker-header h2 {
      margin: 0;
      font-size: 20px;
      color: #333;
    }

    .credit-note {
      margin: 4px 0 16px 0;
      font-size: 12px;
      color: #999;
    }

    .tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 16px;
    }

    .tab {
      padding: 8px 16px;
      border: none;
      background: transparent;
      font-size: 14px;
      font-weight: 500;
      color: #666;
      cursor: pointer;
      border-radius: 6px;
      transition: all 0.15s;
    }

    .tab:hover {
      background: #f0f0f0;
    }

    .tab.active {
      background: #e8f0fe;
      color: #3d2f2a;
    }

    .search-container {
      display: flex;
      gap: 8px;
    }

    .search-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      outline: none;
      box-sizing: border-box;
    }

    .search-input:focus {
      border-color: #3d2f2a;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
    }

    .search-btn {
      padding: 10px 16px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .search-btn:hover {
      background: #1557b0;
    }

    .search-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .picker-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .paper-item {
      padding: 14px 16px;
      margin-bottom: 8px;
      background: #f8f9fa;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .paper-item:hover {
      background: #e8f0fe;
      border-color: #3d2f2a;
    }

    .paper-item.selecting {
      opacity: 0.7;
      cursor: wait;
    }

    .paper-item.no-pdf {
      opacity: 0.6;
      cursor: not-allowed;
      background: #f5f5f5;
    }

    .paper-item.no-pdf:hover {
      background: #f5f5f5;
      border-color: #e0e0e0;
    }

    .paper-item:last-child {
      margin-bottom: 0;
    }

    .paper-title {
      font-weight: 500;
      font-size: 14px;
      color: #333;
      margin-bottom: 6px;
      line-height: 1.4;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .pdf-indicator {
      font-size: 16px;
      flex-shrink: 0;
    }

    .no-pdf-label {
      font-size: 11px;
      color: #dc2626;
      background: #fef2f2;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 500;
    }

    .paper-authors {
      font-size: 13px;
      color: #555;
      margin-bottom: 4px;
    }

    .paper-meta {
      font-size: 12px;
      color: #666;
      display: flex;
      gap: 12px;
    }

    .paper-meta span {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .picker-footer {
      padding: 16px 24px;
      border-top: 1px solid #e0e0e0;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      flex-shrink: 0;
    }

    .btn {
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
    }

    .btn-secondary {
      background: white;
      border: 1px solid #ddd;
      color: #333;
    }

    .btn-secondary:hover {
      background: #f5f5f5;
    }

    .empty-state {
      text-align: center;
      padding: 40px 20px;
      color: #666;
    }

    .empty-state h3 {
      margin: 0 0 8px 0;
      font-size: 16px;
      color: #333;
    }

    .empty-state p {
      margin: 0;
      font-size: 14px;
    }

    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px;
    }

    .error-message {
      padding: 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #dc2626;
      font-size: 13px;
      margin-bottom: 16px;
    }

    .not-configured {
      text-align: center;
      padding: 40px 20px;
    }

    .not-configured h3 {
      margin: 0 0 12px 0;
      font-size: 18px;
      color: #333;
    }

    .not-configured p {
      margin: 0 0 20px 0;
      font-size: 14px;
      color: #666;
      line-height: 1.5;
    }

    .configure-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 12px 24px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: background 0.15s;
    }

    .configure-btn:hover {
      background: #1557b0;
    }

    .no-results {
      text-align: center;
      padding: 24px;
      color: #666;
      font-size: 14px;
    }

    .search-hint {
      text-align: center;
      padding: 40px 20px;
      color: #666;
      font-size: 14px;
    }

    /* Duplicate warning dialog */
    .duplicate-dialog-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1100;
    }

    .duplicate-dialog {
      background: white;
      border-radius: 12px;
      width: 90%;
      max-width: 480px;
      padding: 24px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .duplicate-dialog h3 {
      margin: 0 0 8px 0;
      font-size: 18px;
      color: #3d2f2a;
    }

    .duplicate-dialog .paper-name {
      font-size: 14px;
      color: #666;
      margin-bottom: 16px;
      font-style: italic;
    }

    .duplicate-dialog .existing-sessions {
      background: #f9f3ef;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .duplicate-dialog .existing-sessions h4 {
      margin: 0 0 8px 0;
      font-size: 13px;
      font-weight: 600;
      color: #6b574f;
    }

    .duplicate-dialog .session-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
      color: #3d2f2a;
      padding: 8px 0;
      border-bottom: 1px solid #e8dfd9;
      gap: 12px;
    }

    .duplicate-dialog .session-item:last-child {
      border-bottom: none;
    }

    .duplicate-dialog .session-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .duplicate-dialog .session-label {
      font-weight: 500;
    }

    .duplicate-dialog .session-meta {
      color: #a08a80;
      font-size: 12px;
    }

    .duplicate-dialog .session-open-btn {
      padding: 6px 12px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
      flex-shrink: 0;
    }

    .duplicate-dialog .session-open-btn:hover {
      background: #2d211c;
    }

    .duplicate-dialog .label-input-section {
      margin-bottom: 20px;
    }

    .duplicate-dialog .label-input-section label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #3d2f2a;
      margin-bottom: 6px;
    }

    .duplicate-dialog .label-input-section input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      font-size: 14px;
      font-family: inherit;
      box-sizing: border-box;
      background: #fdfaf8;
    }

    .duplicate-dialog .label-input-section input:focus {
      outline: none;
      border-color: #c45d3a;
    }

    .duplicate-dialog .label-input-section .hint {
      font-size: 12px;
      color: #a08a80;
      margin-top: 4px;
    }

    .duplicate-dialog .actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .duplicate-dialog .btn {
      padding: 12px 16px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      transition: all 0.15s;
      text-align: center;
    }

    .duplicate-dialog .btn-primary {
      background: #3d2f2a;
      color: white;
    }

    .duplicate-dialog .btn-primary:hover {
      background: #2d211c;
    }

    .duplicate-dialog .btn-secondary {
      background: #f9f3ef;
      color: #3d2f2a;
      border: 1px solid #e8dfd9;
    }

    .duplicate-dialog .btn-secondary:hover {
      background: #e8dfd9;
    }

    .duplicate-dialog .btn-text {
      background: transparent;
      color: #6b574f;
    }

    .duplicate-dialog .btn-text:hover {
      color: #3d2f2a;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
  }

  updated(changedProperties: Map<string, unknown>) {
    // If pre-filtered items provided, use those instead of loading
    if (changedProperties.has('preFilteredItems') && this.preFilteredItems) {
      this.items = this.preFilteredItems;
      this.loading = false;
      return;
    }

    // Load recent papers when the picker becomes visible (only in 'full' mode)
    if (changedProperties.has('visible') && this.visible && this.mode === 'full') {
      this.loadRecentPapers();
    }
  }

  private async loadRecentPapers() {
    this.loading = true;
    this.error = '';
    this.notConfigured = false;
    this.activeTab = 'recent';

    try {
      this.items = await api.getRecentPapers(20);
    } catch (err) {
      console.error('Failed to load recent papers:', err);
      if (err instanceof ApiError) {
        // Check if it's a "not configured" error
        if (err.status === 400 && err.message.toLowerCase().includes('not configured')) {
          this.notConfigured = true;
        } else {
          this.error = err.message;
        }
      } else {
        this.error = 'Failed to load recent papers from Zotero';
      }
    } finally {
      this.loading = false;
    }
  }

  private async handleSearch() {
    if (!this.searchQuery.trim()) return;

    this.searching = true;
    this.error = '';
    this.activeTab = 'search';

    try {
      this.items = await api.searchZotero(this.searchQuery.trim(), 20);
    } catch (err) {
      console.error('Failed to search Zotero:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to search Zotero';
      }
    } finally {
      this.searching = false;
    }
  }

  private handleSearchInput(e: Event) {
    const input = e.target as HTMLInputElement;
    this.searchQuery = input.value;
  }

  private handleSearchKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      this.handleSearch();
    }
  }

  private handleTabClick(tab: 'recent' | 'search') {
    this.activeTab = tab;
    if (tab === 'recent') {
      this.loadRecentPapers();
    }
  }

  private async handlePaperClick(paper: ZoteroItem) {
    if (this.selectingKey || this.checkingDuplicates) return;

    // In supplements mode, skip duplicate check
    if (this.mode === 'supplements') {
      this.dispatchPaperSelected(paper);
      return;
    }

    // Check for existing sessions
    this.checkingDuplicates = true;
    this.selectingKey = paper.key;

    try {
      const duplicateCheck = await api.checkZoteroSessions(paper.key);

      if (duplicateCheck.exists && duplicateCheck.count > 0) {
        // Show duplicate warning dialog
        this.duplicateInfo = duplicateCheck;
        this.pendingPaper = paper;
        this.showDuplicateDialog = true;
        this.newSessionLabel = '';
      } else {
        // No duplicates, proceed with selection
        this.dispatchPaperSelected(paper);
      }
    } catch (err) {
      console.error('Failed to check for duplicates:', err);
      // On error, just proceed with the selection
      this.dispatchPaperSelected(paper);
    } finally {
      this.checkingDuplicates = false;
      this.selectingKey = undefined;
    }
  }

  private dispatchPaperSelected(paper: ZoteroItem, label?: string) {
    this.dispatchEvent(
      new CustomEvent('zotero-paper-selected', {
        detail: { paper, label },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleOpenSession(sessionId: string) {
    this.showDuplicateDialog = false;
    this.duplicateInfo = undefined;
    this.pendingPaper = undefined;

    // Dispatch session-selected event to navigate to the existing session
    this.dispatchEvent(
      new CustomEvent('session-selected', {
        detail: { session: { session_id: sessionId } },
        bubbles: true,
        composed: true
      })
    );
    this.handleClose();
  }

  private handleCreateNewSession() {
    if (!this.pendingPaper) return;

    const label = this.newSessionLabel.trim() || undefined;
    this.dispatchPaperSelected(this.pendingPaper, label);

    this.showDuplicateDialog = false;
    this.duplicateInfo = undefined;
    this.pendingPaper = undefined;
    this.newSessionLabel = '';
  }

  private handleCancelDuplicateDialog() {
    this.showDuplicateDialog = false;
    this.duplicateInfo = undefined;
    this.pendingPaper = undefined;
    this.newSessionLabel = '';
  }

  private formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  private handleClose() {
    this.dispatchEvent(
      new CustomEvent('close', {
        bubbles: true,
        composed: true
      })
    );
  }

  private renderPaperItem(paper: ZoteroItem) {
    const isSelecting = this.selectingKey === paper.key;

    return html`
      <div
        class="paper-item ${isSelecting ? 'selecting' : ''}"
        @click=${() => this.handlePaperClick(paper)}
      >
        <div class="paper-title">
          <span class="pdf-indicator">📄</span>
          <span>${paper.title}</span>
        </div>
        ${paper.authors ? html`<div class="paper-authors">${paper.authors}</div>` : ''}
        <div class="paper-meta">
          ${paper.year ? html`<span>${paper.year}</span>` : ''}
          ${paper.publication ? html`<span>${paper.publication}</span>` : ''}
          ${paper.item_type ? html`<span>${this.formatItemType(paper.item_type)}</span>` : ''}
        </div>
        ${isSelecting ? html`<div style="font-size: 12px; color: #3d2f2a; margin-top: 8px;">Loading paper...</div>` : ''}
      </div>
    `;
  }

  private formatItemType(itemType: string): string {
    const typeMap: Record<string, string> = {
      journalArticle: 'Journal Article',
      conferencePaper: 'Conference Paper',
      book: 'Book',
      bookSection: 'Book Chapter',
      thesis: 'Thesis',
      report: 'Report',
      preprint: 'Preprint'
    };
    return typeMap[itemType] || itemType;
  }

  /**
   * Filter items to only show valid papers (not notes, attachments, or untitled items)
   */
  private getFilteredItems(): ZoteroItem[] {
    const skipTypes = ['note', 'annotation', 'attachment'];
    return this.items.filter(paper => {
      // Skip items without proper titles
      if (!paper.title || paper.title.toLowerCase() === 'untitled') {
        return false;
      }
      // Skip non-paper item types
      if (paper.item_type && skipTypes.includes(paper.item_type.toLowerCase())) {
        return false;
      }
      return true;
    });
  }

  render() {
    if (!this.visible) {
      return null;
    }

    return html`
      <div class="zotero-picker" @click=${(e: Event) => {
        if (e.target === e.currentTarget) this.handleClose();
      }}>
        <div class="picker-content">
          <div class="picker-header">
            <h2>${this.mode === 'supplements' ? 'Select Supplement' : 'Load from Zotero'}</h2>
            ${this.mode !== 'supplements' ? html`<p class="credit-note">Uses 20 credits</p>` : ''}

            ${this.mode === 'full' ? html`
              <div class="tabs">
                <button
                  class="tab ${this.activeTab === 'recent' ? 'active' : ''}"
                  @click=${() => this.handleTabClick('recent')}
                >
                  Recent
                </button>
                <button
                  class="tab ${this.activeTab === 'search' ? 'active' : ''}"
                  @click=${() => this.handleTabClick('search')}
                >
                  Search
                </button>
              </div>

              <div class="search-container">
                <input
                  type="text"
                  class="search-input"
                  placeholder="Search by title, author, or DOI..."
                  .value=${this.searchQuery}
                  @input=${this.handleSearchInput}
                  @keydown=${this.handleSearchKeydown}
                />
                <button
                  class="search-btn"
                  @click=${this.handleSearch}
                  ?disabled=${this.searching || !this.searchQuery.trim()}
                >
                  ${this.searching ? 'Searching...' : 'Search'}
                </button>
              </div>
            ` : ''}
          </div>

          <div class="picker-body">
            ${this.error
              ? html`<div class="error-message">${this.error}</div>`
              : ''}

            ${this.notConfigured
              ? html`
                  <div class="not-configured">
                    <h3>Connect Your Zotero Library</h3>
                    <p>
                      To load papers from Zotero, you need to add your Zotero API credentials in Settings.
                    </p>
                    <a href="/settings" class="configure-btn" @click=${this.handleClose}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                      </svg>
                      Go to Settings
                    </a>
                  </div>
                `
              : this.loading || this.searching
              ? html`
                  <div class="loading-container">
                    <loading-spinner message="${this.loading ? 'Loading recent papers...' : 'Searching...'}"></loading-spinner>
                  </div>
                `
              : this.activeTab === 'search' && !this.searchQuery.trim()
              ? html`
                  <div class="search-hint">
                    Enter a search term to find papers in your Zotero library
                  </div>
                `
              : (() => {
                  const filteredItems = this.getFilteredItems();
                  return filteredItems.length === 0
                    ? html`
                        <div class="empty-state">
                          <h3>
                            ${this.mode === 'supplements'
                              ? 'No Supplemental PDFs Found'
                              : this.activeTab === 'recent'
                              ? 'No papers in Zotero'
                              : 'No results found'}
                          </h3>
                          <p>
                            ${this.mode === 'supplements'
                              ? 'This paper has no additional PDF attachments in Zotero.'
                              : this.activeTab === 'recent'
                              ? 'Add papers to your Zotero library to see them here.'
                              : 'Try a different search term.'}
                          </p>
                        </div>
                      `
                    : filteredItems.map((paper) => this.renderPaperItem(paper));
                })()}
          </div>

          <div class="picker-footer">
            <button class="btn btn-secondary" @click=${this.handleClose}>
              Cancel
            </button>
          </div>
        </div>
      </div>

      ${this.showDuplicateDialog ? html`
        <div class="duplicate-dialog-overlay" @click=${this.handleCancelDuplicateDialog}>
          <div class="duplicate-dialog" @click=${(e: Event) => e.stopPropagation()}>
            <h3>Existing Sessions Found</h3>
            <p class="paper-name">${this.duplicateInfo?.paper_title || this.pendingPaper?.title}</p>

            <div class="existing-sessions">
              <h4>You have ${this.duplicateInfo?.count} existing session${this.duplicateInfo?.count !== 1 ? 's' : ''} for this paper:</h4>
              ${this.duplicateInfo?.sessions.map(session => html`
                <div class="session-item">
                  <div class="session-info">
                    ${session.label ? html`<span class="session-label">${session.label}</span>` : ''}
                    <span class="session-meta">
                      ${this.formatDate(session.created_at)} · ${session.exchange_count} exchange${session.exchange_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <button class="session-open-btn" @click=${() => this.handleOpenSession(session.session_id)}>
                    Open
                  </button>
                </div>
              `)}
            </div>

            <div class="label-input-section">
              <label for="session-label">New session label (optional):</label>
              <input
                type="text"
                id="session-label"
                placeholder="e.g., Haiku comparison, Second read..."
                .value=${this.newSessionLabel}
                @input=${(e: InputEvent) => this.newSessionLabel = (e.target as HTMLInputElement).value}
              />
              <span class="hint">Add a label to distinguish this session from existing ones</span>
            </div>

            <div class="actions">
              <button class="btn btn-text" @click=${this.handleCancelDuplicateDialog}>
                Cancel
              </button>
              <button class="btn btn-primary" @click=${this.handleCreateNewSession}>
                Create New Session
              </button>
            </div>
          </div>
        </div>
      ` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'zotero-picker': ZoteroPicker;
  }
}
