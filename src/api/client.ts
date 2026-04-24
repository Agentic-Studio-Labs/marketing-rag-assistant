import type {
  AppSettings,
  ContentItem,
  ContentStats,
  CreateIngestJobRequest,
  CreateRepurposeJobRequest,
  DiscoverResponse,
  GeneratedItem,
  IntegrationState,
  JobDetail,
  JobSummary,
  MagicLinkStartResponse,
  MeResponse,
  PaginatedResponse,
  RepurposeRequest,
  RepurposeResponse,
  SearchResponse,
  SessionResponse,
  UploadInitRequest,
  UploadInitResponse,
} from "./types";
import {
  clearStoredSession,
  getStoredSession,
  setStoredSession,
} from "./session";
import { API_BASE_URL, API_MODE, getBackendInfo } from "./runtime";

type QueryValue = string | number | boolean | undefined | null;

function formatHttpErrorDetail(detail: unknown, fallback: string): string {
  if (detail == null) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" &&
        item !== null &&
        "msg" in item &&
        typeof (item as { msg: unknown }).msg === "string"
          ? (item as { msg: string }).msg
          : JSON.stringify(item),
      )
      .join(" ");
  }
  if (
    typeof detail === "object" &&
    detail !== null &&
    "message" in detail &&
    typeof (detail as { message: unknown }).message === "string"
  ) {
    return (detail as { message: string }).message;
  }
  return fallback;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const session = getStoredSession();
  const headers = new Headers(options?.headers ?? {});
  headers.set("Content-Type", "application/json");

  if (session?.token) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearStoredSession();
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    const detail = (error as { detail?: unknown }).detail;
    throw new Error(
      formatHttpErrorDetail(detail, `HTTP ${res.status}: ${res.statusText}`),
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

function buildQuery(params?: Record<string, QueryValue>) {
  if (!params) return "";

  const entries = Object.entries(params)
    .filter(
      ([, value]) => value !== undefined && value !== null && value !== "",
    )
    .map(([key, value]) => [key, String(value)]);

  return entries.length > 0
    ? `?${new URLSearchParams(entries).toString()}`
    : "";
}

function toCompletedJob(result: RepurposeResponse): JobDetail {
  const firstGenerated = Object.entries(result.generated_content)[0];
  const preview = firstGenerated?.[1]?.slice(0, 200) ?? null;

  return {
    id: `local-${Date.now()}`,
    job_type: "repurpose",
    status: result.success ? "succeeded" : "failed",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    payload: {},
    error: result.errors.join(", ") || null,
    result: {
      generated_content: result.generated_content,
      quality_scores: result.quality_scores,
      analysis: result.analysis,
      saved_ids: result.saved_ids ?? {},
    },
    artifacts: Object.entries(result.generated_content).map(
      ([format, body], index) => ({
        id: `local-artifact-${index}`,
        kind: format,
        path: `memory://${format}`,
        preview_text: body.slice(0, 200),
        content_type: "text/plain",
      }),
    ),
    result_preview: preview,
  };
}

export const api = {
  backendInfo: () => getBackendInfo(),
  health: () => request<{ status: string }>("/health"),

  startMagicLink: (email: string) =>
    request<MagicLinkStartResponse>("/auth/magic-link/start", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  exchangeMagicLink: async (token: string) => {
    const response = await request<SessionResponse>(
      "/auth/magic-link/complete",
      {
        method: "POST",
        body: JSON.stringify({ token }),
      },
    );
    setStoredSession(response.session);
    return response;
  },
  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      clearStoredSession();
    }
  },
  me: () => request<MeResponse>("/me"),

  listContent: (params?: Record<string, string | number>) => {
    const query = buildQuery(params);
    return request<PaginatedResponse<ContentItem>>(`/api/content${query}`);
  },
  getContent: (id: string) => request<ContentItem>(`/api/content/${id}`),
  getSimilar: (id: string) =>
    request<ContentItem[]>(`/api/content/${id}/similar`),
  searchContent: (query: string, filters?: Record<string, string>) =>
    request<SearchResponse>("/api/content/search", {
      method: "POST",
      body: JSON.stringify({ query, filters }),
    }),
  getContentStats: () => request<ContentStats>("/api/content/stats"),

  repurpose: (req: RepurposeRequest) =>
    request<RepurposeResponse>("/api/agents/repurpose", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  discover: (query: string) =>
    request<DiscoverResponse>("/api/agents/query", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),

  createRepurposeJob: async (req: CreateRepurposeJobRequest) => {
    if (API_MODE === "local") {
      const result = await api.repurpose({ ...req, save: true });
      return toCompletedJob(result);
    }

    return request<JobDetail>("/jobs/repurpose", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },
  createIngestJob: (req: CreateIngestJobRequest) =>
    request<JobDetail>("/jobs/ingest", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  listJobs: (params?: Record<string, string | number>) => {
    const query = buildQuery(params);
    return request<PaginatedResponse<JobSummary>>(`/jobs${query}`);
  },
  getJob: (id: string) => request<JobDetail>(`/jobs/${id}`),

  listGenerated: (params?: Record<string, string | number>) => {
    const query = buildQuery(params);
    return request<PaginatedResponse<GeneratedItem>>(`/api/generated${query}`);
  },
  getGenerated: (id: string) => request<GeneratedItem>(`/api/generated/${id}`),

  ingest: (paths: string[]) =>
    request<{ ingested: number }>("/api/ingest", {
      method: "POST",
      body: JSON.stringify({ paths }),
    }),

  getSettings: () => request<AppSettings>("/api/settings"),
  updateSettings: (updates: {
    anthropic_api_key?: string;
    watched_folders?: string[];
  }) =>
    request<{ status: string }>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(updates),
    }),
  listIntegrations: () => request<IntegrationState[]>("/integrations"),
  initUpload: (req: UploadInitRequest) =>
    request<UploadInitResponse>("/uploads/init", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  uploadFile: async (file: File) => {
    const init = await api.initUpload({
      file_name: file.name,
      content_type: file.type || "application/octet-stream",
    });
    const uploadUrl = init.upload_url.startsWith("http")
      ? init.upload_url
      : `${API_BASE_URL}${init.upload_url}`;
    await fetch(uploadUrl, {
      method: "PUT",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: await file.arrayBuffer(),
    });
    return init.object_path;
  },
};
