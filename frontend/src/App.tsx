import { useCallback, useEffect, useState } from "react";
import { AlertCircle, LoaderCircle, X } from "lucide-react";

import { AuthScreen } from "./components/AuthScreen";
import {
  ChatWorkspace,
  type ChatMessage,
} from "./components/ChatWorkspace";
import { KnowledgePanel } from "./components/KnowledgePanel";
import { KnowledgeWorkspace } from "./components/KnowledgeWorkspace";
import { Sidebar, type AppView } from "./components/Sidebar";
import { WorkflowsWorkspace } from "./components/WorkflowsWorkspace";
import {
  ApiError,
  askAssistant,
  type AuthSession,
  createProject,
  createSpace,
  deleteDocument,
  getDocument,
  getSession,
  getWorkflowRun,
  listConversationMessages,
  listConversations,
  listDocuments,
  listProjects,
  listWorkflowRuns,
  type KnowledgeDocument,
  type Project,
  logout,
  runLaunchStrategy,
  type WorkflowRun,
  type WorkflowRunSummary,
  uploadDocument,
} from "./lib/api";

const WORKSPACE_STORAGE_KEY = "norma.workspaceId";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

function pickWorkspaceId(session: AuthSession): string {
  const stored = localStorage.getItem(WORKSPACE_STORAGE_KEY);
  if (stored && session.workspaces.some((item) => item.id === stored)) {
    return stored;
  }
  return session.workspaces[0]?.id ?? "";
}

function isTerminalDocStatus(status: string): boolean {
  return status === "completed" || status === "failed";
}

