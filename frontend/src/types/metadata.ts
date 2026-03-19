/**
 * Metadata types for paper bibliographic information
 */

export interface Metadata {
  title?: string;
  authors?: string[];
  doi?: string;
  pmid?: string;
  arxiv_id?: string;
  abstract?: string;
  publication_date?: string;
  year?: string;
  journal?: string;
  journal_abbr?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  publisher?: string;
  source?: string; // crossref, pubmed, pdf_metadata, ai_pending, database
}

export interface MetadataLookupRequest {
  doi?: string;
  pmid?: string;
}

export interface MetadataUpdateRequest {
  title?: string;
  authors?: string[];
  doi?: string;
  pmid?: string;
  publication_date?: string;
  journal?: string;
  journal_abbr?: string;
  label?: string;
}

export interface MetadataUpdateResponse {
  success: boolean;
  message: string;
  metadata?: Metadata;
}
