import { useCallback, useEffect, useState } from "react";
import { AlertCircle, X } from "lucide-react";

import {
  ChatWorkspace,
  type ChatMessage,
} from "./components/ChatWorkspace";
import { KnowledgePanel } from "./components/KnowledgePanel";
import { Sidebar } from "./components/Sidebar";
import {
  ApiError,
  askAssistant,
  deleteDocument,
  listDocuments,
  type KnowledgeDocument,
  uploadDocument,
} from "./lib/api";
import { getWorkspaceId } from "./lib/workspace";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

export function App() {
  const [workspaceId] = useState(getWorkspaceId);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      setDocuments(await listDocuments(workspaceId));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoadingDocuments(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    let active = true;
    listDocuments(workspaceId)
      .then((result) => {
        if (active) setDocuments(result);
      })
      .catch((requestError: unknown) => {
        if (active) setError(errorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoadingDocuments(false);
      });
    return () => {
      active = false;
    };
  }, [workspaceId]);

  async function handleUpload(file: File) {
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
    const snapshot = documents;
    setDocuments((current) =>
      current.filter((document) => document.id !== documentId),
    );
    try {
      await deleteDocument(workspaceId, documentId);
    } catch (requestError) {
      setDocuments(snapshot);
      setError(errorMessage(requestError));
    }
  }

  async function handleSend(question: string) {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    setMessages((current) => [...current, userMessage]);
    setThinking(true);
    setError(null);

    try {
      const response = await askAssistant(workspaceId, question);
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

  return (
    <div className="flex h-screen overflow-hidden bg-[#080c14] text-slate-200">
      <Sidebar />
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
