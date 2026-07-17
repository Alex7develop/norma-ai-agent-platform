const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export interface KnowledgeDocument {
  id: string;
  workspace_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface AssistantSource {
  citation: number;
  document_id: string | null;
  filename: string | null;
  chunk_index: number | null;
  score: number;
}

export interface AssistantAnswer {
  answer: string;
  sources: AssistantSource[];
  model: string;
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
}

export interface AuthWorkspace {
  id: string;
  name: string;
  role: string;
}

export interface AuthSession {
  user: AuthUser;
  workspaces: AuthWorkspace[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function parseDetail(payload: { detail?: unknown }): string {
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
    return String(payload.detail[0].msg);
  }
  return "Request failed";
}

async function request<T>(
  path: string,
  init?: RequestInit,
  retry = true,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: init?.headers,
  });

  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    const refreshed = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (refreshed.ok) {
      return request<T>(path, init, false);
    }
  }

  if (!response.ok) {
    let message = "Request failed";
    try {
      message = parseDetail((await response.json()) as { detail?: unknown });
    } catch {
      // The backend may return an empty or non-JSON infrastructure response.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function register(payload: {
  email: string;
  password: string;
  display_name: string;
  workspace_name: string;
}): Promise<AuthSession> {
  return request("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function login(payload: {
  email: string;
  password: string;
}): Promise<AuthSession> {
  return request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function logout(): Promise<void> {
  return request("/auth/logout", { method: "POST" });
}

export function getSession(): Promise<AuthSession> {
  return request("/auth/me");
}

export function listDocuments(
  workspaceId: string,
): Promise<KnowledgeDocument[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/knowledge/documents?${query}`);
}

export function uploadDocument(
  workspaceId: string,
  file: File,
): Promise<KnowledgeDocument> {
  const body = new FormData();
  body.append("workspace_id", workspaceId);
  body.append("file", file);
  return request("/knowledge/documents", { method: "POST", body });
}

export function deleteDocument(
  workspaceId: string,
  documentId: string,
): Promise<void> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/knowledge/documents/${documentId}?${query}`, {
    method: "DELETE",
  });
}

export function askAssistant(
  workspaceId: string,
  question: string,
): Promise<AssistantAnswer> {
  return request("/assistant/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: workspaceId, question }),
  });
}
