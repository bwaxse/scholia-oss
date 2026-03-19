import type { Session, SessionFull, ZoteroItem, DuplicateCheckResponse, MessageEvaluation } from '../types/session';
import { authService } from './auth';
import type { QueryRequest, QueryResponse } from '../types/query';
import type { OutlineItem } from '../types/pdf';
import type {
  NotionProjectList,
  NotionProjectContext,
  NotionRelevanceResponse,
  NotionContentResponse,
  NotionExportResponse
} from '../types/notion';
import type {
  Metadata,
  MetadataLookupRequest,
  MetadataUpdateRequest,
  MetadataUpdateResponse
} from '../types/metadata';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseUrl = '';

  /**
   * Fetch wrapper that intercepts 403 responses for deleted/suspended accounts
   * and forces logout + redirect before the caller can handle the error.
   */
  private async _fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const response = await fetch(input as RequestInfo, init);
    if (response.status === 403) {
      try {
        const body = await response.clone().json();
        const detail: string = typeof body.error?.message === 'string' ? body.error.message
          : typeof body.detail === 'string' ? body.detail : '';
        if (detail.includes('account') && (detail.includes('deleted') || detail.includes('suspended'))) {
          authService.logout();
        }
      } catch {
        // Ignore JSON parse errors — let caller handle the 403 normally
      }
    }
    return response;
  }

  /**
   * Get server configuration (capabilities)
   * Note: Zotero/Notion config is now per-user
   */
  async getServerConfig(): Promise<Record<string, never>> {
    const response = await this._fetch(`${this.baseUrl}/sessions/config`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get server config: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get application config (feature availability)
   * Note: Zotero/Notion availability is now per-user (check user settings)
   */
  async getAppConfig(): Promise<{ gemini_available: boolean }> {
    const response = await this._fetch(`${this.baseUrl}/api/config`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get app config: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Create a new session by uploading a PDF
   */
  async createSession(file: File, doi?: string, pmid?: string): Promise<Session> {
    const formData = new FormData();
    formData.append('file', file);
    if (doi) {
      formData.append('doi', doi);
    }
    if (pmid) {
      formData.append('pmid', pmid);
    }

    const response = await this._fetch(`${this.baseUrl}/sessions/new`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      let errorMessage = 'Failed to create session';
      let errorDetails: any;

      try {
        const body = await response.json();
        // Custom exception handler returns { error: { code, message, path } }
        // where message may be a string or a detail dict
        const detail = body.error?.message ?? body.detail ?? body;
        if (detail && typeof detail === 'object') {
          errorDetails = detail;
          if (detail.message) errorMessage = detail.message;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
          errorDetails = body;
        }
      } catch {
        errorMessage = `${errorMessage}: ${response.statusText}`;
      }

      throw new ApiError(errorMessage, response.status, errorDetails);
    }

    return response.json();
  }

  /**
   * Check if sessions already exist for a Zotero item
   */
  async checkZoteroSessions(zoteroKey: string): Promise<DuplicateCheckResponse> {
    const response = await this._fetch(`${this.baseUrl}/sessions/zotero/${zoteroKey}/check`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to check Zotero sessions: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Create a new session from a Zotero paper
   */
  async createSessionFromZotero(zoteroKey: string, label?: string): Promise<Session> {
    const formData = new FormData();
    formData.append('zotero_key', zoteroKey);
    if (label) {
      formData.append('label', label);
    }

    const response = await this._fetch(`${this.baseUrl}/sessions/new`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      let errorMessage = 'Failed to create session from Zotero';
      let errorDetails: any;

      try {
        const body = await response.json();
        // Custom exception handler returns { error: { code, message, path } }
        // where message may be a string or a detail dict
        const detail = body.error?.message ?? body.detail ?? body;
        if (detail && typeof detail === 'object') {
          errorDetails = detail;
          if (detail.message) errorMessage = detail.message;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
          errorDetails = body;
        }
      } catch {
        errorMessage = `${errorMessage}: ${response.statusText}`;
      }

      throw new ApiError(errorMessage, response.status, errorDetails);
    }

    return response.json();
  }

  /**
   * Get full session details including conversation history
   */
  async getSession(sessionId: string): Promise<SessionFull> {
    const response = await this._fetch(`${this.baseUrl}/sessions/${sessionId}`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get session: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Relink a session to a different Zotero item without re-running analysis
   */
  async relinkSessionZotero(sessionId: string, zoteroKey: string): Promise<{ status: string; message: string; session_id: string; zotero_key: string }> {
    const formData = new FormData();
    formData.append('zotero_key', zoteroKey);

    const response = await this._fetch(`${this.baseUrl}/sessions/${sessionId}/relink-zotero`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to relink session: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get document outline (table of contents)
   */
  async getOutline(sessionId: string): Promise<OutlineItem[]> {
    const response = await this._fetch(`${this.baseUrl}/sessions/${sessionId}/outline`);

    if (!response.ok) {
      if (response.status === 404) {
        return []; // No outline available
      }
      throw new ApiError(
        `Failed to get outline: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get extracted key concepts from the document
   */
  async getConcepts(sessionId: string, force: boolean = false, cacheOnly: boolean = false, model: string = 'gemini-flash', useThinking: boolean = false): Promise<any> {
    const params = new URLSearchParams();
    if (force) params.append('force', 'true');
    if (cacheOnly) params.append('cache_only', 'true');
    params.append('model', model);
    if (useThinking) params.append('use_thinking', 'true');

    const url = params.toString()
      ? `${this.baseUrl}/sessions/${sessionId}/concepts?${params}`
      : `${this.baseUrl}/sessions/${sessionId}/concepts`;
    const response = await this._fetch(url);

    if (!response.ok) {
      if (response.status === 404) {
        return null; // No insights available
      }
      throw new ApiError(
        `Failed to get concepts: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * List all sessions
   */
  async listSessions(limit = 50, offset = 0): Promise<Session[]> {
    const response = await this._fetch(
      `${this.baseUrl}/sessions?limit=${limit}&offset=${offset}`
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to list sessions: ${response.statusText}`,
        response.status
      );
    }

    const data = await response.json();
    // Backend returns {sessions: [...], total: n}, extract just the sessions array
    return data.sessions || [];
  }

  /**
   * Query the paper with optional highlighted text
   */
  async query(sessionId: string, request: QueryRequest): Promise<QueryResponse> {
    const response = await this._fetch(`${this.baseUrl}/sessions/${sessionId}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      let errorMessage = 'Query failed';
      let errorData: any = {};

      try {
        errorData = await response.json();
        // Handle FastAPI's nested detail object: {detail: {error, message}}
        const detail = errorData.detail;
        const detailMessage = typeof detail === 'object' ? detail?.message : detail;
        errorMessage = detailMessage || errorData.message || `Query failed: ${response.statusText || 'Unknown error'}`;
      } catch {
        // If JSON parsing fails, try to get text
        const errorText = await response.text().catch(() => '');
        errorMessage = errorText || `Query failed with status ${response.status}: ${response.statusText || 'Unknown error'}`;
      }

      throw new ApiError(
        errorMessage,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Toggle flag on an exchange
   */
  async toggleFlag(sessionId: string, exchangeId: number, note?: string): Promise<void> {
    const response = await this._fetch(
      `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/flag`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note })
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to toggle flag: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Remove flag from an exchange
   */
  async unflag(sessionId: string, exchangeId: number): Promise<void> {
    const response = await this._fetch(
      `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/flag`,
      {
        method: 'DELETE'
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to unflag: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Delete an exchange from the conversation
   */
  async deleteExchange(sessionId: string, exchangeId: number): Promise<void> {
    const response = await this._fetch(
      `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}`,
      {
        method: 'DELETE'
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to delete exchange: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await this._fetch(`${this.baseUrl}/sessions/${sessionId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to delete session: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Export session as markdown
   */
  async exportSession(sessionId: string): Promise<string> {
    const response = await this._fetch(`${this.baseUrl}/sessions/${sessionId}/export`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to export session: ${response.statusText}`,
        response.status
      );
    }

    return response.text();
  }

  /**
   * Search Zotero library
   */
  async searchZotero(query: string, limit = 20): Promise<ZoteroItem[]> {
    const response = await this._fetch(
      `${this.baseUrl}/zotero/search?query=${encodeURIComponent(query)}&limit=${limit}`
    );

    if (!response.ok) {
      throw new ApiError(
        `Zotero search failed: ${response.statusText}`,
        response.status
      );
    }

    const data = await response.json();
    // Backend returns {items: [...], total: n}
    return data.items || [];
  }

  /**
   * Get recent papers from Zotero
   */
  async getRecentPapers(limit = 20): Promise<ZoteroItem[]> {
    const response = await this._fetch(`${this.baseUrl}/zotero/recent?limit=${limit}`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get recent papers: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get attachment files linked to a Zotero paper
   */
  async getPaperAttachments(zoteroKey: string): Promise<ZoteroItem[]> {
    const response = await this._fetch(
      `${this.baseUrl}/zotero/attachments/${zoteroKey}`
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to get attachments: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Load supplement paper text for reference in conversation
   */
  async loadSupplement(sessionId: string, zoteroKey: string): Promise<any> {
    const response = await this._fetch(
      `${this.baseUrl}/zotero/load-supplement?session_id=${sessionId}&zotero_key=${zoteroKey}`,
      { method: 'POST' }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to load supplement: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Upload a supplemental PDF to Zotero
   */
  async uploadSupplement(sessionId: string, zoteroKey: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('zotero_key', zoteroKey);
    formData.append('file', file);

    const response = await this._fetch(
      `${this.baseUrl}/zotero/upload-supplement`,
      {
        method: 'POST',
        body: formData
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to upload supplement: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Save insights to Zotero as a note
   */
  async saveInsightsToZotero(sessionId: string, zoteroKey: string, tags?: string[]): Promise<any> {
    const response = await this._fetch(
      `${this.baseUrl}/zotero/save-insights`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          parent_item_key: zoteroKey,
          tags: tags || ['claude-analyzed']
        })
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to save insights to Zotero: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * List Notion projects (pages)
   */
  async listNotionProjects(query?: string): Promise<NotionProjectList> {
    let url = `${this.baseUrl}/api/notion/projects`;
    if (query) {
      url += `?query=${encodeURIComponent(query)}`;
    }

    const response = await this._fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to list Notion projects: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Get Notion project context
   */
  async getNotionProjectContext(
    pageId: string,
    forceRefresh: boolean = false
  ): Promise<NotionProjectContext> {
    let url = `${this.baseUrl}/api/notion/project/${pageId}/context`;
    if (forceRefresh) {
      url += '?force_refresh=true';
    }

    const response = await this._fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to get project context: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Generate relevance statement and theme suggestion
   */
  async generateNotionRelevance(
    sessionId: string,
    pageId: string,
    model: string = 'gemini-flash'
  ): Promise<NotionRelevanceResponse> {
    const url = `${this.baseUrl}/api/notion/generate-relevance?session_id=${encodeURIComponent(sessionId)}&page_id=${encodeURIComponent(pageId)}&model=${encodeURIComponent(model)}`;

    const response = await this._fetch(url, {
      method: 'POST'
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to generate relevance: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Generate full export content for Notion
   */
  async generateNotionContent(
    sessionId: string,
    pageId: string,
    theme: string,
    relevance: string,
    includeSessionNotes: boolean = true,
    model: string = 'gemini-flash'
  ): Promise<NotionContentResponse> {
    const params = new URLSearchParams({
      session_id: sessionId,
      page_id: pageId,
      theme: theme,
      relevance: relevance,
      include_session_notes: includeSessionNotes.toString(),
      model: model
    });
    const url = `${this.baseUrl}/api/notion/generate-content?${params.toString()}`;

    const response = await this._fetch(url, {
      method: 'POST'
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to generate content: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Export to Notion
   */
  async exportToNotion(
    sessionId: string,
    pageId: string,
    theme: string,
    content: string,
    literatureReviewHeading: string = 'Literature Review'
  ): Promise<NotionExportResponse> {
    const url = `${this.baseUrl}/api/notion/export`;

    const response = await this._fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: sessionId,
        page_id: pageId,
        theme: theme,
        content: content,
        literature_review_heading: literatureReviewHeading
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to export to Notion: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Look up metadata by DOI or PMID
   */
  async lookupMetadata(request: MetadataLookupRequest): Promise<Metadata> {
    const url = `${this.baseUrl}/metadata/lookup`;

    const response = await this._fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to lookup metadata: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Get metadata for a session
   */
  async getMetadata(sessionId: string): Promise<Metadata> {
    const url = `${this.baseUrl}/metadata/${sessionId}`;

    const response = await this._fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to get metadata: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Update metadata for a session
   */
  async updateMetadata(sessionId: string, request: MetadataUpdateRequest): Promise<MetadataUpdateResponse> {
    const url = `${this.baseUrl}/metadata/${sessionId}`;

    const response = await this._fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to update metadata: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Evaluate a message with thumbs up/down feedback
   */
  async evaluateMessage(
    sessionId: string,
    exchangeId: number,
    rating: 'positive' | 'negative',
    reasons?: {
      inaccurate?: boolean;
      unhelpful?: boolean;
      offTopic?: boolean;
      other?: boolean;
    },
    feedbackText?: string
  ): Promise<void> {
    const url = `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/evaluate`;

    const response = await this._fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        rating,
        reason_inaccurate: reasons?.inaccurate || false,
        reason_unhelpful: reasons?.unhelpful || false,
        reason_off_topic: reasons?.offTopic || false,
        reason_other: reasons?.other || false,
        feedback_text: feedbackText
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to evaluate message: ${response.statusText}`,
        response.status,
        errorData
      );
    }
  }

  /**
   * Get existing evaluation for a message
   */
  async getMessageEvaluation(
    sessionId: string,
    exchangeId: number
  ): Promise<MessageEvaluation | null> {
    const url = `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/evaluation`;

    const response = await this._fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to get evaluation: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    const data = await response.json();
    return Object.keys(data).length > 0 ? data : null;
  }

  /**
   * Delete a message evaluation (toggle off rating)
   */
  async deleteMessageEvaluation(
    sessionId: string,
    exchangeId: number
  ): Promise<void> {
    const url = `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/evaluation`;

    const response = await this._fetch(url, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Failed to delete evaluation: ${response.statusText}`,
        response.status,
        errorData
      );
    }
  }

  /**
   * Generic GET request helper
   */
  async get(path: string): Promise<any> {
    const url = `${this.baseUrl}${path}`;
    const response = await this._fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || errorData.message || `Request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Generic POST request helper
   */
  async post(path: string, body?: any): Promise<any> {
    const url = `${this.baseUrl}${path}`;
    const response = await this._fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || errorData.message || `Request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }
}

// Export singleton instance
export const api = new ApiClient();
