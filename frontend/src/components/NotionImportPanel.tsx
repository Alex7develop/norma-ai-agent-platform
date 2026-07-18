import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, Link2, Unlink } from "lucide-react";

import {
  disconnectNotion,
  getNotionAuthorizeUrl,
  getNotionStatus,
  importNotionPages,
  listNotionPages,
  type NotionPage,
  type NotionStatus,
} from "../lib/api";

interface NotionImportPanelProps {
  workspaceId: string;
  spaceId: string;
  onImported: () => Promise<void>;
  onError: (message: string) => void;
}

export function NotionImportPanel({
  workspaceId,
  spaceId,
  onImported,
  onError,
}: NotionImportPanelProps) {
  const [status, setStatus] = useState<NotionStatus | null>(null);
  const [pages, setPages] = useState<NotionPage[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [importing, setImporting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await getNotionStatus(workspaceId);
      setStatus(next);
      if (next.connected) {
        const listed = await listNotionPages(workspaceId);
        setPages(listed);
      } else {
        setPages([]);
        setSelected(new Set());
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : "Notion status failed");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, onError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const notion = params.get("notion");
    if (!notion) return;
    params.delete("notion");
    params.delete("detail");
    const next = params.toString();
    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${next ? `?${next}` : ""}`,
    );
    if (notion === "connected") {
      void refresh();
    } else if (notion === "error") {
      onError("Notion connection failed. Try again.");
    }
  }, [refresh, onError]);

  async function handleConnect() {
    setConnecting(true);
    try {
      const { authorize_url } = await getNotionAuthorizeUrl(workspaceId, spaceId);
      window.location.href = authorize_url;
    } catch (error) {
      onError(error instanceof Error ? error.message : "Failed to start Notion OAuth");
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    try {
      await disconnectNotion(workspaceId);
      await refresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Disconnect failed");
    }
  }

  async function handleImport() {
    if (selected.size === 0) return;
    setImporting(true);
    try {
      await importNotionPages({
        workspaceId,
        spaceId,
        pageIds: [...selected],
      });
      setSelected(new Set());
      await onImported();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  function toggle(pageId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(pageId)) next.delete(pageId);
      else next.add(pageId);
      return next;
    });
  }

  return (
    <section className="mt-6 rounded-2xl border border-white/7 bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-slate-200">Notion</h2>
          <p className="mt-1 text-[11px] text-slate-600">
            Connect a workspace and import pages into this knowledge space.
          </p>
        </div>
        {loading ? (
          <LoaderCircle className="size-4 animate-spin text-slate-600" />
        ) : status?.connected ? (
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-[11px] text-slate-400 transition hover:border-red-400/30 hover:text-red-300"
            onClick={() => void handleDisconnect()}
          >
            <Unlink className="size-3.5" />
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            disabled={connecting}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#2383e2] px-2.5 py-1.5 text-[11px] font-medium text-white transition hover:bg-[#1b6ec2] disabled:opacity-50"
            onClick={() => void handleConnect()}
          >
            {connecting ? (
              <LoaderCircle className="size-3.5 animate-spin" />
            ) : (
              <Link2 className="size-3.5" />
            )}
            Connect Notion
          </button>
        )}
      </div>

      {status?.connected && (
        <div className="mt-4">
          <p className="text-[11px] text-slate-500">
            Connected
            {status.workspace_name ? ` · ${status.workspace_name}` : ""}
          </p>
          {pages.length === 0 ? (
            <p className="mt-3 text-xs text-slate-600">
              No shared pages found. In Notion, open a page → ··· → Connections →
              add this integration.
            </p>
          ) : (
            <>
              <ul className="mt-3 max-h-48 space-y-1 overflow-y-auto">
                {pages.map((page) => (
                  <li key={page.id}>
                    <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-300 hover:bg-white/[0.04]">
                      <input
                        type="checkbox"
                        checked={selected.has(page.id)}
                        onChange={() => toggle(page.id)}
                        className="accent-cyan-400"
                      />
                      <span className="truncate">{page.title}</span>
                    </label>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                disabled={selected.size === 0 || importing}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/20 px-3 py-1.5 text-[11px] font-medium text-cyan-200 transition hover:bg-cyan-500/30 disabled:opacity-40"
                onClick={() => void handleImport()}
              >
                {importing ? (
                  <LoaderCircle className="size-3.5 animate-spin" />
                ) : null}
                Import {selected.size || ""}{" "}
                {selected.size === 1 ? "page" : "pages"}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
