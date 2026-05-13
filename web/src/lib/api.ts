const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? "Unknown error");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function auth<T>(path: string, options: RequestInit = {}): Promise<T> {
  return request<T>(path, options, getToken() ?? undefined);
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  register(data: {
    org_name: string; org_slug: string;
    full_name: string; email: string; password: string;
  }) {
    return request<{ access_token: string; refresh_token: string; user: unknown }>(
      "/auth/register", { method: "POST", body: JSON.stringify(data) }
    );
  },

  login(email: string, password: string) {
    return request<{ access_token: string; refresh_token: string; user: unknown }>(
      "/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }
    );
  },

  refresh(refresh_token: string) {
    return request<{ access_token: string }>(
      "/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token }) }
    );
  },

  me() {
    return auth<import("@/types").User>("/auth/me");
  },

  invite(email: string, role: string) {
    return auth<{ invite_token: string }>(
      "/auth/invite", { method: "POST", body: JSON.stringify({ email, role }) }
    );
  },

  acceptInvite(token: string, full_name: string, password: string) {
    return request<{ access_token: string; refresh_token: string; user: unknown }>(
      "/auth/accept-invite",
      { method: "POST", body: JSON.stringify({ token, full_name, password }) }
    );
  },
};

// ─── Documents ────────────────────────────────────────────────────────────────

export const docApi = {
  list(collection_id?: string) {
    const q = collection_id ? `?collection_id=${collection_id}` : "";
    return auth<import("@/types").Document[]>(`/documents${q}`);
  },

  upload(file: File, collection_id = "default", summarize = false) {
    const form = new FormData();
    form.append("file", file);
    form.append("collection_id", collection_id);
    form.append("summarize", String(summarize));
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(`${BASE}/upload`, { method: "POST", headers, body: form })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(body.detail ?? "Upload failed");
        }
        return res.json() as Promise<import("@/types").Document>;
      });
  },

  ingest(path: string, tenant_id = "default", summarize = true) {
    return auth<import("@/types").Document>("/ingest", {
      method: "POST",
      body: JSON.stringify({ path, tenant_id, summarize }),
    });
  },

  delete(doc_id: string, collection_id = "default") {
    return auth<void>(`/documents/${encodeURIComponent(doc_id)}?collection_id=${collection_id}`, {
      method: "DELETE",
    });
  },

};

// ─── Query ────────────────────────────────────────────────────────────────────

export const queryApi = {
  ask(question: string, tenant_id = "default", top_k?: number, doc_ids?: string[]) {
    return auth<import("@/types").QueryResult>("/ask", {
      method: "POST",
      body: JSON.stringify({ question, tenant_id, top_k, doc_ids: doc_ids?.length ? doc_ids : undefined }),
    });
  },

  search(query: string, tenant_id = "default", top_k = 5, doc_ids?: string[]) {
    return auth<import("@/types").SearchResult[]>("/search", {
      method: "POST",
      body: JSON.stringify({ query, tenant_id, top_k, doc_ids: doc_ids?.length ? doc_ids : undefined }),
    });
  },

  history(limit = 50) {
    return auth<import("@/types").HistoryEntry[]>(`/history?limit=${limit}`);
  },
};

// ─── Org Admin ────────────────────────────────────────────────────────────────

export const adminApi = {
  users() {
    return auth<{ users: import("@/types").User[]; pending_invites: import("@/types").Invitation[] }>("/admin/users");
  },

  updateUser(user_id: string, data: { role?: string; active?: boolean }) {
    return auth<import("@/types").User>(`/admin/users/${user_id}`, {
      method: "PATCH", body: JSON.stringify(data),
    });
  },

  deactivateUser(user_id: string) {
    return auth<void>(`/admin/users/${user_id}`, { method: "DELETE" });
  },

  settings() {
    return auth<import("@/types").Org>("/admin/settings");
  },

  updateSettings(data: {
    llm_provider?: string; embedding_provider?: string; ollama_url?: string;
    pipeline_mode?: string;
    openai_api_key?: string; gemini_api_key?: string;
    anthropic_api_key?: string; nvidia_api_key?: string;
    llm_api_key?: string; embedding_api_key?: string;
  }) {
    return auth<import("@/types").Org>("/admin/settings", {
      method: "PATCH", body: JSON.stringify(data),
    });
  },

  stats() {
    return auth<import("@/types").OrgStats>("/admin/stats");
  },

  validateKey() {
    return auth<{ valid: boolean; provider: string; error: string | null }>(
      "/admin/settings/validate", { method: "POST" }
    );
  },
};

// ─── Super Admin ──────────────────────────────────────────────────────────────

export const superApi = {
  orgs() {
    return auth<import("@/types").Org[]>("/superadmin/orgs");
  },

  createOrg(data: {
    name: string; slug: string;
    admin_email: string; admin_name: string; admin_password: string;
  }) {
    return auth<{ org: import("@/types").Org; admin: import("@/types").User }>(
      "/superadmin/orgs", { method: "POST", body: JSON.stringify(data) }
    );
  },

  updateOrg(org_id: string, data: { name?: string; plan?: string; active?: boolean }) {
    return auth<import("@/types").Org>(`/superadmin/orgs/${org_id}`, {
      method: "PATCH", body: JSON.stringify(data),
    });
  },

  deleteOrg(org_id: string) {
    return auth<void>(`/superadmin/orgs/${org_id}`, { method: "DELETE" });
  },

  stats() {
    return auth<import("@/types").PlatformStats>("/superadmin/stats");
  },

  users() {
    return auth<import("@/types").User[]>("/superadmin/users");
  },

  inviteToOrg(org_id: string, email: string, role = "org_admin") {
    return auth<{ invite_token: string }>(
      `/superadmin/orgs/${org_id}/invite`,
      { method: "POST", body: JSON.stringify({ email, role }) }
    );
  },

  bootstrap(email: string, password: string, full_name = "Super Admin") {
    return request<{ message: string }>(
      "/superadmin/bootstrap",
      { method: "POST", body: JSON.stringify({ email, password, full_name }) }
    );
  },
};

// ─── Knowledge Graph ──────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  description: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  description: string;
  weight: number;
}

export interface GraphData {
  enabled: boolean;
  rag_mode: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  message?: string;
  error?: string;
}

export const graphApi = {
  get() {
    return auth<GraphData>("/graph");
  },

  rebuild(doc_ids?: string[]) {
    return auth<{ message: string }>("/graph/rebuild", {
      method: "POST",
      body: JSON.stringify({ doc_ids: doc_ids?.length ? doc_ids : null }),
    });
  },

  rebuildStatus() {
    return auth<{ running: boolean }>("/graph/rebuild/status");
  },
};

// ─── Document file URL helper ─────────────────────────────────────────────────

export function docFileUrl(doc_id: string, page?: number): string {
  const token = getToken() ?? "";
  const fragment = page ? `#page=${page}` : "";
  return `${BASE}/documents/${encodeURIComponent(doc_id)}/file?token=${encodeURIComponent(token)}${fragment}`;
}

// ─── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  check() {
    return request<{ status: string; store_backend: string }>("/health");
  },
};
