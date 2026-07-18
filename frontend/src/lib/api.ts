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
  error?: string | null;
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
  conversation_id: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
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

export interface KnowledgeSpace {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  spaces: KnowledgeSpace[];
  created_at: string;
}

export function listProjects(workspaceId: string): Promise<Project[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/projects?${query}`);
}

export function createProject(
  workspaceId: string,
  name: string,
): Promise<Project> {
  return request("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: workspaceId, name }),
  });
}

export function createSpace(
  workspaceId: string,
  projectId: string,
  name: string,
): Promise<KnowledgeSpace> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/projects/${projectId}/spaces?${query}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function listDocuments(
  workspaceId: string,
  spaceId?: string | null,
): Promise<KnowledgeDocument[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  if (spaceId) query.set("space_id", spaceId);
  return request(`/knowledge/documents?${query}`);
}

export function getDocument(
  workspaceId: string,
  documentId: string,
): Promise<KnowledgeDocument> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/knowledge/documents/${documentId}?${query}`);
}

export interface NotionStatus {
  connected: boolean;
  workspace_name: string | null;
  workspace_id: string | null;
}

export interface NotionPage {
  id: string;
  title: string;
}

export interface NotionImportItem {
  page_id: string;
  document_id: string | null;
  filename: string | null;
  status: string;
  error: string | null;
}

export function getNotionAuthorizeUrl(
  workspaceId: string,
  spaceId: string,
): Promise<{ authorize_url: string }> {
  const query = new URLSearchParams({
    workspace_id: workspaceId,
    space_id: spaceId,
  });
  return request(`/integrations/notion/authorize?${query}`);
}

export function getNotionStatus(workspaceId: string): Promise<NotionStatus> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/integrations/notion/status?${query}`);
}

export function disconnectNotion(workspaceId: string): Promise<void> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/integrations/notion?${query}`, { method: "DELETE" });
}

export function listNotionPages(workspaceId: string): Promise<NotionPage[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/integrations/notion/pages?${query}`);
}

export function importNotionPages(payload: {
  workspaceId: string;
  spaceId: string;
  pageIds: string[];
}): Promise<{ items: NotionImportItem[] }> {
  return request("/integrations/notion/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: payload.workspaceId,
      space_id: payload.spaceId,
      page_ids: payload.pageIds,
    }),
  });
}

export function uploadDocument(
  workspaceId: string,
  file: File,
  spaceId?: string | null,
): Promise<KnowledgeDocument> {
  const body = new FormData();
  body.append("workspace_id", workspaceId);
  if (spaceId) body.append("space_id", spaceId);
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
  conversationId?: string | null,
  spaceId?: string | null,
): Promise<AssistantAnswer> {
  return request("/assistant/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: workspaceId,
      question,
      conversation_id: conversationId ?? null,
      space_id: spaceId ?? null,
    }),
  });
}

export function listConversations(
  workspaceId: string,
  spaceId?: string | null,
): Promise<ConversationSummary[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  if (spaceId) query.set("space_id", spaceId);
  return request(`/assistant/conversations?${query}`);
}

export function listConversationMessages(
  workspaceId: string,
  conversationId: string,
): Promise<ConversationMessage[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(
    `/assistant/conversations/${conversationId}/messages?${query}`,
  );
}

export interface WorkflowArtifact {
  id: string;
  kind: string;
  title: string;
  content_md: string;
  document_id: string | null;
  created_at: string;
}

export interface WorkflowRun {
  id: string;
  workspace_id: string;
  workflow_type: string;
  status: string;
  brief: string;
  product_name: string | null;
  current_step: string | null;
  error: string | null;
  model: string | null;
  pack_filename: string | null;
  document_id: string | null;
  artifacts: WorkflowArtifact[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunSummary {
  id: string;
  workspace_id: string;
  workflow_type: string;
  status: string;
  brief: string;
  product_name: string | null;
  current_step: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export function runLaunchStrategy(payload: {
  workspaceId: string;
  brief: string;
  productName?: string;
  spaceId?: string | null;
}): Promise<WorkflowRun> {
  return request("/workflows/launch-strategy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: payload.workspaceId,
      brief: payload.brief,
      product_name: payload.productName || null,
      space_id: payload.spaceId ?? null,
    }),
  });
}

export function runResearchBrief(payload: {
  workspaceId: string;
  brief: string;
  productName?: string;
  spaceId?: string | null;
}): Promise<WorkflowRun> {
  return request("/workflows/research-brief", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_id: payload.workspaceId,
      brief: payload.brief,
      product_name: payload.productName || null,
      space_id: payload.spaceId ?? null,
    }),
  });
}

export function listWorkflowRuns(
  workspaceId: string,
  spaceId?: string | null,
): Promise<WorkflowRunSummary[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  if (spaceId) query.set("space_id", spaceId);
  return request(`/workflows/runs?${query}`);
}

export function getWorkflowRun(
  workspaceId: string,
  runId: string,
): Promise<WorkflowRun> {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return request(`/workflows/runs/${runId}?${query}`);
}
