/**
 * TypeScript types for Notion integration.
 */

export interface NotionProject {
  id: string;
  title: string;
  url: string;
  parent?: Record<string, unknown>;
}

export interface NotionProjectList {
  projects: NotionProject[];
  total: number;
}

export interface NotionProjectContext {
  title: string;
  hypothesis: string;
  themes: string[];
  raw_content: string;
  fetched_at?: string;
}

export interface NotionRelevanceResponse {
  suggested_theme: string;
  relevance_statement: string;
  error?: string;
}

export interface NotionContentResponse {
  content: string;
}

export interface NotionExportResponse {
  success: boolean;
  page_url: string;
  message: string;
}

export interface NotionAuthResponse {
  success: boolean;
  access_token: string;
  workspace_name?: string;
  message: string;
}