export function App() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [booting, setBooting] = useState(true);
  const [view, setView] = useState<AppView>("assistant");
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [spaceId, setSpaceId] = useState<string | null>(null);
  const [documentCache, setDocumentCache] = useState<{
    spaceId: string | null;
    documents: KnowledgeDocument[];
  }>({ spaceId: null, documents: [] });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [enqueueing, setEnqueueing] = useState(false);
  const [launchRun, setLaunchRun] = useState<WorkflowRun | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const workspace =
    session?.workspaces.find((item) => item.id === workspaceId) ??
    session?.workspaces[0] ??
    null;
  const resolvedWorkspaceId = workspace?.id ?? null;
  const activeProject =
    projects.find((item) => item.id === projectId) ?? projects[0] ?? null;
  const activeSpace =
    activeProject?.spaces.find((item) => item.id === spaceId) ??
    activeProject?.spaces[0] ??
    null;
  const resolvedSpaceId = activeSpace?.id ?? null;
  const documents =
    documentCache.spaceId === resolvedSpaceId ? documentCache.documents : [];
  const loadingDocuments =
    Boolean(resolvedSpaceId) && documentCache.spaceId !== resolvedSpaceId;

  function resetWorkspaceScopedState() {
    setProjects([]);
    setProjectId(null);
    setSpaceId(null);
    setDocumentCache({ spaceId: null, documents: [] });
    setMessages([]);
    setConversationId(null);
    setLaunchRun(null);
    setWorkflowRuns([]);
  }

  useEffect(() => {
    let active = true;
    getSession()
      .then((result) => {
        if (!active) return;
        setSession(result);
        setWorkspaceId(pickWorkspaceId(result) || null);
      })
      .catch(() => {
        if (active) setSession(null);
      })
      .finally(() => {
        if (active) setBooting(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("notion") === "connected" || params.get("notion") === "error") {
      setView("knowledge");
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    if (!resolvedWorkspaceId || !resolvedSpaceId) return;
    try {
      const result = await listDocuments(resolvedWorkspaceId, resolvedSpaceId);
      setDocumentCache({ spaceId: resolvedSpaceId, documents: result });
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }, [resolvedWorkspaceId, resolvedSpaceId]);

  const refreshWorkflowRuns = useCallback(async () => {
    if (!resolvedWorkspaceId) return;
    try {
      const runs = await listWorkflowRuns(resolvedWorkspaceId, resolvedSpaceId);
      setWorkflowRuns(runs);
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }, [resolvedWorkspaceId, resolvedSpaceId]);

  const refreshProjects = useCallback(async () => {
    if (!resolvedWorkspaceId) return;
    const result = await listProjects(resolvedWorkspaceId);
    setProjects(result);
    return result;
  }, [resolvedWorkspaceId]);

  useEffect(() => {
    if (!resolvedWorkspaceId) return;
    let active = true;
    void listProjects(resolvedWorkspaceId)
      .then((result) => {
        if (!active) return;
        setProjects(result);
        const first = result[0];
        setProjectId(first?.id ?? null);
        setSpaceId(first?.spaces[0]?.id ?? null);
      })
      .catch((requestError: unknown) => {
        if (active) setError(errorMessage(requestError));
      });
    return () => {
      active = false;
    };
  }, [resolvedWorkspaceId]);

  useEffect(() => {
    if (!resolvedWorkspaceId || !resolvedSpaceId) return;
    let active = true;
    void listDocuments(resolvedWorkspaceId, resolvedSpaceId)
      .then((result) => {
        if (active) setDocumentCache({ spaceId: resolvedSpaceId, documents: result });
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(errorMessage(requestError));
        setDocumentCache({ spaceId: resolvedSpaceId, documents: [] });
      });

    void listConversations(resolvedWorkspaceId, resolvedSpaceId)
      .then(async (conversations) => {
        if (!active || conversations.length === 0) {
          if (active) {
            setConversationId(null);
            setMessages([]);
          }
          return;
        }
        const latest = conversations[0];
        const history = await listConversationMessages(
          resolvedWorkspaceId,
          latest.id,
        );
        if (!active) return;
        setConversationId(latest.id);
        setMessages(
          history.map((item) => ({
            id: item.id,
            role: item.role === "assistant" ? "assistant" : "user",
            content: item.content,
          })),
        );
      })
      .catch(() => {
        if (!active) return;
        setConversationId(null);
      });

    void refreshWorkflowRuns();

    return () => {
      active = false;
    };
  }, [resolvedWorkspaceId, resolvedSpaceId, refreshWorkflowRuns]);

  useEffect(() => {
    if (
      !resolvedWorkspaceId ||
      !launchRun ||
      (launchRun.status !== "pending" && launchRun.status !== "running")
    ) {
      return;
    }
    const timer = window.setInterval(() => {
      void getWorkflowRun(resolvedWorkspaceId, launchRun.id)
        .then((result) => {
          setLaunchRun(result);
          void refreshWorkflowRuns();
          if (result.status === "completed") void refreshDocuments();
        })
        .catch((requestError: unknown) => {
          setError(errorMessage(requestError));
        });
    }, 2000);
    return () => window.clearInterval(timer);
  }, [
    resolvedWorkspaceId,
    launchRun,
    refreshDocuments,
    refreshWorkflowRuns,
  ]);

  useEffect(() => {
    if (!resolvedWorkspaceId || !resolvedSpaceId) return;
    const pending = documents.filter(
      (doc) => !isTerminalDocStatus(doc.status),
    );
    if (pending.length === 0) return;
    const timer = window.setInterval(() => {
      void Promise.all(
        pending.map((doc) => getDocument(resolvedWorkspaceId, doc.id)),
      )
        .then((updated) => {
          setDocumentCache((current) => {
            if (current.spaceId !== resolvedSpaceId) return current;
            const byId = new Map(updated.map((item) => [item.id, item]));
            return {
              spaceId: resolvedSpaceId,
              documents: current.documents.map(
                (item) => byId.get(item.id) ?? item,
              ),
            };
          });
          if (updated.every((item) => isTerminalDocStatus(item.status))) {
            void refreshDocuments();
          }
        })
        .catch((requestError: unknown) => {
          setError(errorMessage(requestError));
        });
    }, 2000);
    return () => window.clearInterval(timer);
  }, [documents, resolvedWorkspaceId, resolvedSpaceId, refreshDocuments]);

  async function handleUpload(file: File) {
    if (!resolvedWorkspaceId || !resolvedSpaceId) return;
    setUploading(true);
    setError(null);
    try {
      const created = await uploadDocument(
        resolvedWorkspaceId,
        file,
        resolvedSpaceId,
      );
      setDocumentCache((current) => ({
        spaceId: resolvedSpaceId,
        documents: [
          created,
          ...(current.spaceId === resolvedSpaceId ? current.documents : []),
        ],
      }));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId: string) {
    if (!resolvedWorkspaceId || !resolvedSpaceId) return;
    const snapshot = documentCache;
    setDocumentCache({
      spaceId: resolvedSpaceId,
      documents: documents.filter((document) => document.id !== documentId),
    });
    try {
      await deleteDocument(resolvedWorkspaceId, documentId);
    } catch (requestError) {
      setDocumentCache(snapshot);
      setError(errorMessage(requestError));
    }
  }

  async function handleSend(question: string) {
    if (!resolvedWorkspaceId || !resolvedSpaceId) return;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    setMessages((current) => [...current, userMessage]);
    setThinking(true);
    setError(null);

    try {
      const response = await askAssistant(
        resolvedWorkspaceId,
        question,
        conversationId,
        resolvedSpaceId,
      );
      setConversationId(response.conversation_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          model: response.model,
        },
      ]);
    } catch (requestError) {
      const message = errorMessage(requestError);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `I couldn't complete that request. ${message}`,
        },
      ]);
      setError(message);
    } finally {
      setThinking(false);
    }
  }

  async function handleEnqueue(brief: string, productName?: string) {
    if (!resolvedWorkspaceId) return;
    setEnqueueing(true);
    setError(null);
    try {
      const result = await runLaunchStrategy({
        workspaceId: resolvedWorkspaceId,
        brief,
        productName,
        spaceId: resolvedSpaceId,
      });
      setLaunchRun(result);
      await refreshWorkflowRuns();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setEnqueueing(false);
    }
  }

  async function handleSelectRun(runId: string) {
    if (!resolvedWorkspaceId) return;
    try {
      const result = await getWorkflowRun(resolvedWorkspaceId, runId);
      setLaunchRun(result);
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  async function handleCreateProject(name: string) {
    if (!resolvedWorkspaceId) return;
    try {
      const project = await createProject(resolvedWorkspaceId, name);
      const next = await refreshProjects();
      setProjectId(project.id);
      setSpaceId(project.spaces[0]?.id ?? next?.[0]?.spaces[0]?.id ?? null);
    } catch (requestError) {
      setError(errorMessage(requestError));
      throw requestError;
    }
  }

  async function handleCreateSpace(name: string) {
    if (!resolvedWorkspaceId || !activeProject) return;
    try {
      const space = await createSpace(
        resolvedWorkspaceId,
        activeProject.id,
        name,
      );
      await refreshProjects();
      setProjectId(activeProject.id);
      setSpaceId(space.id);
    } catch (requestError) {
      setError(errorMessage(requestError));
      throw requestError;
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // Clear local session even if the revoke request fails.
    }
    localStorage.removeItem(WORKSPACE_STORAGE_KEY);
    setSession(null);
    setWorkspaceId(null);
    resetWorkspaceScopedState();
    setView("assistant");
  }

  if (booting) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#080c14] text-slate-500">
        <LoaderCircle className="size-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!session || !workspace || !resolvedWorkspaceId) {
    return (
      <AuthScreen
        onAuthenticated={(next) => {
          setSession(next);
          setWorkspaceId(pickWorkspaceId(next) || null);
          resetWorkspaceScopedState();
          setError(null);
          setView("assistant");
        }}
      />
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#080c14] text-slate-200">
      <Sidebar
        user={session.user}
        workspaces={session.workspaces}
        workspaceId={resolvedWorkspaceId}
        projects={projects}
        projectId={activeProject?.id ?? null}
        spaceId={resolvedSpaceId}
        activeView={view}
        onNavigate={setView}
        onSelectWorkspace={(id) => {
          localStorage.setItem(WORKSPACE_STORAGE_KEY, id);
          setWorkspaceId(id);
          resetWorkspaceScopedState();
        }}
        onSelectProject={(id) => {
          setProjectId(id);
          const project = projects.find((item) => item.id === id);
          setSpaceId(project?.spaces[0]?.id ?? null);
        }}
        onSelectSpace={setSpaceId}
        onCreateProject={handleCreateProject}
        onCreateSpace={handleCreateSpace}
        onLogout={() => void handleLogout()}
      />
      {view === "assistant" && (
        <>
          <ChatWorkspace
            messages={messages}
            thinking={thinking}
            documentsCount={documents.length}
            onSend={handleSend}
          />
          <KnowledgePanel
            documents={documents}
            loading={loadingDocuments}
            uploading={uploading}
            onUpload={handleUpload}
            onDelete={handleDelete}
          />
        </>
      )}
      {view === "workflows" && (
        <WorkflowsWorkspace
          runs={workflowRuns}
          activeRun={launchRun}
          enqueueing={enqueueing}
          onEnqueue={handleEnqueue}
          onSelectRun={handleSelectRun}
        />
      )}
      {view === "knowledge" && resolvedSpaceId && (
        <KnowledgeWorkspace
          workspaceId={resolvedWorkspaceId}
          spaceId={resolvedSpaceId}
          documents={documents}
          loading={loadingDocuments}
          uploading={uploading}
          onUpload={handleUpload}
          onDelete={handleDelete}
          onRefreshDocuments={refreshDocuments}
          onError={(message) => setError(message)}
        />
      )}
      {error && (
        <div className="fixed bottom-5 left-1/2 z-50 flex max-w-md -translate-x-1/2 items-center gap-3 rounded-xl border border-red-400/15 bg-[#1a1118] px-4 py-3 text-xs text-red-200 shadow-2xl shadow-black/50">
          <AlertCircle className="size-4 shrink-0 text-red-400" />
          <span>{error}</span>
          <button
            className="ml-2 text-red-400/60 hover:text-red-300"
            onClick={() => setError(null)}
          >
            <X className="size-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
