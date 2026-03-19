export interface Session {
  session_id: string;
  filename: string;
  created_at: string;
  initial_analysis: string;
  page_count?: number;
  zotero_key?: string;  // Zotero item key if session was loaded from Zotero
  label?: string;  // User label to distinguish multiple sessions for same paper
  title?: string;  // Paper title from metadata
  authors?: string;  // Authors from metadata
  publication_date?: string;  // Publication date from metadata
  journal?: string;  // Journal name from metadata
  journal_abbr?: string;  // Journal abbreviation from Zotero
}

export interface MessageEvaluation {
  rating: 'positive' | 'negative';
  reason_inaccurate?: boolean;
  reason_unhelpful?: boolean;
  reason_off_topic?: boolean;
  reason_other?: boolean;
  feedback_text?: string;
}

export interface ConversationMessage {
  id: number;  // Display ID (may differ from exchange_id for initial analysis)
  exchange_id: number;  // Actual database exchange_id - use this for API calls
  role: 'user' | 'assistant';
  content: string;
  highlighted_text?: string;
  page?: number;
  timestamp: string;
  model?: string;
  flagged?: boolean;
  evaluation?: MessageEvaluation;
}

export interface SessionFull extends Session {
  conversation: ConversationMessage[];
  flags: number[];
  highlights: Highlight[];
  title?: string;  // Paper title from metadata
  authors?: string;  // Authors from metadata
  publication_date?: string;  // Publication date from metadata
  journal?: string;  // Journal name from metadata
  journal_abbr?: string;  // Journal abbreviation from Zotero
}

export interface Highlight {
  id?: number;
  text: string;
  page: number;
  exchange_id?: number;
  coords?: BoundingBox;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ZoteroItem {
  key: string;
  title: string;
  authors: string;
  year?: string;
  publication?: string;
  item_type: string;
  has_pdf: boolean;
}

export interface ExistingSessionInfo {
  session_id: string;
  created_at: string;
  label?: string;
  exchange_count: number;
}

export interface DuplicateCheckResponse {
  exists: boolean;
  count: number;
  sessions: ExistingSessionInfo[];
  paper_title?: string;
}
