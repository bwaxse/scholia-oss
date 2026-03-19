/**
 * App Shell - authenticated application wrapper
 *
 * Handles:
 * - Session routing (/ vs /session/:id)
 * - Navigation between sessions
 * - User menu and logout
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../services/api';
import { sessionStorage } from '../services/session-storage';
import type { ConversationMessage, Session, SessionFull } from '../types/session';
import type { TextSelection } from '../types/pdf';
import type { ZoteroItem } from '../types/session';

// Import existing components
import '../components/pdf-viewer/pdf-viewer';
import '../components/left-panel/left-panel';
import '../components/session-picker/session-list';
import '../components/zotero-picker/zotero-picker';
import '../components/shared/loading-spinner';
import '../components/shared/error-message';

import type { PdfViewer } from '../components/pdf-viewer/pdf-viewer';

@customElement('app-shell')
export class AppShell extends LitElement {
  @property({ type: String }) sessionId = '';

  @state() private filename = '';
  @state() private zoteroKey?: string;
  @state() private sessionLabel?: string;
  @state() private paperTitle?: string;
  @state() private paperAuthors?: string;
  @state() private paperYear?: string;
  @state() private paperPublicationDate?: string;
  @state() private paperJournal?: string;
  @state() private paperJournalAbbr?: string;
  @state() private pdfUrl = '';
  @state() private pdfLoadError = false;
  @state() private conversation: ConversationMessage[] = [];
  @state() private flags: number[] = [];
  @state() private selectedText = '';
  @state() private selectedPage?: number;
  @state() private loading = false;
  @state() private error = '';
  @state() private errorActionHref = '';
  @state() private showSessionPicker = false;
  @state() private showZoteroPicker = false;
  @state() private geminiAvailable = false;
  @state() private mobileView: 'home' | 'paper' | 'discuss' | 'insights' = 'home';
  @state() private showUploadMetadataDialog = false;
  @state() private pendingFile: File | null = null;
  @state() private uploadDoi = '';
  @state() private uploadPmid = '';
  @state() private relinkMode = false;  // True when user wants to relink PDF, not create new session
  @state() private relinkSessionId = '';  // Session ID to relink (preserved from when relink was initiated)

  @query('pdf-viewer') private pdfViewer?: PdfViewer;

  private boundKeydownHandler = this.handleKeydown.bind(this);

  private extractYear(publicationDate?: string): string | undefined {
    if (!publicationDate) return undefined;
    const yearMatch = publicationDate.match(/\d{4}/);
    return yearMatch ? yearMatch[0] : undefined;
  }

  async connectedCallback() {
    super.connectedCallback();
    document.addEventListener('keydown', this.boundKeydownHandler);


    // Check for Gemini availability
    try {
      const appConfig = await api.getAppConfig();
      this.geminiAvailable = appConfig.gemini_available;
    } catch (err) {
      console.warn('Failed to fetch app config:', err);
    }

    // Load session if ID provided
    if (this.sessionId) {
      await this.loadSession(this.sessionId);
    }

    // Restore mobile view preference
    const savedMobileView = sessionStorage.getMobileView();
    if (savedMobileView) {
      this.mobileView = savedMobileView as typeof this.mobileView;
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener('keydown', this.boundKeydownHandler);
  }

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has('sessionId') && this.sessionId) {
      this.loadSession(this.sessionId);
    }

    if (changedProperties.has('mobileView')) {
      this.setAttribute('data-mobile-view', this.mobileView);
      sessionStorage.setMobileView(this.mobileView);
    }
  }

  private handleKeydown(e: KeyboardEvent) {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modifier = isMac ? e.metaKey : e.ctrlKey;

    // Cmd/Ctrl + K - Focus query input
    if (modifier && e.key === 'k') {
      e.preventDefault();
      this.focusQueryInput();
      return;
    }

    // Cmd/Ctrl + Shift + F - Flag last exchange
    if (modifier && e.shiftKey && e.key === 'F') {
      e.preventDefault();
      this.flagLastExchange();
      return;
    }

    // Escape - Close modals or clear text selection
    if (e.key === 'Escape') {
      if (this.showSessionPicker) {
        this.showSessionPicker = false;
      } else if (this.showZoteroPicker) {
        this.showZoteroPicker = false;
      } else if (this.selectedText) {
        this.handleClearSelection();
      }
      return;
    }
  }

  private focusQueryInput() {
    const leftPanel = this.shadowRoot?.querySelector('left-panel');
    if (leftPanel) {
      const askTab = leftPanel.shadowRoot?.querySelector('ask-tab');
      if (askTab) {
        const queryInput = askTab.shadowRoot?.querySelector('query-input');
        if (queryInput) {
          const textarea = queryInput.shadowRoot?.querySelector('textarea');
          if (textarea) {
            textarea.focus();
          }
        }
      }
    }
  }

  private flagLastExchange() {
    if (this.conversation.length >= 2) {
      const lastAssistantIndex = this.conversation.length - 1;
      if (this.conversation[lastAssistantIndex].role === 'assistant') {
        const exchangeId = this.conversation[lastAssistantIndex].id;
        if (!this.flags.includes(exchangeId)) {
          this.flags = [...this.flags, exchangeId];
          api.toggleFlag(this.sessionId, exchangeId).catch(console.error);
        }
      }
    }
  }

  private async loadSession(sessionId: string) {
    this.loading = true;
    this.error = '';
    this.pdfLoadError = false;  // Reset PDF error state for new session

    try {
      const session: SessionFull = await api.getSession(sessionId);

      this.filename = session.filename;
      this.paperTitle = session.title;
      this.paperAuthors = session.authors;
      this.paperYear = this.extractYear(session.publication_date);
      this.paperPublicationDate = session.publication_date;
      this.paperJournal = session.journal;
      this.paperJournalAbbr = session.journal_abbr;
      this.zoteroKey = session.zotero_key;
      this.sessionLabel = session.label;

      // Build conversation with initial analysis at the start
      const existingConversation = session.conversation || [];
      if (session.initial_analysis) {
        this.conversation = [
          { id: 0, exchange_id: 0, role: 'user', content: 'Initial analysis', timestamp: session.created_at },
          { id: 1, exchange_id: 0, role: 'assistant', content: session.initial_analysis, timestamp: session.created_at },
          // Preserve exchange_id from API, use sequential id for display
          ...existingConversation.map((msg, idx) => ({ ...msg, id: idx + 2 }))
        ];
      } else {
        this.conversation = existingConversation;
      }
      this.flags = session.flags || [];

      // Use URL path for PDF
      this.pdfUrl = `/sessions/${sessionId}/pdf`;

      // Save to session storage
      sessionStorage.setLastSessionId(sessionId);

      this.loading = false;
    } catch (err) {
      console.error('Failed to load session:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load session';
      }
      this.loading = false;
    }
  }

  handlePdfLoadError() {
    this.pdfLoadError = true;
  }

  handleReselectPaper() {
    // Set relink mode with current session ID before opening picker
    this.relinkMode = true;
    this.relinkSessionId = this.sessionId;
    this.showZoteroPicker = true;
  }

  async handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file || file.type !== 'application/pdf') {
      this.error = 'Please select a valid PDF file';
      return;
    }

    this.pendingFile = file;
    this.uploadDoi = '';
    this.uploadPmid = '';
    this.showUploadMetadataDialog = true;

    input.value = '';
  }

  async handleUploadWithMetadata() {
    if (!this.pendingFile) return;

    this.loading = true;
    this.error = '';
    this.errorActionHref = '';
    this.showUploadMetadataDialog = false;

    try {
      const session = await api.createSession(
        this.pendingFile,
        this.uploadDoi || undefined,
        this.uploadPmid || undefined
      );

      // Navigate to the new session
      this.navigateToSession(session.session_id);

      this.filename = session.filename;
      this.paperTitle = session.title;
      this.paperAuthors = session.authors;
      this.paperYear = this.extractYear(session.publication_date);
      this.paperPublicationDate = session.publication_date;
      this.paperJournal = session.journal;
      this.paperJournalAbbr = session.journal_abbr;
      this.zoteroKey = undefined;
      this.pdfUrl = URL.createObjectURL(this.pendingFile);

      sessionStorage.setLastSessionId(session.session_id);

      this.conversation = [
        { id: 0, exchange_id: 0, role: 'user', content: 'Initial analysis', timestamp: session.created_at },
        { id: 1, exchange_id: 0, role: 'assistant', content: session.initial_analysis, timestamp: session.created_at }
      ];

      this.loading = false;
      this.pendingFile = null;
    } catch (err) {
      console.error('Upload error:', err);
      this.errorActionHref = '';
      if (err instanceof ApiError && err.status === 402 && err.details?.error === 'insufficient_credits') {
        const needed = err.details.credits_needed ?? '?';
        const have = err.details.current_balance ?? '?';
        this.error = `Insufficient credits: you need ${needed} credits but only have ${have}.`;
        this.errorActionHref = '/settings';
      } else if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to upload PDF. Please try again.';
      }
      this.loading = false;
      this.pendingFile = null;
    }
  }

  handleCancelUpload() {
    this.showUploadMetadataDialog = false;
    this.pendingFile = null;
    this.uploadDoi = '';
    this.uploadPmid = '';
  }

  handleTextSelection(e: CustomEvent<TextSelection>) {
    const { text, page } = e.detail;
    this.selectedText = text;
    this.selectedPage = page;
  }

  handleClearSelection() {
    this.selectedText = '';
    this.selectedPage = undefined;
  }

  handleNavigateToPage(e: CustomEvent<{ page: number }>) {
    if (this.pdfViewer) {
      this.pdfViewer.scrollToPage(e.detail.page);
    }
  }

  private navigateToSession(sessionId: string) {
    window.history.pushState({}, '', `/session/${sessionId}`);
    // Dispatch popstate to trigger route update
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  private navigateHome() {
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  handleHomeClick() {
    // Clear current session and go to app home
    this.sessionId = '';
    this.pdfUrl = '';
    this.conversation = [];
    this.flags = [];
    this.navigateHome();
  }

  async handleSessionSelected(e: CustomEvent<{ session: Session }>) {
    const { session } = e.detail;
    this.showSessionPicker = false;
    this.navigateToSession(session.session_id);
  }

  handleShowZoteroPicker() {
    this.showZoteroPicker = true;
  }

  handleCloseZoteroPicker() {
    this.showZoteroPicker = false;
    this.relinkMode = false;
    this.relinkSessionId = '';
  }

  async handleZoteroPaperSelected(e: CustomEvent<{ paper: ZoteroItem; label?: string }>) {
    const { paper, label } = e.detail;
    this.showZoteroPicker = false;
    this.loading = true;
    this.error = '';

    try {
      // If we're in relink mode (from PDF error state), use relink API
      if (this.relinkMode && this.relinkSessionId) {
        await api.relinkSessionZotero(this.relinkSessionId, paper.key);

        // Update local state
        this.zoteroKey = paper.key;
        this.pdfLoadError = false;
        this.relinkMode = false;

        // Force PDF reload by updating URL with cache buster
        this.pdfUrl = `/sessions/${this.relinkSessionId}/pdf?t=${Date.now()}`;

        this.loading = false;
        this.relinkSessionId = '';
        return;
      }

      // Create new session from Zotero paper (with optional label for duplicates)
      const session = await api.createSessionFromZotero(paper.key, label);
      this.navigateToSession(session.session_id);

      this.filename = session.filename;
      this.paperTitle = session.title;
      this.paperAuthors = session.authors;
      this.paperYear = this.extractYear(session.publication_date);
      this.paperPublicationDate = session.publication_date;
      this.paperJournal = session.journal;
      this.paperJournalAbbr = session.journal_abbr;
      this.zoteroKey = paper.key;

      // Use URL path for PDF
      this.pdfUrl = `/sessions/${session.session_id}/pdf`;

      sessionStorage.setLastSessionId(session.session_id);

      this.conversation = [
        { id: 0, exchange_id: 0, role: 'user', content: 'Initial analysis', timestamp: session.created_at },
        { id: 1, exchange_id: 0, role: 'assistant', content: session.initial_analysis, timestamp: session.created_at }
      ];

      this.loading = false;
    } catch (err) {
      console.error('Zotero load error:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load paper from Zotero';
      }
      this.loading = false;
      this.relinkMode = false;
      this.relinkSessionId = '';
    }
  }

  handleCloseSessionPicker() {
    this.showSessionPicker = false;
  }

  handleUploadNewFromPicker() {
    this.showSessionPicker = false;
  }

  static styles = css`
    :host {
      display: flex;
      height: 100vh;
      height: 100dvh;
      overflow: hidden;
      font-family: 'Lora', Georgia, serif;
    }

    .left-pane {
      width: 400px;
      flex-shrink: 0;
      border-right: 1px solid #e8dfd9;
      display: flex;
      flex-direction: column;
      background: #f9f3ef;
    }

    .center-pane {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      background: #525659;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: #fdfaf8;
      color: #3d2f2a;
      padding: 40px;
      text-align: center;
      overflow: hidden;
      box-sizing: border-box;
    }

    .empty-state .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      font-family: Georgia, 'Times New Roman', serif;
      font-size: clamp(24px, 4vw, 72px);
      font-weight: 500;
      margin-bottom: 24px;
      color: #3d2f2a;
      max-width: 100%;
      overflow: hidden;
    }

    .empty-state .logo img {
      height: clamp(40px, 2vw, 80px);
      width: auto;
      flex-shrink: 0;
    }


    .empty-state p {
      margin: 0 0 12px 0;
      color: #6b574f;
      font-size: 16px;
      max-width: 400px;
    }

    .empty-state-hint {
      font-size: 14px;
      color: #a08a80;
      margin-top: 8px;
    }

    .empty-state-tagline {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 2.5rem;
      font-weight: 400;
      margin: 0 0 1.5rem 0;
      color: #3d2f2a;
      letter-spacing: -0.02em;
      line-height: 1.1;
    }

    .empty-state-tagline em {
      font-style: italic;
      font-weight: 500;
      color: #a64b2d;
    }

    .upload-btn {
      padding: 14px 28px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 600;
      font-family: inherit;
      transition: all 0.15s;
    }

    .upload-btn:hover {
      background: #2d211c;
    }

    .empty-state-actions {
      display: flex;
      gap: 16px;
      justify-content: center;
      align-items: center;
    }

    .zotero-btn {
      padding: 14px 28px;
      background: white;
      color: #3d2f2a;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 600;
      font-family: inherit;
      transition: all 0.15s;
    }

    .zotero-btn:hover {
      background: #f9f3ef;
      border-color: #a08a80;
    }

    .pdf-error-state {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px;
      text-align: center;
      background: #3d2f2a;
    }

    .pdf-error-icon {
      width: 64px;
      height: 64px;
      margin-bottom: 24px;
      color: #fce9e2;
    }

    .pdf-error-icon svg {
      width: 100%;
      height: 100%;
    }

    .pdf-error-state h2 {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 24px;
      font-weight: 500;
      margin: 0 0 12px 0;
      color: white;
    }

    .pdf-error-state p {
      font-size: 16px;
      color: rgba(255, 255, 255, 0.8);
      margin: 0 0 24px 0;
      max-width: 400px;
      line-height: 1.6;
    }

    .pdf-error-state .zotero-btn {
      background: #fce9e2;
      color: #a64b2d;
      border: none;
      font-weight: 600;
    }

    .pdf-error-state .zotero-btn:hover {
      background: white;
    }

    @media (max-width: 600px) {
      .empty-state-actions {
        flex-direction: column;
        width: 100%;
        max-width: 280px;
      }

      .empty-state-tagline {
        font-size: 2rem;
      }

      .upload-btn,
      .zotero-btn {
        width: 100%;
        text-align: center;
      }
    }

    input[type='file'] {
      display: none;
    }

    .loading-screen {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: #525659;
    }

    .error-screen {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: #525659;
      padding: 40px;
    }

    .error-screen error-message {
      max-width: 500px;
      margin-bottom: 20px;
    }

    /* Upload metadata dialog */
    .upload-metadata-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(61, 47, 42, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      padding: 20px;
    }

    .upload-metadata-dialog {
      background: white;
      border-radius: 8px;
      max-width: 500px;
      width: 100%;
      padding: 24px;
      box-shadow: 0 4px 20px rgba(61, 47, 42, 0.15);
    }

    .upload-metadata-dialog h2 {
      margin: 0 0 8px 0;
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 18px;
      font-weight: 500;
      color: #3d2f2a;
    }

    .upload-metadata-dialog p {
      margin: 0 0 20px 0;
      font-size: 13px;
      color: #6b574f;
      line-height: 1.5;
    }

    .upload-metadata-dialog .field {
      margin-bottom: 16px;
    }

    .upload-metadata-dialog .field label {
      display: block;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 600;
      color: #3d2f2a;
    }

    .upload-metadata-dialog .field input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      font-size: 14px;
      font-family: inherit;
      box-sizing: border-box;
      background: #fdfaf8;
      color: #3d2f2a;
      transition: border-color 0.15s;
    }

    .upload-metadata-dialog .field input:focus {
      outline: none;
      border-color: #c45d3a;
    }

    .upload-metadata-dialog .field input::placeholder {
      color: #a08a80;
    }

    .upload-metadata-dialog .actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      margin-top: 24px;
    }

    .upload-metadata-dialog .btn {
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.15s;
    }

    .upload-metadata-dialog .btn-secondary {
      background: #f9f3ef;
      color: #6b574f;
    }

    .upload-metadata-dialog .btn-secondary:hover {
      background: #e8dfd9;
    }

    .upload-metadata-dialog .btn-primary {
      background: #3d2f2a;
      color: white;
    }

    .upload-metadata-dialog .btn-primary:hover {
      background: #2d211c;
    }

    /* Mobile styles */
    .mobile-bottom-nav {
      display: none;
    }

    @media (max-width: 768px) {
      :host {
        flex-direction: column;
      }

      .left-pane {
        width: 100%;
        height: 100%;
        border-right: none;
        display: none;
      }

      .center-pane {
        display: none;
      }

      :host([data-mobile-view='home']) .left-pane,
      :host([data-mobile-view='discuss']) .left-pane,
      :host([data-mobile-view='insights']) .left-pane {
        display: flex;
      }

      :host([data-mobile-view='paper']) .center-pane {
        display: flex;
      }

      .mobile-bottom-nav {
        display: flex;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        border-top: 1px solid #e8dfd9;
        z-index: 1000;
        padding: 4px 0;
        padding-bottom: max(4px, env(safe-area-inset-bottom));
      }

      .mobile-nav-btn {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        padding: 4px;
        background: none;
        border: none;
        color: #a08a80;
        font-size: 10px;
        font-family: inherit;
        cursor: pointer;
        transition: color 0.15s;
      }

      .mobile-nav-btn.active {
        color: #3d2f2a;
      }

      .mobile-nav-btn svg {
        width: 20px;
        height: 20px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
      }

      .mobile-nav-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      :host {
        padding-bottom: 44px;
      }
    }

    @media (min-width: 769px) {
      .mobile-bottom-nav {
        display: none !important;
      }

      :host {
        padding-bottom: 0 !important;
      }
    }
  `;

  private renderEmptyState() {
    return html`
      <div class="empty-state">
        <div class="logo">
          <img src="/logo_small.png?v=2" alt="Scholia" />
          Scholia.fyi
        </div>
        <h1 class="empty-state-tagline">Read <em>critically.</em></h1>
        <p class="empty-state-hint">Select a recent paper, load from Zotero, or upload a PDF to get started.</p>
      </div>
    `;
  }

  private renderLoadingScreen() {
    return html`
      <div class="loading-screen">
        <loading-spinner size="large" message="Analyzing paper..." light></loading-spinner>
      </div>
    `;
  }

  private renderErrorScreen() {
    return html`
      <div class="error-screen">
        <error-message .message=${this.error} .actionHref=${this.errorActionHref}></error-message>
        <label class="upload-btn">
          Upload PDF
          <input type="file" accept=".pdf" @change=${this.handleFileUpload} />
        </label>
      </div>
    `;
  }

  render() {
    return html`
      <!-- Mobile bottom navigation -->
      <nav class="mobile-bottom-nav">
        <button
          class="mobile-nav-btn ${this.mobileView === 'home' ? 'active' : ''}"
          @click=${this.handleHomeClick}
        >
          <svg viewBox="0 0 24 24">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          <span>Home</span>
        </button>

        <button
          class="mobile-nav-btn ${this.mobileView === 'paper' ? 'active' : ''}"
          @click=${() => (this.mobileView = 'paper')}
          ?disabled=${!this.sessionId}
        >
          <svg viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span>Paper</span>
        </button>

        <button
          class="mobile-nav-btn ${this.mobileView === 'discuss' ? 'active' : ''}"
          @click=${() => (this.mobileView = 'discuss')}
          ?disabled=${!this.sessionId}
        >
          <svg viewBox="0 0 24 24">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span>Discuss</span>
        </button>

        <button
          class="mobile-nav-btn ${this.mobileView === 'insights' ? 'active' : ''}"
          @click=${() => (this.mobileView = 'insights')}
          ?disabled=${!this.sessionId}
        >
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>Insights</span>
        </button>
      </nav>

      <div class="left-pane">
        <left-panel
          .sessionId=${this.sessionId}
          .filename=${this.filename}
          .paperTitle=${this.paperTitle}
          .paperAuthors=${this.paperAuthors}
          .paperYear=${this.paperYear}
          .paperPublicationDate=${this.paperPublicationDate}
          .paperJournal=${this.paperJournal}
          .paperJournalAbbr=${this.paperJournalAbbr}
          .zoteroKey=${this.zoteroKey}
          .sessionLabel=${this.sessionLabel}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          .geminiAvailable=${this.geminiAvailable}
          .activeTab=${this.mobileView === 'insights' ? 'concepts' : 'ask'}
          @conversation-updated=${(e: CustomEvent) => (this.conversation = e.detail.conversation)}
          @flags-updated=${(e: CustomEvent) => (this.flags = e.detail.flags)}
          @clear-selection=${this.handleClearSelection}
          @navigate-to-page=${this.handleNavigateToPage}
          @home-click=${this.handleHomeClick}
          @session-selected=${this.handleSessionSelected}
          @zotero-picker-open=${this.handleShowZoteroPicker}
          @upload-pdf=${(e: CustomEvent) => this.handleFileUpload(e.detail.event)}
        ></left-panel>
      </div>

      <div class="center-pane">
        ${this.loading
          ? this.renderLoadingScreen()
          : this.error
            ? this.renderErrorScreen()
            : this.pdfUrl
              ? this.pdfLoadError
                ? html`
                    <div class="pdf-error-state">
                      <div class="pdf-error-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <line x1="12" y1="8" x2="12" y2="12"></line>
                          <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                      </div>
                      <h2>PDF Not Available</h2>
                      <p>The PDF file could not be loaded. This may happen if your Zotero library settings have changed.</p>
                      <button class="zotero-btn" @click=${this.handleReselectPaper}>
                        Load Different Paper from Zotero
                      </button>
                    </div>
                  `
                : html`
                    <pdf-viewer .pdfUrl=${this.pdfUrl} @text-selected=${this.handleTextSelection} @pdf-load-error=${this.handlePdfLoadError}></pdf-viewer>
                  `
              : this.renderEmptyState()}
      </div>

      <session-list
        .visible=${this.showSessionPicker}
        @session-selected=${this.handleSessionSelected}
        @close=${this.handleCloseSessionPicker}
        @upload-new=${this.handleUploadNewFromPicker}
      ></session-list>

      <zotero-picker
        .visible=${this.showZoteroPicker}
        @zotero-paper-selected=${this.handleZoteroPaperSelected}
        @session-selected=${this.handleSessionSelected}
        @close=${this.handleCloseZoteroPicker}
      ></zotero-picker>

      ${this.showUploadMetadataDialog
        ? html`
            <div
              class="upload-metadata-overlay"
              @click=${(e: Event) => e.target === e.currentTarget && this.handleCancelUpload()}
            >
              <div class="upload-metadata-dialog">
                <h2>Paper Metadata (Optional)</h2>
                <p>
                  If you know the DOI or PMID for this paper, enter it below. We'll automatically fetch the
                  metadata. Otherwise, we'll extract it from the PDF.
                </p>

                <div class="field">
                  <label>DOI</label>
                  <input
                    type="text"
                    .value=${this.uploadDoi}
                    @input=${(e: Event) => (this.uploadDoi = (e.target as HTMLInputElement).value)}
                    placeholder="10.1234/example"
                  />
                </div>

                <div class="field">
                  <label>PMID</label>
                  <input
                    type="text"
                    .value=${this.uploadPmid}
                    @input=${(e: Event) => (this.uploadPmid = (e.target as HTMLInputElement).value)}
                    placeholder="12345678"
                  />
                </div>

                <div class="actions">
                  <button class="btn btn-secondary" @click=${this.handleCancelUpload}>Cancel</button>
                  <button class="btn btn-primary" @click=${this.handleUploadWithMetadata}>Upload</button>
                </div>
              </div>
            </div>
          `
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-shell': AppShell;
  }
}
