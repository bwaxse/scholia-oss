export type ModelType = 'sonnet' | 'haiku' | 'gemini-flash' | 'gemini-pro';

export interface QueryRequest {
  query: string;
  highlighted_text?: string;
  page?: number;
  model?: ModelType;
  use_thinking?: boolean;
}

export interface QueryResponse {
  exchange_id: number;
  response: string;
  model_used: string;
  use_thinking?: boolean;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    thinking_tokens?: number;
  };
}

export interface LinkedInPostEndings {
  question: string;
  declarative: string;
  forward_looking: string;
}

export interface LinkedInPostResponse {
  hook: string;
  body: string;
  endings: LinkedInPostEndings;
  full_post_options: string[];
}
