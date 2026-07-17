const STORAGE_KEY = "norma.workspace-id";

export function getWorkspaceId(): string {
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const workspaceId = window.crypto.randomUUID();
  window.localStorage.setItem(STORAGE_KEY, workspaceId);
  return workspaceId;
}
