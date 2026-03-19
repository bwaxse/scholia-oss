import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api } from '../../services/api';
import type { ConversationMessage } from '../../types/session';
import type { Metadata } from '../../types/metadata';
import './ask-tab';
import './concepts-tab';
import '../metadata-edit-dialog';

export type TabType = 'concepts' | 'ask';

@customElement('left-panel')
export class LeftPanel extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) filename = '';
  @property({ type: String }) paperTitle?: string;  // Paper title from metadata
  @property({ type: String }) paperAuthors?: string;  // Authors from metadata (JSON string)
  @property({ type: String }) paperYear?: string;  // Publication year from metadata
  @property({ type: String }) paperPublicationDate?: string;  // Full publication date from metadata
  @property({ type: String }) paperJournal?: string;  // Journal name from metadata
  @property({ type: String }) paperJournalAbbr?: string;  // Journal abbreviation from Zotero
  @property({ type: String }) zoteroKey?: string;  // Zotero key if session was loaded from Zotero
  @property({ type: String }) sessionLabel?: string;  // Session label for distinguishing multiple sessions
  @property({ type: Array }) conversation: ConversationMessage[] = [];
  @property({ type: Array }) flags: number[] = [];
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;
  @property({ type: Boolean }) geminiAvailable = false;

  @state() private activeTab: TabType = 'ask';
  @state() private showMetadataDialog = false;
  @state() private currentMetadata?: Metadata;
  @state() private deletingSession = false;
  @state() private showUserMenu = false;
  @state() private modelAccess = { haiku: true, flash: true, sonnet: true, gemini_pro: true };

  private boundClickOutside = this.handleClickOutside.bind(this);

  connectedCallback() {
    super.connectedCallback();
    document.addEventListener('click', this.boundClickOutside);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener('click', this.boundClickOutside);
  }

  private handleClickOutside(e: MouseEvent) {
    if (!this.showUserMenu) return;

    const userMenuContainer = this.shadowRoot?.querySelector('.user-menu-container');
    if (!userMenuContainer) return;

    // Check if click was inside the user menu container using composedPath
    // This handles Shadow DOM boundaries correctly
    const path = e.composedPath();
    if (!path.includes(userMenuContainer)) {
      this.showUserMenu = false;
    }
  }

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f9f3ef;
    }

    .panel-header {
      padding: 16px;
      background: white;
      border-bottom: 1px solid #e8dfd9;
      flex-shrink: 0;
    }

    .header-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-title-link {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: #3d2f2a;
    }

    .header-logo {
      height: 20px;
      width: auto;
      display: block;
    }

    .header-title-link h1 {
      font-size: 24px;
      font-weight: 400;
      margin: 0;
      color: #3d2f2a;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: auto;
    }

    .user-menu-container {
      position: relative;
    }

    .user-avatar-btn {
      padding: 4px;
      background: transparent;
      border: none;
      cursor: pointer;
      color: #999;
      transition: color 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .user-avatar-btn:hover {
      color: #666;
    }

    .user-avatar-btn svg {
      width: 18px;
      height: 18px;
    }

    .user-menu-dropdown {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      background: white;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      min-width: 200px;
      z-index: 1000;
      overflow: hidden;
    }

    .menu-item {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 12px 16px;
      background: white;
      border: none;
      text-align: left;
      font-size: 14px;
      color: #3d2f2a;
      cursor: pointer;
      transition: background 0.15s;
      text-decoration: none;
      font-family: inherit;
    }

    .menu-item:hover {
      background: #f9f3ef;
    }

    .menu-item svg {
      flex-shrink: 0;
    }

    .sign-out-btn {
      border-top: 1px solid #e8dfd9;
    }

    .home-button {
      padding: 4px;
      background: transparent;
      border: none;
      cursor: pointer;
      color: #999;
      transition: color 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .home-button svg {
      width: 18px;
      height: 18px;
    }

    .home-button:hover {
      color: #666;
    }

    .delete-session-btn {
      padding: 4px;
      background: transparent;
      border: none;
      cursor: pointer;
      color: #999;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .delete-session-btn svg {
      width: 14px;
      height: 14px;
    }

    .delete-session-btn:hover {
      color: #c45d3a;
      background: #fce9e2;
    }

    .delete-session-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .edit-metadata-btn {
      padding: 4px;
      background: transparent;
      border: none;
      cursor: pointer;
      color: #999;
      transition: color 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .edit-metadata-btn:hover {
      color: #666;
    }

    .edit-metadata-btn svg {
      width: 14px;
      height: 14px;
    }

    .paper-metadata {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #f0e8e3;
    }

    .paper-title-row {
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }

    .paper-title-row .paper-title {
      flex: 1;
    }

    .session-actions {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }

    .panel-header h1 {
      margin: 0 0 2px 0;
      font-size: 18px;
      color: #3d2f2a;
    }

    .panel-header .tagline {
      margin: 0;
      font-size: 11px;
      color: #999;
      font-style: italic;
      font-weight: 300;
    }

    .panel-header .paper-title {
      margin: 0 0 4px 0;
      font-size: 13px;
      font-weight: 500;
      color: #333;
      line-height: 1.3;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      word-break: break-word;
    }

    .panel-header .paper-authors {
      margin: 0;
      font-size: 11px;
      color: #666;
    }

    .panel-header .filename {
      margin: 0;
      font-size: 13px;
      color: #666;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .tabs {
      display: flex;
      background: white;
      border-bottom: 1px solid #e8dfd9;
      flex-shrink: 0;
    }

    .tab-button {
      flex: 1;
      padding: 12px 16px;
      border: none;
      background: transparent;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      color: #666;
      transition: all 0.2s;
      position: relative;
    }

    .tab-button:hover {
      background: #f5f5f5;
      color: #333;
    }

    .tab-button.active {
      color: #3d2f2a;
    }

    .tab-button.active::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: #3d2f2a;
    }

    .tab-content {
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }

    .tab-content > * {
      height: 100%;
    }

    /* Hide inactive tabs */
    .tab-content > :not(.active) {
      display: none;
    }

    /* Mobile styles */
    @media (max-width: 768px) {
      /* Hide header on mobile - it's replaced by bottom nav */
      .panel-header {
        display: none;
      }

      /* Hide tabs on mobile - they're in the bottom nav */
      .tabs {
        display: none;
      }

      /* Make tab content take full height */
      .tab-content {
        flex: 1;
        overflow: hidden;
        display: flex;
        flex-direction: column;
      }

      .tab-content > * {
        flex: 1;
        overflow-y: auto;
      }
    }
  `;

  private handleTabClick(tab: TabType) {
    this.activeTab = tab;
    this.dispatchEvent(
      new CustomEvent('tab-change', {
        detail: { tab },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleHomeClick() {
    // Switch to Ask tab to show Recent Papers
    this.activeTab = 'ask';

    this.dispatchEvent(
      new CustomEvent('home-click', {
        bubbles: true,
        composed: true
      })
    );
  }

  private async handleDeleteSession() {
    if (!this.sessionId) return;

    const title = this.paperTitle || this.filename;
    if (!confirm(`Delete session for "${title}"? This cannot be undone.`)) {
      return;
    }

    this.deletingSession = true;

    try {
      await api.deleteSession(this.sessionId);
      // Navigate home after successful deletion
      this.handleHomeClick();
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Failed to delete session');
      this.deletingSession = false;
    }
  }

  private toggleUserMenu() {
    this.showUserMenu = !this.showUserMenu;
  }

  private async handleSignOut() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.href = '/';
    } catch (err) {
      console.error('Failed to sign out:', err);
      alert('Failed to sign out. Please try again.');
    }
  }

  private handleEditMetadata() {
    // Populate current metadata from properties
    this.currentMetadata = {
      title: this.paperTitle,
      authors: this.paperAuthors ? JSON.parse(this.paperAuthors) : undefined,
      year: this.paperYear,
      publication_date: this.paperPublicationDate,
      journal: this.paperJournal,
      journal_abbr: this.paperJournalAbbr
    };
    this.showMetadataDialog = true;
  }

  private handleMetadataUpdated(e: CustomEvent) {
    const metadata = e.detail as Metadata;

    // Update local properties
    if (metadata.title) this.paperTitle = metadata.title;
    if (metadata.authors) this.paperAuthors = JSON.stringify(metadata.authors);
    if (metadata.publication_date) this.paperPublicationDate = metadata.publication_date;
    // Extract year from publication_date if year not provided
    if (metadata.year) {
      this.paperYear = metadata.year;
    } else if (metadata.publication_date) {
      const yearMatch = metadata.publication_date.match(/\d{4}/);
      if (yearMatch) this.paperYear = yearMatch[0];
    }
    if (metadata.journal) this.paperJournal = metadata.journal;
    if (metadata.journal_abbr) this.paperJournalAbbr = metadata.journal_abbr;

    // Close dialog
    this.showMetadataDialog = false;

    // Dispatch event to parent
    this.dispatchEvent(
      new CustomEvent('metadata-updated', {
        detail: metadata,
        bubbles: true,
        composed: true
      })
    );
  }

  /**
   * Format authors, journal, and year for display.
   * Handles both JSON array format and semicolon-separated format.
   * Format: "authors. journal abbrev. year" with journal italicized
   * Example: '["Smith, John", "Doe, Jane"]' + "Nature" + "2023" -> "Smith & Doe. Nature. 2023"
   */
  private formatAuthorsWithYear(authors: string, year?: string): ReturnType<typeof html> {
    if (!authors) return html``;

    let authorList: string[] = [];

    // Try to parse as JSON array first
    try {
      const parsed = JSON.parse(authors);
      if (Array.isArray(parsed)) {
        authorList = parsed;
      }
    } catch {
      // If not JSON, split by semicolon or newline
      authorList = authors.split(/[;\n]/).map(a => a.trim()).filter(a => a);
    }

    if (authorList.length === 0) return html``;

    // Extract last names
    const lastNames = authorList.map(a => a.split(',')[0].trim());

    let authorText = '';
    if (lastNames.length === 1) {
      // Just first author
      authorText = lastNames[0];
    } else if (lastNames.length === 2) {
      // First & Last
      authorText = `${lastNames[0]} & ${lastNames[1]}`;
    } else if (lastNames.length <= 6) {
      // 3-6 authors: show all separated by commas
      authorText = lastNames.join(', ');
    } else {
      // 7+ authors: show first 3...last 3
      const firstThree = lastNames.slice(0, 3).join(', ');
      const lastThree = lastNames.slice(-3).join(', ');
      authorText = `${firstThree}...${lastThree}`;
    }

    // Get journal (prefer abbreviation from Zotero, fall back to manual abbreviation)
    const journal = this.paperJournalAbbr || this.abbreviateJournal(this.paperJournal);

    // Build formatted output with periods and italicized journal
    if (journal && year) {
      return html`${authorText}. <i>${journal}</i>. ${year}`;
    } else if (journal) {
      return html`${authorText}. <i>${journal}</i>`;
    } else if (year) {
      return html`${authorText}. ${year}`;
    }
    return html`${authorText}`;
  }

  /**
   * Abbreviate journal name for display.
   * Examples: "Nature Communications" -> "Nat Commun", "Cell" -> "Cell"
   */
  private abbreviateJournal(journal?: string): string {
    if (!journal) return '';

    // Common journal abbreviations
    const abbreviations: Record<string, string> = {
      'Nature Communications': 'Nat Commun',
      'Nature Genetics': 'Nat Genet',
      'Nature Methods': 'Nat Methods',
      'Nature Biotechnology': 'Nat Biotechnol',
      'Proceedings of the National Academy of Sciences': 'PNAS',
      'Journal of the American Medical Association': 'JAMA',
      'New England Journal of Medicine': 'NEJM',
      'American Journal of Human Genetics': 'AJHG',
      'Public Library of Science': 'PLOS',
      'PLOS Genetics': 'PLOS Genet',
      'PLOS Computational Biology': 'PLOS Comput Biol',
    };

    // Check for exact match
    if (abbreviations[journal]) {
      return abbreviations[journal];
    }

    // For unknown journals, truncate if too long (>20 chars)
    if (journal.length > 20) {
      // Take first 3 words
      const words = journal.split(' ');
      if (words.length > 3) {
        return words.slice(0, 3).join(' ') + '.';
      }
    }

    return journal;
  }

  render() {
    return html`
      <div class="panel-header">
        <div class="header-row">
          <a href="/" class="header-title-link">
            <img src="/logo_small.png?v=2" alt="Scholia" class="header-logo" />
            <h1>Scholia</h1>
          </a>
          <div class="header-actions">
            ${this.sessionId
              ? html`
                  <button class="home-button" @click=${this.handleHomeClick} title="Home">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                      <polyline points="9 22 9 12 15 12 15 22"></polyline>
                    </svg>
                  </button>
                `
              : ''}
            <div class="user-menu-container">
              <button class="user-avatar-btn" @click=${this.toggleUserMenu} title="Account">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </button>
              ${this.showUserMenu ? html`
                <div class="user-menu-dropdown">
                  <a href="/settings?returnTo=${encodeURIComponent(window.location.pathname)}" class="menu-item">
                    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
                      <circle cx="12" cy="12" r="3"></circle>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                    Scholia Settings
                  </a>
                  <button class="menu-item sign-out-btn" @click=${this.handleSignOut}>
                    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                      <polyline points="16 17 21 12 16 7"></polyline>
                      <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                    Sign Out
                  </button>
                </div>
              ` : ''}
            </div>
          </div>
        </div>
        ${this.paperTitle || this.filename
          ? html`
              <div class="paper-metadata">
                ${this.paperTitle
                  ? html`
                      <div class="paper-title-row">
                        <p class="paper-title" title="${this.paperTitle}">${this.paperTitle}</p>
                        <div class="session-actions">
                          <button class="edit-metadata-btn" @click=${this.handleEditMetadata} title="Edit Metadata">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                          </button>
                          <button class="delete-session-btn" @click=${this.handleDeleteSession} ?disabled=${this.deletingSession} title="Delete session">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                          </button>
                        </div>
                      </div>
                      ${this.paperAuthors
                        ? html`<p class="paper-authors">${this.formatAuthorsWithYear(this.paperAuthors, this.paperYear)}</p>`
                        : ''}
                    `
                  : html`
                      <div class="paper-title-row">
                        <p class="filename" title="${this.filename}">${this.filename}</p>
                        <div class="session-actions">
                          <button class="edit-metadata-btn" @click=${this.handleEditMetadata} title="Edit Metadata">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                          </button>
                          <button class="delete-session-btn" @click=${this.handleDeleteSession} ?disabled=${this.deletingSession} title="Delete session">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                          </button>
                        </div>
                      </div>
                    `
                }
              </div>
            `
          : ''}
      </div>

      ${this.sessionId
        ? html`
            <div class="tabs">
              <button
                class="tab-button ${this.activeTab === 'ask' ? 'active' : ''}"
                @click=${() => this.handleTabClick('ask')}
              >
                Discuss
              </button>
              <button
                class="tab-button ${this.activeTab === 'concepts' ? 'active' : ''}"
                @click=${() => this.handleTabClick('concepts')}
              >
                Insights
              </button>
            </div>
          `
        : ''}

      <div class="tab-content" @edit-metadata=${this.handleEditMetadata} @home-click=${() => this.dispatchEvent(new CustomEvent('home-click', { bubbles: true, composed: true }))}>
        <concepts-tab
          class="${this.activeTab === 'concepts' ? 'active' : ''}"
          .sessionId=${this.sessionId}
          .zoteroKey=${this.zoteroKey}
          .paperTitle=${this.paperTitle}
          .paperAuthors=${this.paperAuthors}
          .paperYear=${this.paperYear}
          .paperJournal=${this.paperJournal}
          .paperJournalAbbr=${this.paperJournalAbbr}
          .filename=${this.filename}
          .geminiAvailable=${this.geminiAvailable}
          .modelAccess=${this.modelAccess}
        ></concepts-tab>

        <ask-tab
          class="${this.activeTab === 'ask' ? 'active' : ''}"
          .sessionId=${this.sessionId}
          .zoteroKey=${this.zoteroKey}
          .paperTitle=${this.paperTitle}
          .paperAuthors=${this.paperAuthors}
          .paperYear=${this.paperYear}
          .paperJournal=${this.paperJournal}
          .paperJournalAbbr=${this.paperJournalAbbr}
          .filename=${this.filename}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          .geminiAvailable=${this.geminiAvailable}
          .modelAccess=${this.modelAccess}
          @conversation-updated=${(e: CustomEvent) => {
            this.dispatchEvent(
              new CustomEvent('conversation-updated', {
                detail: e.detail,
                bubbles: true,
                composed: true
              })
            );
          }}
          @flags-updated=${(e: CustomEvent) =>
            this.dispatchEvent(
              new CustomEvent('flags-updated', {
                detail: e.detail,
                bubbles: true,
                composed: true
              })
            )}
          @clear-selection=${() =>
            this.dispatchEvent(
              new CustomEvent('clear-selection', {
                bubbles: true,
                composed: true
              })
            )}
        ></ask-tab>
      </div>

      <metadata-edit-dialog
        .sessionId=${this.sessionId}
        .initialMetadata=${this.currentMetadata}
        .sessionLabel=${this.sessionLabel || ''}
        .open=${this.showMetadataDialog}
        @metadata-updated=${this.handleMetadataUpdated}
        @close=${() => (this.showMetadataDialog = false)}
      ></metadata-edit-dialog>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'left-panel': LeftPanel;
  }
}
