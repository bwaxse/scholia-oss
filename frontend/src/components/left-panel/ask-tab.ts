import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { ConversationMessage, Session, MessageEvaluation } from '../../types/session';
import type { QueryRequest, ModelType } from '../../types/query';
import type { ZoteroItem } from '../../types/session';
import '../shared/conversation-item';
import '../shared/query-input';
import '../shared/loading-spinner';
import '../shared/error-message';
import '../zotero-picker/zotero-picker';

interface SessionGroup {
  groupKey: string;       // zotero_key or title-based key
  displayTitle: string;   // Paper title for display
  authors?: string;
  sessions: Session[];
}

@customElement('ask-tab')
export class AskTab extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: Array }) conversation: ConversationMessage[] = [];
  @property({ type: Array }) flags: number[] = [];
  @property({ type: Object }) evaluations: Map<number, MessageEvaluation> = new Map();
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;
  @property({ type: String }) zoteroKey?: string;  // Zotero key if session was loaded from Zotero
  @property({ type: String }) paperTitle?: string;  // Paper title from metadata
  @property({ type: String }) paperAuthors?: string;  // Authors from metadata
  @property({ type: String }) paperYear?: string;  // Publication year from metadata
  @property({ type: String }) paperJournal?: string;  // Journal name from metadata
  @property({ type: String }) paperJournalAbbr?: string;  // Journal abbreviation from Zotero
  @property({ type: String }) filename = '';
  @property({ type: Boolean }) geminiAvailable = false;
  @property({ type: Object }) modelAccess = { haiku: true, flash: true, sonnet: true, gemini_pro: true };

  @state() private loading = false;
  @state() private error = '';
  @state() private showSupplementPicker = false;
  @state() private loadingSupplements = false;
  @state() private supplementAttachments: ZoteroItem[] = [];
  @state() private supplementCount: number | null = null; // null = not loaded yet, 0 = none available, >0 = count
  @state() private selectedModel: ModelType = 'sonnet'; // Default to Sonnet
  @state() private allSessions: Session[] = [];
  @state() private loadingSessions = false;
  @state() private zoteroConfigured = false;
  @state() private initialLoadComplete = false;
  @state() private showAllMobileSessions = false;
  @state() private showAllGroups = false; // Show all groups beyond 7 on desktop
  @state() private expandedGroups: Set<string> = new Set();
  @state() private showSearch = false;
  @state() private searchQuery = '';
  @state() private deletingId?: string;

  connectedCallback() {
    super.connectedCallback();
    this.checkZoteroConfig();
  }

  private async checkZoteroConfig() {
    try {
      const response = await fetch('/api/settings/zotero');
      if (response.ok) {
        const config = await response.json();
        this.zoteroConfigured = config.configured;
      }
    } catch (err) {
      console.error('Failed to check Zotero config:', err);
    }
  }

  @query('.conversation-container') private conversationContainer!: HTMLElement;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f9f3ef;
    }

    .conversation-container {
      flex: 1;
      overflow-y: auto;
      padding: 0;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      text-align: center;
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
      line-height: 1.5;
    }

    .sessions-list-container {
      padding: 16px;
      flex: 1;
      overflow-y: auto;
    }

    /* Mobile styles for sessions list */
    @media (max-width: 768px) {
      .sessions-list-container {
        padding-top: 0; /* Remove top padding on mobile to prevent scroll cutoff */
      }
    }

    .sessions-header {
      margin: 16px 0 16px 0; /* Add top margin to prevent cutoff */
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }

    .sessions-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .search-icon-btn {
      background: none;
      border: none;
      padding: 4px;
      cursor: pointer;
      color: #666;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.2s;
    }

    .search-icon-btn:hover {
      color: #333;
    }

    .search-icon-btn svg {
      width: 18px;
      height: 18px;
    }

    .search-input-row {
      margin-bottom: 12px;
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .search-input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      font-size: 13px;
      font-family: inherit;
      color: #333;
      background: white;
    }

    .search-input:focus {
      outline: none;
      border-color: #3d2f2a;
    }

    .search-input::placeholder {
      color: #999;
    }

    .search-close-btn {
      background: none;
      border: none;
      padding: 4px;
      cursor: pointer;
      color: #666;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .search-close-btn:hover {
      color: #333;
    }

    .home-action-buttons {
      display: flex;
      flex-direction: row;
      gap: 12px;
      padding: 16px;
      background: #f9f3ef;
      border-top: 1px solid #e8dfd9;
      flex-shrink: 0;
    }

    .upload-pdf-btn,
    .load-zotero-btn {
      flex: 1;
      padding: 12px;
      background: #3d2f2a;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      font-family: 'Lora', Georgia, serif;
      text-align: center;
      cursor: pointer;
      transition: background 0.2s;
    }

    .upload-pdf-btn:hover,
    .load-zotero-btn:hover {
      background: #2d211c;
    }

    .upload-pdf-btn input[type="file"] {
      display: none;
    }

    .sessions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .see-more-btn {
      display: block;
      padding: 10px;
      background: transparent;
      border: 1px dashed #c4b5ab;
      border-radius: 6px;
      color: #6b574f;
      font-size: 13px;
      font-family: inherit;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s;
    }

    .see-more-btn:hover {
      background: #f0e8e2;
      border-color: #3d2f2a;
      color: #3d2f2a;
    }

    .see-more-btn .mobile-text {
      display: none;
    }

    .see-more-btn .desktop-text {
      display: inline;
    }

    @media (max-width: 768px) {

      .see-more-btn .mobile-text {
        display: inline;
      }

      .see-more-btn .desktop-text {
        display: none;
      }

      .desktop-only {
        display: none; /* Hide extra sessions/groups on mobile */
      }
    }

    .session-item {
      background: white;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .session-item:hover {
      border-color: #3d2f2a;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .session-info-single {
      flex: 1;
      min-width: 0;
    }

    .session-info {
      flex: 1;
      min-width: 0;
    }

    .delete-btn-icon {
      flex-shrink: 0;
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

    .delete-btn-icon:hover {
      color: #c45d3a;
      background: #fce9e2;
    }

    .delete-btn-icon:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .session-filename {
      font-size: 12px;
      font-weight: 500;
      color: #666;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .session-date {
      font-size: 12px;
      color: #666;
    }

    /* Session grouping styles */
    .session-group {
      margin-bottom: 8px;
    }

    .session-group:last-child {
      margin-bottom: 0;
    }

    .group-header {
      display: flex;
      align-items: center;
      padding: 10px 12px;
      background: white;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s;
      gap: 8px;
    }

    .group-header:hover {
      background: #f8f9fa;
      border-color: #3d2f2a;
    }

    .group-header.expanded {
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
      border-bottom-color: transparent;
    }

    .expand-icon {
      flex-shrink: 0;
      width: 14px;
      height: 14px;
      transition: transform 0.15s;
    }

    .expand-icon.expanded {
      transform: rotate(90deg);
    }

    .group-info {
      flex: 1;
      min-width: 0;
    }

    .group-title {
      font-weight: 500;
      font-size: 14px;
      color: #333;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .group-count {
      flex-shrink: 0;
      font-size: 11px;
      color: #666;
      background: #e8dfd9;
      padding: 2px 8px;
      border-radius: 10px;
    }

    .group-sessions {
      border: 1px solid #e8dfd9;
      border-top: none;
      border-bottom-left-radius: 6px;
      border-bottom-right-radius: 6px;
      overflow: hidden;
    }

    .group-sessions .session-item {
      margin-bottom: 0;
      border-radius: 0;
      border-left: none;
      border-right: none;
      border-top: none;
      background: white;
      padding: 8px 12px;
    }

    .group-sessions .session-item:last-child {
      border-bottom: none;
    }

    .group-sessions .session-item:hover {
      background: #f8f9fa;
    }

    .session-label-badge {
      display: inline-block;
      font-size: 11px;
      color: #6b5b4f;
      background: #f5f0eb;
      padding: 2px 6px;
      border-radius: 4px;
      margin-right: 8px;
      font-weight: 500;
    }

    .no-sessions {
      text-align: center;
      padding: 40px 20px;
      color: #666;
    }

    .no-sessions p {
      margin: 4px 0;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
    }

    .loading-container p {
      margin-top: 12px;
      color: #666;
      font-size: 13px;
    }

    .initial-analysis {
      background: #f9fafb;
      padding: 16px;
      margin-bottom: 16px;
      border-bottom: 1px solid #e8dfd9;
    }

    .initial-analysis-title {
      font-weight: 700;
      color: #333;
      margin-bottom: 4px;
      font-size: 15px;
    }

    .initial-analysis-subtitle {
      font-weight: 600;
      color: #666;
      margin-bottom: 12px;
      font-size: 13px;
    }

    .initial-analysis-content {
      color: #444;
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
    }

    .initial-analysis-content .section-header {
      font-weight: 700;
      color: #333;
    }

    .error-container {
      padding: 16px;
    }

    .loading-overlay {
      display: flex;
      justify-content: center;
      padding: 20px;
    }

    query-input {
      flex-shrink: 0;
    }

    .model-selector {
      padding: 12px 16px;
      background: white;
      border-top: 1px solid #e8dfd9;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }

    .model-label {
      font-size: 12px;
      color: #666;
      font-weight: 500;
    }

    .toggle-group {
      display: inline-flex;
      border: 1px solid #d0d0d0;
      border-radius: 4px;
      background: white;
    }

    .toggle-btn {
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 500;
      background: white;
      border: none;
      color: #666;
      cursor: pointer;
      transition: all 0.15s;
      min-width: 50px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .btn-cost {
      font-size: 10px;
      font-weight: 400;
      opacity: 0.7;
    }

    .toggle-btn:first-child {
      border-radius: 3px 0 0 3px;
    }

    .toggle-btn:last-child {
      border-radius: 0 3px 3px 0;
    }

    .toggle-btn:hover:not(.active) {
      background: #f5f5f5;
    }

    .toggle-btn.active {
      background: #3d2f2a;
      color: white;
    }

    .toggle-btn:not(:last-child) {
      border-right: 1px solid #d0d0d0;
    }

    .toggle-btn.restricted {
      opacity: 0.5;
      cursor: not-allowed;
      position: relative;
    }

    .toggle-btn.restricted:hover:not(.active) {
      background: white;
    }

    .toggle-btn.restricted:hover::after {
      content: attr(data-tooltip);
      position: absolute;
      top: calc(100% + 8px);
      left: 50%;
      transform: translateX(-50%);
      background: #333;
      color: white;
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 11px;
      white-space: nowrap;
      z-index: 100;
      pointer-events: none;
    }


    .action-buttons {
      display: flex;
      gap: 8px;
      padding: 8px 16px;
      position: sticky;
      bottom: 0;
      background: transparent;
      z-index: 10;
    }

    .jump-to-bottom-btn,
    .add-supplement-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: #f5f5f5;
      border: 1px solid #e8dfd9;
      border-radius: 6px;
      font-size: 13px;
      color: #666;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }

    .jump-to-bottom-btn:hover,
    .add-supplement-btn:hover {
      background: #e8e8e8;
      color: #333;
    }

    .add-supplement-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }


    .chat-input-section {
      flex-shrink: 0;
      background: white;
    }

    .supplemental-section {
      padding: 12px 16px;
      background: #f9fafb;
      border-bottom: 1px solid #e8dfd9;
    }

    .supplemental-heading {
      font-size: 12px;
      font-weight: 600;
      color: #666;
      margin-bottom: 8px;
    }

    .supplemental-button {
      width: 100%;
      padding: 10px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }

    .supplemental-upload-btn {
      background: #4CAF50;
      border: 1px solid #45a049;
      color: white;
    }

    .supplemental-upload-btn:hover {
      background: #45a049;
    }

    .supplemental-add-btn {
      background: #f0f0f0;
      border: 1px solid #ddd;
      color: #333;
    }

    .supplemental-add-btn:hover {
      background: #e8e8e8;
    }

    .mobile-paper-header {
      display: none; /* Hidden on desktop */
    }

    .mobile-icons {
      display: none; /* Hidden on desktop */
    }

    .mobile-paper-title {
      font-size: 14px;
      font-weight: 600;
      color: #333;
      margin: 0 0 4px 0;
      line-height: 1.3;
    }

    .mobile-paper-meta {
      font-size: 11px;
      color: #666;
      font-style: italic;
      margin: 0;
    }

    /* Mobile styles */
    @media (max-width: 768px) {
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden;
      }

      .mobile-paper-header {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 12px 16px 16px 16px;
        background: transparent;
      }

      .mobile-paper-header .paper-info {
        flex: 1;
        min-width: 0;
      }

      .mobile-icons {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-shrink: 0;
      }

      .mobile-icons a,
      .mobile-icons button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: none;
        background: none;
        color: #666;
        cursor: pointer;
        padding: 0;
        text-decoration: none;
      }

      .mobile-icons svg {
        width: 20px;
        height: 20px;
      }

      .conversation-container {
        flex: 1;
        overflow-y: auto;
        /* Account for fixed chat input at bottom: nav (44px) + safe area + input (~160px) */
        padding-bottom: calc(44px + env(safe-area-inset-bottom, 0px) + 160px + 16px);
      }

      .chat-input-section {
        /* Fixed above the bottom navigation */
        position: fixed;
        /* Nav is 44px height + safe-area padding (content-box) */
        bottom: calc(44px + env(safe-area-inset-bottom, 0px));
        left: 0;
        right: 0;
        z-index: 999; /* Just below nav (1000) but above content */
        border-top: 1px solid #e8dfd9;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
        background: white;
      }

      /* Hide desktop model selector on mobile */
      .model-selector {
        display: none;
      }

      .home-action-buttons {
        flex-direction: column;
        padding: 12px 16px;
        /* Add padding to avoid being covered by mobile-bottom-nav (44px + safe area) */
        padding-bottom: calc(12px + 44px + env(safe-area-inset-bottom, 0px));
      }

      .initial-analysis-title {
        display: none; /* Hide on mobile - title is in header */
      }
    }

    /* Insufficient Credits Modal */
    .modal-overlay {
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

    .modal-content {
      background: white;
      padding: 24px;
      border-radius: 12px;
      max-width: 400px;
      width: 90%;
      text-align: center;
    }

    .modal-content h3 {
      margin: 0 0 12px 0;
      color: #3d2f2a;
      font-size: 18px;
    }

    .modal-content p {
      margin: 0 0 8px 0;
      color: #666;
      font-size: 14px;
    }

    .modal-actions {
      display: flex;
      gap: 12px;
      margin-top: 20px;
      justify-content: center;
    }

    .modal-btn {
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
    }

    .modal-btn.secondary {
      background: #f0f0f0;
      color: #666;
    }

    .modal-btn.secondary:hover {
      background: #e5e5e5;
    }

    .modal-btn.primary {
      background: #c45d3a;
      color: white;
    }

    .modal-btn.primary:hover {
      background: #a84d2f;
    }
  `;

  private handleSubModelChange(model: ModelType) {
    // Check if user has access to the model
    if (model === 'sonnet' && !this.modelAccess.sonnet) return;
    if (model === 'gemini-pro' && !this.modelAccess.gemini_pro) return;
    this.selectedModel = model;
  }

  async handleSubmitQuery(e: CustomEvent<QueryRequest>) {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      // Add model parameter to the query request
      const queryWithModel = {
        ...e.detail,
        model: this.selectedModel
      };
      const response = await api.query(this.sessionId, queryWithModel);

      // Add user message to conversation
      const userMessage: ConversationMessage = {
        id: response.exchange_id,
        exchange_id: response.exchange_id,
        role: 'user',
        content: e.detail.query,
        highlighted_text: e.detail.highlighted_text,
        page: e.detail.page,
        timestamp: new Date().toISOString()
      };

      // Add assistant response to conversation
      // Note: Both user and assistant share the same exchange_id
      const assistantMessage: ConversationMessage = {
        id: response.exchange_id,
        exchange_id: response.exchange_id,
        role: 'assistant',
        content: response.response,
        model: response.model_used,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, userMessage, assistantMessage];

      // Notify parent of conversation update
      this.dispatchEvent(
        new CustomEvent('conversation-updated', {
          detail: { conversation: this.conversation },
          bubbles: true,
          composed: true
        })
      );

      // Scroll to bottom after update
      await this.updateComplete;
      this.scrollToBottom();
    } catch (err) {
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to send query. Please try again.';
      }
      console.error('Query error:', err);
    } finally {
      this.loading = false;
    }
  }

  updated(changedProperties: Map<string, unknown>) {
    // If model access changes and current model is no longer accessible, fallback
    if (changedProperties.has('modelAccess')) {
      if (this.selectedModel === 'sonnet' && !this.modelAccess.sonnet) {
        this.selectedModel = 'haiku';
      } else if (this.selectedModel === 'gemini-pro' && !this.modelAccess.gemini_pro) {
        this.selectedModel = 'gemini-flash';
      }
    }

    // Check for supplements when zoteroKey is set
    if (changedProperties.has('zoteroKey') && this.zoteroKey) {
      this.checkSupplementsAvailable();
    }

    // Reset initial load flag when session changes
    if (changedProperties.has('sessionId')) {
      this.initialLoadComplete = false;
      if (!this.sessionId) {
        this.loadAllSessions();
      }
    }

    // Load evaluations when conversation changes
    if (changedProperties.has('conversation') && this.conversation.length > 0 && this.sessionId) {
      this.loadEvaluations();
    }

    // Track initial load - but don't auto-scroll to bottom on mobile
    // Users can use the "Jump to bottom" button if needed
    // Explicit scrollToBottom() calls handle scrolling after user actions (sending messages, etc.)
    if (changedProperties.has('conversation') && this.conversation.length > 0) {
      if (!this.initialLoadComplete) {
        // Mark initial load as complete after first conversation render
        this.initialLoadComplete = true;
      }
    }
  }

  private async loadAllSessions() {
    this.loadingSessions = true;
    try {
      // Load all sessions (limit 100 for now)
      this.allSessions = await api.listSessions(100, 0);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      this.loadingSessions = false;
    }
  }

  private handleSessionClick(session: Session) {
    this.dispatchEvent(
      new CustomEvent('session-selected', {
        detail: { session },
        bubbles: true,
        composed: true
      })
    );
  }

  private async handleDeleteClick(session: Session, e: Event) {
    e.stopPropagation();

    const title = session.title || session.filename;
    if (!confirm(`Delete session for "${title}"? This cannot be undone.`)) {
      return;
    }

    this.deletingId = session.session_id;

    try {
      await api.deleteSession(session.session_id);
      this.allSessions = this.allSessions.filter((s) => s.session_id !== session.session_id);
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Failed to delete session');
    } finally {
      this.deletingId = undefined;
    }
  }

  private formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  }

  /**
   * Format authors, journal, and year for display.
   * Handles both JSON array format and semicolon-separated format.
   */
  private formatAuthorsWithYear(authors: string, year?: string): string {
    if (!authors) return '';

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

    if (authorList.length === 0) return '';

    // Extract last names
    const lastNames = authorList.map(a => a.split(',')[0].trim());

    let authorText = '';
    if (lastNames.length === 1) {
      authorText = lastNames[0];
    } else if (lastNames.length === 2) {
      authorText = `${lastNames[0]} & ${lastNames[1]}`;
    } else if (lastNames.length <= 6) {
      authorText = lastNames.join(', ');
    } else {
      const firstThree = lastNames.slice(0, 3).join(', ');
      const lastThree = lastNames.slice(-3).join(', ');
      authorText = `${firstThree}...${lastThree}`;
    }

    // Add journal if available (prefer abbreviation from Zotero)
    const journal = this.paperJournalAbbr || this.abbreviateJournal(this.paperJournal);
    if (journal) {
      authorText += `, ${journal}`;
    }

    // Add year if available
    if (year) {
      return `${authorText}, ${year}`;
    }
    return authorText;
  }

  /**
   * Abbreviate journal name for display.
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
      const words = journal.split(' ');
      if (words.length > 3) {
        return words.slice(0, 3).join(' ') + '.';
      }
    }

    return journal;
  }

  private async checkSupplementsAvailable() {
    if (!this.zoteroKey) {
      this.supplementCount = null;
      return;
    }

    try {
      const attachments = await api.getPaperAttachments(this.zoteroKey);
      this.supplementCount = attachments.length;
      // Pre-cache the attachments so we don't need to fetch again when opening picker
      if (attachments.length > 0) {
        this.supplementAttachments = attachments;
      }
    } catch (err) {
      // If we can't fetch, just don't show count
      this.supplementCount = null;
      console.error('Failed to check supplements:', err);
    }
  }

  private async handleShowSupplementPicker() {
    if (!this.zoteroKey) {
      // If no Zotero key, we could implement file upload here
      this.error = 'Upload supplement feature coming soon';
      return;
    }

    // If we don't have attachments cached or count is 0, try to fetch
    if (!this.supplementAttachments.length || this.supplementCount === 0) {
      this.loadingSupplements = true;
      try {
        const attachments = await api.getPaperAttachments(this.zoteroKey);
        if (attachments.length === 0) {
          this.error = 'No supplemental files found for this paper';
          this.loadingSupplements = false;
          return;
        }
        this.supplementAttachments = attachments;
        this.supplementCount = attachments.length;
      } catch (err) {
        if (err instanceof ApiError) {
          this.error = `Failed to load supplements: ${err.message}`;
        } else {
          this.error = 'Failed to load supplements';
        }
        this.loadingSupplements = false;
        return;
      } finally {
        this.loadingSupplements = false;
      }
    }

    // Show picker with cached attachments
    this.showSupplementPicker = true;
  }

  private handleCloseSupplementPicker() {
    this.showSupplementPicker = false;
  }

  private async handleSupplementUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file || !this.sessionId || !this.zoteroKey) {
      return;
    }

    this.loadingSupplements = true;
    this.error = '';

    try {
      // Upload supplement to backend (which will add it to Zotero)
      await api.uploadSupplement(this.sessionId, this.zoteroKey, file);

      // Refresh the supplement count and list
      await this.checkSupplementsAvailable();

      // Show success message (system message, not a real exchange)
      const successMessage: ConversationMessage = {
        id: this.conversation.length,
        exchange_id: -1,  // System message, not deletable
        role: 'user',
        content: `📎 **Supplement Uploaded**: "${file.name}" has been added to your Zotero library and is now available for reference.`,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, successMessage];

      // Notify parent
      this.dispatchEvent(
        new CustomEvent('conversation-updated', {
          detail: { conversation: this.conversation },
          bubbles: true,
          composed: true
        })
      );
    } catch (err) {
      if (err instanceof ApiError) {
        this.error = `Failed to upload supplement: ${err.message}`;
      } else {
        this.error = 'Failed to upload supplement. Please try again.';
      }
      console.error('Upload error:', err);
    } finally {
      this.loadingSupplements = false;
      // Clear the input so the same file can be uploaded again if needed
      input.value = '';
    }
  }

  private async handleSupplementSelected(e: CustomEvent<{ session: any; paper: ZoteroItem }>) {
    if (!this.sessionId) return;

    const { paper } = e.detail;
    this.showSupplementPicker = false;
    this.loadingSupplements = true;
    this.error = '';

    try {
      // Load supplement text from backend
      const supplement = await api.loadSupplement(this.sessionId, paper.key);

      // Add system message about loaded supplement (system message, not a real exchange)
      const supplementMessage: ConversationMessage = {
        id: this.conversation.length,
        exchange_id: -1,  // System message, not deletable
        role: 'user',
        content: `📎 **Supplement Loaded**: "${supplement.title}" (${supplement.authors || 'Unknown'}, ${supplement.year || 'N/A'})\n\nYou can now reference this supplement in your questions.`,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, supplementMessage];

      // Add the supplement text as a system message that Claude can see
      const supplementContextMessage: ConversationMessage = {
        id: this.conversation.length + 1,
        exchange_id: -1,  // System message, not deletable
        role: 'assistant',
        content: `[Supplement loaded: "${supplement.title}"\n\n${supplement.supplement_text.substring(0, 3000)}${supplement.supplement_text.length > 3000 ? '...' : ''}]`,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, supplementContextMessage];

      // Notify parent of conversation update
      this.dispatchEvent(
        new CustomEvent('conversation-updated', {
          detail: { conversation: this.conversation },
          bubbles: true,
          composed: true
        })
      );

      // Scroll to bottom after update
      await this.updateComplete;
      this.scrollToBottom();
    } catch (err) {
      if (err instanceof ApiError) {
        this.error = `Failed to load supplement: ${err.message}`;
      } else {
        this.error = 'Failed to load supplement. Please try again.';
      }
      console.error('Supplement loading error:', err);
    } finally {
      this.loadingSupplements = false;
    }
  }

  async handleFlagToggle(e: CustomEvent<{ exchangeId: number }>) {
    if (!this.sessionId) return;

    const { exchangeId } = e.detail;
    const isFlagged = this.flags.includes(exchangeId);

    // Update UI immediately (optimistic update)
    if (isFlagged) {
      this.flags = this.flags.filter((id) => id !== exchangeId);
    } else {
      this.flags = [...this.flags, exchangeId];
    }

    // Notify parent of flags update
    this.dispatchEvent(
      new CustomEvent('flags-updated', {
        detail: { flags: this.flags },
        bubbles: true,
        composed: true
      })
    );

    this.requestUpdate();

    // Then sync with backend (don't block UI on this)
    try {
      if (isFlagged) {
        await api.unflag(this.sessionId, exchangeId);
      } else {
        await api.toggleFlag(this.sessionId, exchangeId);
      }
    } catch (err) {
      console.error('Flag toggle error:', err);
      // Note: We keep the optimistic UI update even if API fails
    }
  }

  async handleEvaluateMessage(e: CustomEvent) {
    if (!this.sessionId) return;

    const { exchangeId, rating, reasons, feedbackText } = e.detail;

    // Optimistic update
    const newEvaluation: MessageEvaluation = {
      rating,
      ...(reasons?.inaccurate && { reason_inaccurate: true }),
      ...(reasons?.unhelpful && { reason_unhelpful: true }),
      ...(reasons?.offTopic && { reason_off_topic: true }),
      ...(reasons?.other && { reason_other: true }),
      ...(feedbackText && { feedback_text: feedbackText })
    };

    this.evaluations.set(exchangeId, newEvaluation);
    this.requestUpdate();

    // Show brief feedback for thumbs up
    if (rating === 'positive') {
      console.log('Thanks for your feedback!'); // TODO: Add toast notification
    }

    // Save to backend
    try {
      await api.evaluateMessage(
        this.sessionId,
        exchangeId,
        rating,
        reasons,
        feedbackText
      );
    } catch (err) {
      console.error('Failed to save evaluation:', err);
      // Revert optimistic update on error
      this.evaluations.delete(exchangeId);
      this.requestUpdate();
    }
  }

  async loadEvaluations() {
    if (!this.sessionId) return;

    // Load evaluations for all assistant messages
    for (const msg of this.conversation) {
      if (msg.role === 'assistant' && msg.exchange_id > 0) {
        try {
          const evaluation = await api.getMessageEvaluation(
            this.sessionId,
            msg.exchange_id
          );
          if (evaluation) {
            this.evaluations.set(msg.exchange_id, evaluation);
          }
        } catch (err) {
          // No evaluation yet - that's ok, skip silently
        }
      }
    }
    this.requestUpdate();
  }

  async handleDeleteEvaluation(e: CustomEvent) {
    if (!this.sessionId) return;

    const { exchangeId } = e.detail;

    // Optimistic update - remove from map
    this.evaluations.delete(exchangeId);
    this.requestUpdate();

    // Delete from backend
    try {
      await api.deleteMessageEvaluation(this.sessionId, exchangeId);
    } catch (err) {
      console.error('Failed to delete evaluation:', err);
      // Could restore the evaluation here if needed
    }
  }

  async handleDeleteExchange(e: CustomEvent<{ exchangeId: number }>) {
    if (!this.sessionId) return;

    const { exchangeId } = e.detail;

    // Remove from conversation UI immediately (optimistic update)
    // Filter by exchange_id, not display id
    this.conversation = this.conversation.filter(
      (msg) => msg.exchange_id !== exchangeId
    );

    // Remove from flags if it was flagged
    if (this.flags.includes(exchangeId)) {
      this.flags = this.flags.filter((id) => id !== exchangeId);
      this.dispatchEvent(
        new CustomEvent('flags-updated', {
          detail: { flags: this.flags },
          bubbles: true,
          composed: true
        })
      );
    }

    // Notify parent to refresh conversation
    this.dispatchEvent(
      new CustomEvent('conversation-updated', {
        bubbles: true,
        composed: true
      })
    );

    this.requestUpdate();

    // Then sync with backend
    try {
      await api.deleteExchange(this.sessionId, exchangeId);
    } catch (err) {
      console.error('Delete exchange error:', err);
      this.error = err instanceof Error ? err.message : 'Failed to delete exchange';
      // Reload conversation from server on error
      this.dispatchEvent(
        new CustomEvent('reload-needed', {
          bubbles: true,
          composed: true
        })
      );
    }
  }

  handleClearSelection() {
    this.dispatchEvent(
      new CustomEvent('clear-selection', {
        bubbles: true,
        composed: true
      })
    );
  }

  private scrollToBottom() {
    if (this.conversationContainer) {
      this.conversationContainer.scrollTop = this.conversationContainer.scrollHeight;
    }
  }

  private renderConversation() {
    // Skip the initial analysis (first two messages: user prompt + assistant analysis)
    const conversationMessages = this.conversation.slice(2);

    if (conversationMessages.length === 0) {
      return html`
        <div class="empty-state">
          <h3>No questions yet</h3>
          <p>
            Type a question below, or select text in the PDF to ask about specific passages.
          </p>
        </div>
      `;
    }

    // Group messages into pairs (user question + assistant response)
    const exchanges: Array<{ user: ConversationMessage; assistant: ConversationMessage }> = [];
    for (let i = 0; i < conversationMessages.length; i += 2) {
      const userMsg = conversationMessages[i];
      const assistantMsg = conversationMessages[i + 1];
      if (userMsg && assistantMsg && userMsg.role === 'user' && assistantMsg.role === 'assistant') {
        exchanges.push({ user: userMsg, assistant: assistantMsg });
      }
    }

    return exchanges.map(
      (exchange) => html`
        <conversation-item
          .userMessage=${exchange.user}
          .assistantMessage=${exchange.assistant}
          .flagged=${this.flags.includes(exchange.assistant.exchange_id)}
          .evaluation=${this.evaluations.get(exchange.assistant.exchange_id)}
          @flag-toggle=${this.handleFlagToggle}
          @delete-exchange=${this.handleDeleteExchange}
          @evaluate-message=${this.handleEvaluateMessage}
          @delete-evaluation=${this.handleDeleteEvaluation}
        ></conversation-item>
      `
    );
  }

  private renderInitialAnalysis() {
    const initialAnalysis = this.conversation.find(
      (msg) => msg.id === 1 && msg.role === 'assistant'
    );

    if (!initialAnalysis) return '';

    let content = initialAnalysis.content;

    // Strip title if present (we display it elsewhere)
    const titleMatch = content.match(/^TITLE:\s*(.+?)(?:\n|$)/i);
    if (titleMatch) {
      content = content.substring(titleMatch[0].length).trim();
    } else {
      // Fallback: check for markdown header format
      const headerMatch = content.match(/^#\s*(.+?)[\r\n]/);
      if (headerMatch) {
        content = content.substring(headerMatch[0].length).trim();
      }
    }

    // Parse content to make section headers bold
    const formattedContent = this.formatAnalysisContent(content);

    return html`
      <div class="initial-analysis">
        <div class="initial-analysis-subtitle">Review Summary</div>
        <div class="initial-analysis-content">${formattedContent}</div>
      </div>
    `;
  }

  private formatAnalysisContent(content: string) {
    // Split content by lines and process each line
    const lines = content.split('\n');
    const result: any[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Check for section headers like "**Core Innovation**:" or "Core Innovation:" or "• **Core Innovation**:" or "- **Core Innovation**:"
      const boldMatch = line.match(/^([•\-–—*]\s*)\*\*([^*]+)\*\*(:.*)?$/);
      const plainHeaderMatch = line.match(/^([•\-–—*]\s*)([A-Z][A-Za-z\s]+)(:)(.*)$/);

      if (boldMatch) {
        // Handle **Bold Header**: format
        const [, prefix, headerText, rest] = boldMatch;
        result.push(html`${prefix}<span class="section-header">${headerText}</span>${rest || ''}`);
      } else if (plainHeaderMatch && plainHeaderMatch[2].length < 30) {
        // Handle plain "Header:" format (only if reasonably short)
        const [, prefix, headerText, colon, rest] = plainHeaderMatch;
        result.push(html`${prefix}<span class="section-header">${headerText}</span>${colon}${rest}`);
      } else {
        result.push(line);
      }

      // Add newline between lines (except after last line)
      if (i < lines.length - 1) {
        result.push('\n');
      }
    }

    return result;
  }

  private groupSessionsByPaper(sessions: Session[]): SessionGroup[] {
    const groupMap = new Map<string, SessionGroup>();

    for (const session of sessions) {
      // Use zotero_key if available, otherwise use title, otherwise use filename
      const groupKey = session.zotero_key || session.title || session.filename;
      const displayTitle = session.title || session.filename;

      if (groupMap.has(groupKey)) {
        groupMap.get(groupKey)!.sessions.push(session);
      } else {
        groupMap.set(groupKey, {
          groupKey,
          displayTitle,
          authors: session.authors,
          sessions: [session]
        });
      }
    }

    // Convert to array and sort groups by most recent session date
    return Array.from(groupMap.values()).sort((a, b) => {
      const aDate = new Date(a.sessions[0].created_at).getTime();
      const bDate = new Date(b.sessions[0].created_at).getTime();
      return bDate - aDate;
    });
  }

  private filterSessionGroups(groups: SessionGroup[]): SessionGroup[] {
    if (!this.searchQuery.trim()) {
      return groups;
    }

    const query = this.searchQuery.toLowerCase().trim();
    return groups.filter(group => {
      // Search in title
      if (group.displayTitle.toLowerCase().includes(query)) {
        return true;
      }
      // Search in authors
      if (group.authors && group.authors.toLowerCase().includes(query)) {
        return true;
      }
      // Search in session labels
      return group.sessions.some(session =>
        session.label && session.label.toLowerCase().includes(query)
      );
    });
  }

  private toggleGroup(groupKey: string) {
    const newExpanded = new Set(this.expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
    } else {
      newExpanded.add(groupKey);
    }
    this.expandedGroups = newExpanded;
  }

  private renderGroupedSessionItem(session: Session) {
    const isDeleting = this.deletingId === session.session_id;
    return html`
      <div class="session-item" @click=${() => this.handleSessionClick(session)}>
        <div class="session-info">
          <div class="session-filename">
            ${session.label ? html`<span class="session-label-badge">${session.label}</span>` : ''}
            ${this.formatDate(session.created_at)}
          </div>
        </div>
        <button
          class="delete-btn-icon"
          @click=${(e: Event) => this.handleDeleteClick(session, e)}
          ?disabled=${isDeleting}
          title="Delete session"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;
  }

  private renderSessionGroup(group: SessionGroup) {
    const isExpanded = this.expandedGroups.has(group.groupKey);

    // For single-session groups, render inline without collapse
    if (group.sessions.length === 1) {
      const session = group.sessions[0];
      const isDeleting = this.deletingId === session.session_id;
      return html`
        <div class="session-item" @click=${() => this.handleSessionClick(session)}>
          <div class="session-info-single">
            <div class="session-filename" title="${group.displayTitle}">
              ${group.displayTitle}
            </div>
            <div class="session-date">${this.formatDate(session.created_at)}</div>
          </div>
          <button
            class="delete-btn-icon"
            @click=${(e: Event) => this.handleDeleteClick(session, e)}
            ?disabled=${isDeleting}
            title="Delete session"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;
    }

    // Multi-session group with collapsible header
    return html`
      <div class="session-group">
        <div
          class="group-header ${isExpanded ? 'expanded' : ''}"
          @click=${() => this.toggleGroup(group.groupKey)}
        >
          <svg class="expand-icon ${isExpanded ? 'expanded' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
          <div class="group-info">
            <div class="group-title" title="${group.displayTitle}">${group.displayTitle}</div>
          </div>
          <span class="group-count">${group.sessions.length} sessions</span>
        </div>
        ${isExpanded ? html`
          <div class="group-sessions">
            ${group.sessions.map(session => this.renderGroupedSessionItem(session))}
          </div>
        ` : ''}
      </div>
    `;
  }

  render() {
    if (!this.sessionId) {
      return html`
        <div class="sessions-list-container">
          <div class="sessions-header-row">
            <h3 class="sessions-header">Recent Papers</h3>
            <div style="display: flex; align-items: center; gap: 8px;">
              <button
                class="search-icon-btn"
                @click=${() => this.showSearch = !this.showSearch}
                title="Search papers"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
              </button>
              <div class="mobile-icons">
                <a href="/settings" title="Settings">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                  </svg>
                </a>
              </div>
            </div>
          </div>
          ${this.showSearch ? html`
            <div class="search-input-row">
              <input
                type="text"
                class="search-input"
                placeholder="Search by title, author, or label..."
                .value=${this.searchQuery}
                @input=${(e: Event) => this.searchQuery = (e.target as HTMLInputElement).value}
                @keydown=${(e: KeyboardEvent) => {
                  if (e.key === 'Escape') {
                    this.showSearch = false;
                    this.searchQuery = '';
                  }
                }}
              />
              <button
                class="search-close-btn"
                @click=${() => {
                  this.showSearch = false;
                  this.searchQuery = '';
                }}
                title="Close search"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          ` : ''}
          ${this.loadingSessions ? html`
            <div class="loading-container">
              <loading-spinner></loading-spinner>
              <p>Loading sessions...</p>
            </div>
          ` : this.allSessions.length > 0 ? html`
            <div class="sessions-list">
              ${(() => {
                const allGroups = this.groupSessionsByPaper(this.allSessions);
                const sessionGroups = this.filterSessionGroups(allGroups);
                const mobileLimit = 5;
                const desktopLimit = 7;

                return html`
                  ${sessionGroups.map((group, index) => {
                    // Mobile: hide groups after index 5 unless showAllMobileSessions is true
                    // Desktop: hide groups after index 7 unless showAllGroups is true
                    const hideOnMobile = !this.showAllMobileSessions && index >= mobileLimit;
                    const hideOnDesktop = !this.showAllGroups && index >= desktopLimit;

                    if (hideOnDesktop) {
                      // Completely hidden on both mobile and desktop
                      return html``;
                    } else if (hideOnMobile) {
                      // Hidden on mobile, visible on desktop
                      return html`<div class="desktop-only">${this.renderSessionGroup(group)}</div>`;
                    } else {
                      // Visible on both mobile and desktop
                      return this.renderSessionGroup(group);
                    }
                  })}

                  ${(() => {
                    // Show button if there are more groups to show on either mobile or desktop
                    const showButton = (!this.showAllMobileSessions && sessionGroups.length > mobileLimit) ||
                                      (!this.showAllGroups && sessionGroups.length > desktopLimit);

                    if (!showButton) return html``;

                    // Calculate remaining count for each screen size
                    const mobileRemaining = sessionGroups.length - mobileLimit;
                    const desktopRemaining = sessionGroups.length - desktopLimit;

                    return html`
                      <button class="see-more-btn" @click=${() => {
                        this.showAllMobileSessions = true;
                        this.showAllGroups = true;
                      }}>
                        <span class="mobile-text">See ${mobileRemaining} more ${mobileRemaining === 1 ? 'paper' : 'papers'}</span>
                        <span class="desktop-text">See ${desktopRemaining} more ${desktopRemaining === 1 ? 'paper' : 'papers'}</span>
                      </button>
                    `;
                  })()}
                `;
              })()}
              ${(() => {
                const allGroups = this.groupSessionsByPaper(this.allSessions);
                const sessionGroups = this.filterSessionGroups(allGroups);
                if (this.searchQuery && sessionGroups.length === 0) {
                  return html`
                    <div class="no-sessions">
                      <p>No papers found</p>
                      <p style="font-size: 13px; color: #999;">Try a different search term</p>
                    </div>
                  `;
                }
                return '';
              })()}
            </div>
          ` : html`
            <div class="no-sessions">
              <p>No previous sessions yet</p>
              <p style="font-size: 13px; color: #999;">Upload a PDF to get started</p>
            </div>
          `}
        </div>

        <!-- Action buttons - fixed at bottom -->
        <div class="home-action-buttons">
          <label class="upload-pdf-btn">
            Upload PDF
            <input
              type="file"
              accept=".pdf"
              @change=${(e: Event) => {
                this.dispatchEvent(
                  new CustomEvent('upload-pdf', {
                    detail: { event: e },
                    bubbles: true,
                    composed: true
                  })
                );
              }}
            />
          </label>

          <button
            class="load-zotero-btn"
            @click=${() => {
              if (this.zoteroConfigured) {
                this.dispatchEvent(
                  new CustomEvent('zotero-picker-open', {
                    bubbles: true,
                    composed: true
                  })
                );
              } else {
                window.location.href = '/settings#zotero';
              }
            }}
          >
            ${this.zoteroConfigured ? 'Load from Zotero' : 'Set up Zotero'}
          </button>
        </div>

      `;
    }

    return html`
      <!-- Conversation Container -->
      <div class="conversation-container chat-history">
        <!-- Mobile paper header (shown only on mobile, scrolls with content) -->
        ${this.paperTitle || this.filename
          ? html`
              <div class="mobile-paper-header">
                <div class="paper-info">
                  ${this.paperTitle
                    ? html`
                        <div class="mobile-paper-title">${this.paperTitle}</div>
                        ${this.paperAuthors
                          ? html`<div class="mobile-paper-meta">${this.formatAuthorsWithYear(this.paperAuthors, this.paperYear)}</div>`
                          : ''}
                      `
                    : this.filename
                    ? html`<div class="mobile-paper-title">${this.filename}</div>`
                    : ''}
                </div>
                <div class="mobile-icons">
                  <button @click=${() => this.dispatchEvent(new CustomEvent('home-click', { bubbles: true, composed: true }))} title="Home">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                      <polyline points="9 22 9 12 15 12 15 22"></polyline>
                    </svg>
                  </button>
                  <a href="/settings" title="Settings">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="3"></circle>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                  </a>
                  <button @click=${() => this.dispatchEvent(new CustomEvent('edit-metadata', { bubbles: true, composed: true }))} title="Edit Metadata">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                  </button>
                </div>
              </div>
            `
          : ''}

        ${this.renderInitialAnalysis()} ${this.renderConversation()}
        ${this.loading || this.loadingSupplements
          ? html`
              <div class="loading-overlay">
                <loading-spinner message="${this.loadingSupplements ? 'Loading supplement...' : 'Thinking...'}"></loading-spinner>
              </div>
            `
          : ''}
        ${this.error
          ? html`
              <div class="error-container">
                <error-message
                  .message=${this.error}
                  dismissible
                  @dismiss=${() => (this.error = '')}
                ></error-message>
              </div>
            `
          : ''}
        <!-- Action Buttons (inside conversation container for sticky positioning) -->
        ${this.sessionId && this.conversation.length > 0
          ? html`
              <div class="action-buttons">
                <button
                  class="jump-to-bottom-btn"
                  @click=${this.scrollToBottom}
                  title="Jump to bottom"
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" style="stroke: currentColor; fill: none; stroke-width: 2;">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                  Jump to Bottom
                </button>

                <button
                  class="add-supplement-btn"
                  @click=${this.zoteroKey && this.supplementCount === 0
                    ? () => {
                        const input = this.shadowRoot?.getElementById('supplement-upload') as HTMLInputElement;
                        input?.click();
                      }
                    : this.handleShowSupplementPicker}
                  ?disabled=${!this.sessionId || this.loading || this.loadingSupplements}
                  title="Add supplemental PDF"
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" style="stroke: currentColor; fill: none; stroke-width: 2;">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                  </svg>
                  ${this.zoteroKey && this.supplementCount === 0
                    ? 'Upload Supplement'
                    : this.zoteroKey
                      ? this.supplementCount === null
                        ? 'Add Supplement...'
                        : `Add Supplement (${this.supplementCount})`
                      : 'Upload Supplement'}
                </button>
              </div>
            `
          : ''}
      </div>

      <!-- Hidden file input for supplement upload -->
      <input
        type="file"
        accept="application/pdf"
        style="display: none;"
        id="supplement-upload"
        @change=${this.handleSupplementUpload}
      />

      <!-- Chat Input Section (Sticky on mobile) -->
      <div class="chat-input-section">
        <!-- Desktop model selector (hidden on mobile) -->
        <div class="model-selector">
          <span class="model-label">Claude:</span>
          <div class="toggle-group">
            <button
              class="toggle-btn ${this.selectedModel === 'sonnet' ? 'active' : ''} ${!this.modelAccess.sonnet ? 'restricted' : ''}"
              @click=${() => this.modelAccess.sonnet && this.handleSubModelChange('sonnet')}
              data-tooltip="Only Pro/Max"
              ?disabled=${!this.modelAccess.sonnet}
            >
              Sonnet <span class="btn-cost">8</span>
            </button>
            <button
              class="toggle-btn ${this.selectedModel === 'haiku' ? 'active' : ''}"
              @click=${() => this.handleSubModelChange('haiku')}
            >
              Haiku <span class="btn-cost">2</span>
            </button>
          </div>
          ${this.geminiAvailable ? html`
            <span class="model-label">Gemini:</span>
            <div class="toggle-group">
              <button
                class="toggle-btn ${this.selectedModel === 'gemini-pro' ? 'active' : ''} ${!this.modelAccess.gemini_pro ? 'restricted' : ''}"
                @click=${() => this.modelAccess.gemini_pro && this.handleSubModelChange('gemini-pro')}
                data-tooltip="Only Pro/Max"
                ?disabled=${!this.modelAccess.gemini_pro}
              >
                Pro <span class="btn-cost">4</span>
              </button>
              <button
                class="toggle-btn ${this.selectedModel === 'gemini-flash' ? 'active' : ''}"
                @click=${() => this.handleSubModelChange('gemini-flash')}
              >
                Flash <span class="btn-cost">1</span>
              </button>
            </div>
          ` : ''}
        </div>

        <query-input
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          .selectedModel=${this.selectedModel}
          .geminiAvailable=${this.geminiAvailable}
          .modelAccess=${this.modelAccess}
          .loading=${this.loading}
          @submit-query=${this.handleSubmitQuery}
          @clear-selection=${this.handleClearSelection}
          @model-change=${(e: CustomEvent) => this.handleSubModelChange(e.detail.model)}
        ></query-input>
      </div>

      <!-- Zotero Picker Modal -->
      <zotero-picker
        .visible=${this.showSupplementPicker}
        .preFilteredItems=${this.supplementAttachments}
        .mode=${'supplements'}
        @zotero-paper-selected=${this.handleSupplementSelected}
        @close=${this.handleCloseSupplementPicker}
      ></zotero-picker>

      <!-- Insufficient Credits Modal -->
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ask-tab': AskTab;
  }
}
