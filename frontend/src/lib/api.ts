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

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? message;
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
