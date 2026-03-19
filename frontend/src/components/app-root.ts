import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../services/api';
import { sessionStorage } from '../services/session-storage';
import type { ConversationMessage, Session } from '../types/session';
import type { TextSelection } from '../types/pdf';
import './pdf-viewer/pdf-viewer';
import './left-panel/left-panel';
import './session-picker/session-list';
import './zotero-picker/zotero-picker';
import './shared/loading-spinner';
import './shared/error-message';
import type { PdfViewer } from './pdf-viewer/pdf-viewer';
import type { ZoteroItem } from '../types/session';

@customElement('app-root')
export class AppRoot extends LitElement {
  @state() private sessionId = '';
  @state() private filename = '';
  @state() private zoteroKey?: string;  // Zotero key if session was loaded from Zotero
  @state() private paperTitle?: string;  // Paper title from metadata
  @state() private paperAuthors?: string;  // Authors from metadata
  @state() private paperYear?: string;  // Publication year extracted from metadata
  @state() private paperJournal?: string;  // Journal name from metadata
  @state() private paperJournalAbbr?: string;  // Journal abbreviation from Zotero
  @state() private pdfUrl = '';
  @state() private conversation: ConversationMessage[] = [];
  @state() private flags: number[] = [];
  @state() private selectedText = '';
  @state() private selectedPage?: number;
  @state() private loading = false;
  @state() private error = '';
  @state() private errorActionHref = '';
  @state() private showSessionPicker = false;
  @state() private showZoteroPicker = false;
  @state() private geminiAvailable = false;  // Whether Gemini models are available
  @state() private mobileView: 'home' | 'paper' | 'discuss' | 'insights' = 'home';  // Mobile view (4 tabs)
  @state() private showUploadMetadataDialog = false;
  @state() private pendingFile: File | null = null;
  @state() private uploadDoi = '';
  @state() private uploadPmid = '';

  @query('pdf-viewer') private pdfViewer?: PdfViewer;

  private boundKeydownHandler = this.handleKeydown.bind(this);

  /**
   * Extract year from publication_date string.
   * Handles formats like "2023", "2023-01-15", "January 2023", etc.
   */
  private extractYear(publicationDate?: string): string | undefined {
    if (!publicationDate) return undefined;
    const yearMatch = publicationDate.match(/\d{4}/);
    return yearMatch ? yearMatch[0] : undefined;
  }

