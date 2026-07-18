import {
  File,
  FileText,
  LoaderCircle,
  Plus,
  Trash2,
  UploadCloud,
} from "lucide-react";

import type { KnowledgeDocument } from "../lib/api";
import { DocumentStatusBadge } from "../lib/documentStatus";

interface KnowledgePanelProps {
  documents: KnowledgeDocument[];
  loading: boolean;
  uploading: boolean;
  onUpload: (file: File) => Promise<void>;
  onDelete: (documentId: string) => Promise<void>;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function KnowledgePanel({
  documents,
  loading,
  uploading,
  onUpload,
  onDelete,
}: KnowledgePanelProps) {
  return (
    <aside className="hidden h-screen w-[340px] shrink-0 border-l border-white/7 bg-[#0a0f19] xl:flex xl:flex-col">
      <div className="border-b border-white/7 px-5 py-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Knowledge base
            </h2>
            <p className="mt-1 text-[11px] text-slate-600">
              {documents.length} {documents.length === 1 ? "document" : "documents"}
            </p>
          </div>
          <label className="grid size-8 cursor-pointer place-items-center rounded-lg border border-white/8 bg-white/[0.035] text-slate-400 transition hover:border-cyan-400/30 hover:text-cyan-300">
            {uploading ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <Plus className="size-4" />
            )}
            <input
              className="hidden"
              type="file"
              accept=".pdf,.docx,.md,.markdown,.txt"
              disabled={uploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void onUpload(file);
                event.target.value = "";
              }}
            />
          </label>
        </div>

        <label className="mt-4 flex cursor-pointer flex-col items-center rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-5 text-center transition hover:border-cyan-400/25 hover:bg-cyan-400/[0.025]">
          {uploading ? (
            <LoaderCircle className="size-5 animate-spin text-cyan-400" />
          ) : (
            <UploadCloud className="size-5 text-slate-500" />
          )}
          <span className="mt-2 text-xs font-medium text-slate-400">
            {uploading ? "Indexing document…" : "Upload knowledge"}
          </span>
          <span className="mt-1 text-[10px] text-slate-600">
            PDF, DOCX, Markdown or TXT · 10 MB
          </span>
          <input
            className="hidden"
            type="file"
            accept=".pdf,.docx,.md,.markdown,.txt"
            disabled={uploading}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void onUpload(file);
              event.target.value = "";
            }}
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {loading ? (
          <div className="grid h-32 place-items-center">
            <LoaderCircle className="size-5 animate-spin text-slate-600" />
          </div>
        ) : documents.length === 0 ? (
          <div className="mx-2 mt-5 rounded-xl border border-white/6 bg-white/[0.018] px-5 py-8 text-center">
            <FileText className="mx-auto size-6 text-slate-700" />
            <p className="mt-3 text-xs font-medium text-slate-400">
              No knowledge yet
            </p>
            <p className="mt-1 text-[10px] leading-4 text-slate-600">
              Upload a document to ground Norma&apos;s answers.
            </p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {documents.map((document) => (
              <div
                className="group flex items-start gap-3 rounded-xl border border-transparent px-3 py-3 transition hover:border-white/7 hover:bg-white/[0.025]"
                key={document.id}
              >
                <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-blue-500/10 text-blue-300">
                  <File className="size-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-slate-300">
                    {document.filename}
                  </p>
                  <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-600">
                    <span>
                      {formatBytes(document.size_bytes)} · {document.chunk_count}{" "}
                      chunks
                    </span>
                    <DocumentStatusBadge status={document.status} />
                  </p>
                </div>
                <button
                  aria-label={`Delete ${document.filename}`}
                  className="mt-1 text-slate-700 opacity-0 transition hover:text-red-400 group-hover:opacity-100"
                  onClick={() => void onDelete(document.id)}
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
