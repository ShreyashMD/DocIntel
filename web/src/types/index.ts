export type Role = "superadmin" | "org_admin" | "manager" | "user" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  org_id: string | null;
  role: Role;
  active: boolean;
  created_at: string;
  last_login?: string | null;
}

export interface Org {
  id: string;
  name: string;
  slug: string;
  plan: string;
  active: boolean;
  llm_provider?: string;
  embedding_provider?: string | null;
  ollama_url?: string;
  pipeline_mode?: string;
  // Per-provider key status
  has_openai_key?: boolean;
  has_gemini_key?: boolean;
  has_anthropic_key?: boolean;
  has_nvidia_key?: boolean;
  // Legacy
  has_llm_key?: boolean;
  has_embedding_key?: boolean;
  created_at: string;
}

export interface Invitation {
  id: string;
  email: string;
  role: Role;
  expires_at: string;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  file_path: string;
  collection_id: string;
  status: "pending" | "ingesting" | "ready" | "failed";
  chunk_count: number;
  file_size?: number;
  created_at: string;
}

export interface SearchResult {
  chunk: { id: string; text: string; metadata: Record<string, unknown> };
  score: number;
  document_path: string;
  tenant_id: string;
  doc_id?: string;
}

export interface QueryResult {
  question: string;
  answer: string;
  sources: SearchResult[];
  model: string;
}

export interface HistoryEntry {
  id: string;
  question: string;
  answer: string;
  sources: Array<{ document_path: string; score: number; page?: number }>;
  model?: string;
  duration_ms?: number;
  collection_id?: string;
  created_at: string;
}

export interface PlatformStats {
  orgs: number;
  users: number;
  docs: number;
  queries: number;
  runtime_metrics: Record<string, unknown>;
}

export interface OrgStats {
  users: number;
  docs: number;
  chunks: number;
  queries: number;
}