  async connectedCallback() {
    super.connectedCallback();
    document.addEventListener('keydown', this.boundKeydownHandler);

    // Load saved zoom preference
    const savedZoom = sessionStorage.getPdfZoom();
    if (this.pdfViewer && savedZoom) {
      this.pdfViewer.scale = savedZoom;
    }

    // Check app configuration (feature availability)
    try {
      const appConfig = await api.getAppConfig();
      this.geminiAvailable = appConfig.gemini_available;
    } catch (err) {
      console.warn('Failed to fetch app config:', err);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener('keydown', this.boundKeydownHandler);
  }

  updated(changedProperties: Map<string, any>) {
    super.updated(changedProperties);

    // Update data-has-session attribute for mobile CSS
    if (changedProperties.has('sessionId')) {
      if (this.sessionId) {
        this.setAttribute('data-has-session', '');
        // Restore saved mobile view or default to paper view
        const savedView = sessionStorage.getMobileView();
        if (savedView && savedView !== 'home') {
          this.mobileView = savedView;
        } else {
          this.mobileView = 'paper';
        }
      } else {
        this.removeAttribute('data-has-session');
        // Go back to home when session cleared
        this.mobileView = 'home';
      }
    }

    // Update data-mobile-view attribute for mobile CSS and save preference
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
    // Find the query input in the shadow DOM
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

  private async flagLastExchange() {
    if (!this.sessionId || this.conversation.length < 2) return;

    // Find the last assistant message
    const lastAssistantMsg = [...this.conversation]
      .reverse()
      .find(msg => msg.role === 'assistant');

    if (lastAssistantMsg && lastAssistantMsg.id > 1) {
      const isFlagged = this.flags.includes(lastAssistantMsg.id);

      try {
        if (isFlagged) {
          await api.unflag(this.sessionId, lastAssistantMsg.id);
          this.flags = this.flags.filter(id => id !== lastAssistantMsg.id);
        } else {
          await api.toggleFlag(this.sessionId, lastAssistantMsg.id);
          this.flags = [...this.flags, lastAssistantMsg.id];
        }
      } catch (err) {
        console.error('Failed to toggle flag:', err);
      }
    }
  }

  static styles = css`
    :host {
      display: flex;
      /* Use dvh to account for mobile browser chrome (address bar, toolbar) */
      /* Falls back to vh for browsers that don't support dvh */
      height: 100vh;
      height: 100dvh;
      font-family: 'Lora', Georgia, serif;
    }

    .left-panel {
      width: 450px;
      min-width: 450px;
      flex-shrink: 0;
      border-right: 1px solid #e0e0e0;
      display: flex;
      flex-direction: column;
      background: #f8f9fa;
    }

    left-panel {
      height: 100%;
    }

    .center-pane {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: white;
      color: #333;
      padding: 40px;
      text-align: center;
    }

    .empty-state h2 {
      margin: 0 0 8px 0;
      font-size: 32px;
    }

    .empty-state .logo {
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 72px;
      font-weight: 400;
      margin-bottom: 24px;
      color: #3d2f2a;
    }

    .empty-state .logo img {
      height: clamp(40px, 2vw, 80px);
      width: auto;
    }


    .empty-state .tagline {
      margin: 0 0 24px 0;
      color: #666;
      font-size: 14px;
      font-style: italic;
      font-weight: 300;
    }

    .empty-state p {
      margin: 0 0 32px 0;
      color: #666;
      font-size: 16px;
      max-width: 400px;
    }

    .upload-btn {
      padding: 14px 28px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .upload-btn:hover {
      background: #333;
    }

    .secondary-btn {
      padding: 14px 28px;
      background: transparent;
      color: white;
      border: 2px solid white;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .secondary-btn:hover {
      background: rgba(255, 255, 255, 0.1);
    }

    .empty-state-actions {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      justify-content: center;
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

    .recent-sessions {
      width: 100%;
      max-width: 500px;
      margin: 0 0 32px 0;
    }

    .recent-sessions h3 {
      font-size: 16px;
      margin: 0 0 16px 0;
      color: rgba(255, 255, 255, 0.9);
      text-align: left;
    }

    .session-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      margin-bottom: 8px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
      text-align: left;
    }

    .session-item:hover {
      background: rgba(255, 255, 255, 0.15);
      border-color: rgba(255, 255, 255, 0.3);
    }

    .session-item:last-child {
      margin-bottom: 0;
    }

    .session-info {
      flex: 1;
      min-width: 0;
    }

    .session-filename {
      font-weight: 500;
      font-size: 14px;
      color: white;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .session-meta {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
    }

    .see-all-link {
      color: rgba(255, 255, 255, 0.8);
      font-size: 14px;
      text-decoration: none;
      cursor: pointer;
      display: inline-block;
      margin-top: 12px;
    }

    .see-all-link:hover {
      color: white;
      text-decoration: underline;
    }

    .no-sessions {
      color: rgba(255, 255, 255, 0.7);
      font-size: 14px;
      margin-bottom: 24px;
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
      :host {
        position: relative;
      }

      .left-panel {
        width: 100%;
        min-width: 100%;
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 10;
      }

      .center-pane {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 5;
      }

      /* Mobile view switching */
      /* Home view: show left panel (paper list) */
      :host([data-mobile-view="home"]) .left-panel {
        z-index: 10;
      }

      :host([data-mobile-view="home"]) .center-pane {
        display: none;
      }

      /* Paper view: show PDF, hide left panel */
      :host([data-mobile-view="paper"]) .left-panel {
        display: none;
      }

      :host([data-mobile-view="paper"]) .center-pane {
        z-index: 10;
      }

      /* Discuss view: show left panel (discuss tab), hide PDF */
      :host([data-mobile-view="discuss"]) .left-panel {
        z-index: 10;
      }

      :host([data-mobile-view="discuss"]) .center-pane {
        display: none;
      }

      /* Insights view: show left panel (insights tab), hide PDF */
      :host([data-mobile-view="insights"]) .left-panel {
        z-index: 10;
      }

      :host([data-mobile-view="insights"]) .center-pane {
        display: none;
      }

      /* Mobile bottom navigation bar */
      .mobile-bottom-nav {
        display: flex;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        /* 44px for nav content, safe-area for home indicator padding */
        height: 44px;
        padding-bottom: env(safe-area-inset-bottom, 0px);
        box-sizing: content-box; /* padding adds to height */
        background: white;
        border-top: 1px solid #e0e0e0;
        z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
      }

      .mobile-nav-btn {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        background: none;
        border: none;
        color: #666;
        font-size: 10px;
        font-weight: 500;
        cursor: pointer;
        transition: color 0.2s;
      }

      .mobile-nav-btn svg {
        width: 20px;
        height: 20px;
        stroke: currentColor;
        fill: none;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      .mobile-nav-btn.active {
        color: #3d2f2a;
      }

      .mobile-nav-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      /* Add padding to content to account for bottom nav */
      :host {
        padding-bottom: 44px;
      }
    }

    /* Hide mobile nav on desktop */
    @media (min-width: 769px) {
      .mobile-bottom-nav {
        display: none !important;
      }

      :host {
        padding-bottom: 0 !important;
      }
    }

    /* Upload metadata dialog */
    .upload-metadata-overlay {
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

    .upload-metadata-dialog {
      background: white;
      border-radius: 8px;
      max-width: 500px;
      width: 100%;
      padding: 24px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }

    .upload-metadata-dialog h2 {
      margin: 0 0 8px 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }

    .upload-metadata-dialog p {
      margin: 0 0 20px 0;
      font-size: 13px;
      color: #666;
      line-height: 1.4;
    }

    .upload-metadata-dialog .field {
      margin-bottom: 16px;
    }

    .upload-metadata-dialog .field label {
      display: block;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 500;
      color: #555;
    }

    .upload-metadata-dialog .field input {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      font-family: inherit;
      box-sizing: border-box;
    }

    .upload-metadata-dialog .field input:focus {
      outline: none;
      border-color: #3d2f2a;
    }

    .upload-metadata-dialog .actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      margin-top: 24px;
    }

    .upload-metadata-dialog .btn {
      padding: 8px 20px;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
    }

    .upload-metadata-dialog .btn-secondary {
      background: #f5f5f5;
      color: #666;
    }

    .upload-metadata-dialog .btn-secondary:hover {
      background: #e0e0e0;
    }

    .upload-metadata-dialog .btn-primary {
      background: #3d2f2a;
      color: white;
    }

    .upload-metadata-dialog .btn-primary:hover {
      background: #1557b0;
    }
  `;

  async handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file || file.type !== 'application/pdf') {
      this.error = 'Please select a valid PDF file';
      return;
    }

    // Store file and show metadata dialog
    this.pendingFile = file;
    this.uploadDoi = '';
    this.uploadPmid = '';
    this.showUploadMetadataDialog = true;

    // Reset file input
    input.value = '';
  }

