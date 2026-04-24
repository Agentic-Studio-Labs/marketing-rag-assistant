export interface ContentItem {
  id: string;
  workspace_id?: string | null;
  title: string;
  body: string;
  summary: string;
  content_type: string;
  persona: string;
  funnel_stage: string;
  channel: string;
  topics: string;
  performance_score: number;
  url: string;
  created_at: string;
  source_path: string;
  score?: number;
}

export interface GeneratedItem {
  id: string;
  workspace_id?: string | null;
  source_content_id: string;
  source_title: string;
  format: string;
  tone: string;
  body: string;
  quality_score: number | null;
  prompts: string;
  created_at: string;
  artifact_path?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ContentStats {
  total: number;
  avg_performance: number;
  by_content_type: Record<string, number>;
  by_persona: Record<string, number>;
  by_funnel_stage: Record<string, number>;
  by_channel: Record<string, number>;
}

export interface SearchResponse {
  items: ContentItem[];
  query: string;
}

export interface RepurposeRequest {
  content_id: string;
  formats: string[];
  tone: string;
  custom_instructions?: Record<string, string>;
  save?: boolean;
}

export interface RepurposeResponse {
  success: boolean;
  generated_content: Record<string, string>;
  quality_scores: Record<string, number>;
  analysis: Record<string, string>;
  errors: string[];
  saved_ids?: Record<string, string>;
}

export interface DiscoverResponse {
  query: string;
  answer: string;
  results: ContentItem[];
  filters_applied: Record<string, string | number | boolean>;
  search_terms: string;
}

export interface AppSettings {
  anthropic_api_key_set?: boolean;
  watched_folders?: string[];
  llm_model?: string;
  embedding_model?: string;
  auth_mode?: "local" | "magic_link";
  workspace_name?: string;
  upload_mode?: "local" | "cloud";
}

export interface BackendInfo {
  mode: "local" | "cloud";
  baseUrl: string;
  authRequired: boolean;
}

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  workspace_id?: string | null;
  workspace_name?: string | null;
}

export interface SessionToken {
  token: string;
  expires_at: string;
}

export interface MagicLinkStartResponse {
  status: "sent";
  email: string;
  dev_magic_link_token?: string;
}

export interface SessionResponse {
  session: SessionToken;
  user: UserProfile;
}

export interface IntegrationState {
  id: string;
  provider: string;
  connected: boolean;
  last_checked_at?: string | null;
  last_rotated_at?: string | null;
  status_message?: string | null;
}

export interface JobArtifact {
  id: string;
  kind: string;
  path: string;
  content_type?: string | null;
  preview_text?: string | null;
}

export interface JobSummary {
  id: string;
  job_type: "repurpose" | "ingest" | "query";
  status: "queued" | "running" | "succeeded" | "failed";
  created_at: string;
  updated_at: string;
  source_content_id?: string | null;
  result_preview?: string | null;
}

export interface JobDetail extends JobSummary {
  payload: Record<string, unknown>;
  error?: string | null;
  result?: Record<string, unknown> | null;
  artifacts: JobArtifact[];
}

export interface CreateRepurposeJobRequest {
  content_id: string;
  formats: string[];
  tone: string;
  custom_instructions?: Record<string, string>;
}

export interface CreateIngestJobRequest {
  object_paths: string[];
  source_label?: string;
}

export interface UploadInitRequest {
  file_name: string;
  content_type: string;
}

export interface UploadInitResponse {
  object_path: string;
  upload_url: string;
}

export interface MeResponse {
  user: UserProfile;
}
