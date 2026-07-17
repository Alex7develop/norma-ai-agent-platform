import { useCallback, useEffect, useState } from "react";
import { AlertCircle, LoaderCircle, X } from "lucide-react";

import { AuthScreen } from "./components/AuthScreen";
import {
  ChatWorkspace,
  type ChatMessage,
} from "./components/ChatWorkspace";
import { KnowledgePanel } from "./components/KnowledgePanel";
import { Sidebar } from "./components/Sidebar";
import {
  ApiError,
  askAssistant,
  type AuthSession,
  deleteDocument,
  getSession,
  listConversationMessages,
  listConversations,
  listDocuments,
  type KnowledgeDocument,
  logout,
  runLaunchStrategy,
  uploadDocument,
  type WorkflowRun,
} from "./lib/api";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

export function App() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [booting, setBooting] = useState(true);
  const [documentCache, setDocumentCache] = useState<{
    workspaceId: string | null;
    documents: KnowledgeDocument[];
  }>({ workspaceId: null, documents: [] });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [launchRunning, setLaunchRunning] = useState(false);
  const [launchRun, setLaunchRun] = useState<WorkflowRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const workspace = session?.workspaces[0] ?? null;
  const workspaceId = workspace?.id ?? null;
  const documents =
    documentCache.workspaceId === workspaceId ? documentCache.documents : [];
  const loadingDocuments =
    Boolean(workspaceId) && documentCache.workspaceId !== workspaceId;

  useEffect(() => {
    let active = true;
    getSession()
      .then((result) => {
        if (active) setSession(result);
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

  const refreshDocuments = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const result = await listDocuments(workspaceId);
      setDocumentCache({ workspaceId, documents: result });
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }, [workspaceId]);

  useEffect(() => {
    if (!workspaceId) {
      return;
    }
    let active = true;
    void listDocuments(workspaceId)
      .then((result) => {
        if (active) setDocumentCache({ workspaceId, documents: result });
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(errorMessage(requestError));
        setDocumentCache({ workspaceId, documents: [] });
      });

    void listConversations(workspaceId)
      .then(async (conversations) => {
        if (!active || conversations.length === 0) {
          if (active) {
            setConversationId(null);
            setMessages([]);
          }
          return;
        }
        const latest = conversations[0];
        const history = await listConversationMessages(workspaceId, latest.id);
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

    return () => {
      active = false;
    };
  }, [workspaceId]);

  async function handleUpload(file: File) {
    if (!workspaceId) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(workspaceId, file);
      await refreshDocuments();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId: string) {
    if (!workspaceId) return;
    const snapshot = documentCache;
    setDocumentCache({
      workspaceId,
      documents: documents.filter((document) => document.id !== documentId),
    });
    try {
      await deleteDocument(workspaceId, documentId);
    } catch (requestError) {
      setDocumentCache(snapshot);
      setError(errorMessage(requestError));
    }
  }

  async function handleSend(question: string) {
    if (!workspaceId) return;
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
        workspaceId,
        question,
        conversationId,
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

  async function handleLaunchStrategy(brief: string, productName?: string) {
    if (!workspaceId) return;
    setLaunchRunning(true);
    setError(null);
    try {
      const result = await runLaunchStrategy({
        workspaceId,
        brief,
        productName,
      });
      setLaunchRun(result);
      await refreshDocuments();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLaunchRunning(false);
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // Clear local session even if the revoke request fails.
    }
    setSession(null);
    setDocumentCache({ workspaceId: null, documents: [] });
    setMessages([]);
    setConversationId(null);
    setLaunchRun(null);
  }

  if (booting) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#080c14] text-slate-500">
        <LoaderCircle className="size-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!session || !workspace) {
    return (
      <AuthScreen
        onAuthenticated={(next) => {
          setSession(next);
          setMessages([]);
          setConversationId(null);
          setError(null);
        }}
      />
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#080c14] text-slate-200">
      <Sidebar
        user={session.user}
        workspace={workspace}
        onLogout={() => void handleLogout()}
      />
      <ChatWorkspace
        messages={messages}
        thinking={thinking}
        documentsCount={documents.length}
        launchRunning={launchRunning}
        launchRun={launchRun}
        onSend={handleSend}
        onLaunchStrategy={handleLaunchStrategy}
      />
      <KnowledgePanel
        documents={documents}
        loading={loadingDocuments}
        uploading={uploading}
        onUpload={handleUpload}
        onDelete={handleDelete}
      />
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