  async handleUploadWithMetadata() {
    if (!this.pendingFile) return;

    this.loading = true;
    this.error = '';
    this.errorActionHref = '';
    this.showUploadMetadataDialog = false;

    try {
      // Create session with backend, passing DOI/PMID if provided
      const session = await api.createSession(
        this.pendingFile,
        this.uploadDoi || undefined,
        this.uploadPmid || undefined
      );

      this.sessionId = session.session_id;
      this.filename = session.filename;
      this.paperTitle = session.title;
      this.paperAuthors = session.authors;
      this.paperYear = this.extractYear(session.publication_date);
      this.paperJournal = session.journal;
      this.paperJournalAbbr = session.journal_abbr;
      this.zoteroKey = undefined;  // File upload, no Zotero key
      this.pdfUrl = URL.createObjectURL(this.pendingFile);

      // Save to session storage for "pick up where left off"
      sessionStorage.setLastSessionId(session.session_id);

      // Initialize conversation with initial analysis
      this.conversation = [
        {
          id: 0,
          exchange_id: 0,
          role: 'user',
          content: 'Initial analysis',
          timestamp: session.created_at
        },
        {
          id: 1,
          exchange_id: 0,
          role: 'assistant',
          content: session.initial_analysis,
          timestamp: session.created_at
        }
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
      } else if (err instanceof ApiError && err.status === 400 && err.details?.error === 'PAGE_LIMIT_EXCEEDED') {
        this.error = err.details.message ?? err.message;
        this.errorActionHref = '/pricing';
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

  handleShowSessionPicker() {
    this.showSessionPicker = true;
  }

  handleCloseSessionPicker() {
    this.showSessionPicker = false;
  }

  async handleSessionSelected(e: CustomEvent<{ session: Session }>) {
    const { session } = e.detail;
    this.showSessionPicker = false;
    this.loading = true;
    this.error = '';

    try {
      // Load full session data
      const fullSession = await api.getSession(session.session_id);

      this.sessionId = fullSession.session_id;
      this.filename = fullSession.filename;
      this.paperTitle = fullSession.title;
      this.paperAuthors = fullSession.authors;
      this.paperYear = this.extractYear(fullSession.publication_date);
      this.paperJournal = fullSession.journal;
      this.paperJournalAbbr = fullSession.journal_abbr;
      this.zoteroKey = fullSession.zotero_key;  // Restore Zotero key if available
      this.flags = fullSession.flags || [];

      // Build conversation with initial analysis as first messages
      const initialMessages: ConversationMessage[] = [];
      if (fullSession.initial_analysis) {
        initialMessages.push({
          id: 0,
          exchange_id: 0,
          role: 'user',
          content: 'Initial analysis',
          timestamp: fullSession.created_at
        });
        initialMessages.push({
          id: 1,
          exchange_id: 0,
          role: 'assistant',
          content: fullSession.initial_analysis,
          timestamp: fullSession.created_at
        });
      }

      // Convert conversation messages from API format to frontend format
      const conversationMessages: ConversationMessage[] = (fullSession.conversation || []).map((msg: any) => ({
        id: msg.exchange_id,
        exchange_id: msg.exchange_id,
        role: msg.role,
        content: msg.content,
        model: msg.model,
        highlighted_text: msg.highlighted_text,
        page: msg.page_number,
        timestamp: msg.timestamp
      }));

      this.conversation = [...initialMessages, ...conversationMessages];

      // Save to session storage
      sessionStorage.setLastSessionId(fullSession.session_id);

      // Load PDF from backend
      this.pdfUrl = `/sessions/${fullSession.session_id}/pdf`;
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

  handleUploadNewFromPicker() {
    this.showSessionPicker = false;
    // Trigger file input click
    const fileInput = this.shadowRoot?.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  }

  handleShowZoteroPicker() {
    this.showZoteroPicker = true;
  }

  handleCloseZoteroPicker() {
    this.showZoteroPicker = false;
  }

  handleHomeClick() {
    // Clear current session and return to empty state
    this.sessionId = '';
    this.filename = '';
    this.paperTitle = undefined;
    this.paperAuthors = undefined;
    this.paperYear = undefined;
    this.paperJournal = undefined;
    this.paperJournalAbbr = undefined;
    this.zoteroKey = undefined;
    this.pdfUrl = '';
    this.conversation = [];
    this.flags = [];
    this.selectedText = '';
    this.selectedPage = undefined;
    this.error = '';
    this.mobileView = 'home'; // Navigate to home view on mobile
  }

  async handleZoteroPaperSelected(e: CustomEvent<{ session: Session; paper: ZoteroItem }>) {
    const { session, paper } = e.detail;
    this.showZoteroPicker = false;
    this.loading = true;
    this.error = '';

    try {
      // Load full session data
      const fullSession = await api.getSession(session.session_id);

      this.sessionId = fullSession.session_id;
      this.filename = fullSession.filename;
      this.paperTitle = fullSession.title;
      this.paperAuthors = fullSession.authors;
      this.paperYear = this.extractYear(fullSession.publication_date);
      this.paperJournal = fullSession.journal;
      this.paperJournalAbbr = fullSession.journal_abbr;
      this.zoteroKey = paper.key;  // Set Zotero key from selected paper
      this.flags = fullSession.flags || [];

      // Build conversation with initial analysis as first messages
      const initialMessages: ConversationMessage[] = [];
      if (fullSession.initial_analysis) {
        initialMessages.push({
          id: 0,
          exchange_id: 0,
          role: 'user',
          content: 'Initial analysis',
          timestamp: fullSession.created_at
        });
        initialMessages.push({
          id: 1,
          exchange_id: 0,
          role: 'assistant',
          content: fullSession.initial_analysis,
          timestamp: fullSession.created_at
        });
      }

      // Convert conversation messages from API format to frontend format
      const conversationMessages: ConversationMessage[] = (fullSession.conversation || []).map((msg: any) => ({
        id: msg.exchange_id,
        exchange_id: msg.exchange_id,
        role: msg.role,
        content: msg.content,
        model: msg.model,
        highlighted_text: msg.highlighted_text,
        page: msg.page_number,
        timestamp: msg.timestamp
      }));

      this.conversation = [...initialMessages, ...conversationMessages];

      // Save to session storage
      sessionStorage.setLastSessionId(fullSession.session_id);

      // Load PDF from backend
      this.pdfUrl = `/sessions/${fullSession.session_id}/pdf`;
      this.loading = false;

    } catch (err) {
      console.error('Failed to load Zotero session:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load paper from Zotero';
      }
      this.loading = false;
    }
  }

  private renderEmptyState() {
    return html`
      <div class="empty-state">
        <div class="logo">
          <img src="/logo_small.png?v=2" alt="Scholia" />
          Scholia.fyi
        </div>
        <p>Upload a PDF to get started.</p>
        <div class="empty-state-actions">
          <label class="upload-btn">
            Upload PDF
            <input type="file" accept=".pdf" @change=${this.handleFileUpload} />
          </label>
        </div>
      </div>
    `;
  }

  private renderLoadingScreen() {
    return html`
      <div class="loading-screen">
        <loading-spinner
          size="large"
          message="Analyzing paper..."
          light
        ></loading-spinner>
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
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
          <span>Home</span>
        </button>

        <button
          class="mobile-nav-btn ${this.mobileView === 'paper' ? 'active' : ''}"
          @click=${() => this.mobileView = 'paper'}
          ?disabled=${!this.sessionId}
        >
          <svg viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>Paper</span>
        </button>

        <button
          class="mobile-nav-btn ${this.mobileView === 'discuss' ? 'active' : ''}"
          @click=${() => this.mobileView = 'discuss'}
          ?disabled=${!this.sessionId}
        >
          <svg viewBox="0 0 24 24">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span>Discuss</span>
        </button>

        <button
          class="mobile-nav-btn ${this.mobileView === 'insights' ? 'active' : ''}"
          @click=${() => this.mobileView = 'insights'}
          ?disabled=${!this.sessionId}
        >
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4M12 8h.01"/>
          </svg>
          <span>Insights</span>
        </button>
      </nav>

      <div class="left-panel">
        <left-panel
          .sessionId=${this.sessionId}
          .filename=${this.filename}
          .paperTitle=${this.paperTitle}
          .paperAuthors=${this.paperAuthors}
          .paperYear=${this.paperYear}
          .paperJournal=${this.paperJournal}
          .paperJournalAbbr=${this.paperJournalAbbr}
          .zoteroKey=${this.zoteroKey}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          .geminiAvailable=${this.geminiAvailable}
          .activeTab=${this.mobileView === 'insights' ? 'concepts' : 'ask'}
          @conversation-updated=${(e: CustomEvent) =>
            (this.conversation = e.detail.conversation)}
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
          ? html`
              <pdf-viewer
                .pdfUrl=${this.pdfUrl}
                @text-selected=${this.handleTextSelection}
              ></pdf-viewer>
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
                  If you know the DOI or PMID for this paper, enter it below. We'll automatically fetch the metadata.
                  Otherwise, we'll extract it from the PDF.
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
    'app-root': AppRoot;
  }
}
