import {
  File,
  FileText,
  LoaderCircle,
  Trash2,
  UploadCloud,
} from "lucide-react";

import type { KnowledgeDocument } from "../lib/api";

interface KnowledgeWorkspaceProps {
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

export function KnowledgeWorkspace({
  documents,
  loading,
  uploading,
  onUpload,
  onDelete,
}: KnowledgeWorkspaceProps) {
  return (
    <main className="flex min-w-0 flex-1 flex-col bg-[#0b101a]">
      <header className="flex h-[68px] shrink-0 items-center border-b border-white/7 px-4 sm:px-6">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">
            Knowledge base
          </h1>
          <p className="mt-0.5 text-[10px] text-slate-600">
            {documents.length}{" "}
            {documents.length === 1 ? "document" : "documents"} indexed in this
            workspace
          </p>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto max-w-3xl">
          <label className="flex cursor-pointer flex-col items-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center transition hover:border-cyan-400/25 hover:bg-cyan-400/[0.025]">
            {uploading ? (
              <LoaderCircle className="size-6 animate-spin text-cyan-400" />
            ) : (
              <UploadCloud className="size-6 text-slate-500" />
            )}
            <span className="mt-3 text-sm font-medium text-slate-300">
              {uploading ? "Indexing document…" : "Upload knowledge"}
            </span>
            <span className="mt-1 text-xs text-slate-600">
              PDF, DOCX, Markdown or TXT · up to 10 MB
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

          <div className="mt-8">
            {loading ? (
              <div className="grid h-40 place-items-center">
                <LoaderCircle className="size-5 animate-spin text-slate-600" />
              </div>
            ) : documents.length === 0 ? (
              <div className="rounded-2xl border border-white/6 px-6 py-12 text-center">
                <FileText className="mx-auto size-7 text-slate-700" />
                <p className="mt-3 text-sm text-slate-400">No knowledge yet</p>
                <p className="mt-1 text-xs text-slate-600">
                  Upload a document or run Launch Strategy to populate the
                  library.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-white/6 rounded-2xl border border-white/7">
                {documents.map((document) => (
                  <li
                    className="flex items-center gap-4 px-4 py-4 transition hover:bg-white/[0.02]"
                    key={document.id}
                  >
                    <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-blue-500/10 text-blue-300">
                      <File className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-200">
                        {document.filename}
                      </p>
                      <p className="mt-1 text-xs text-slate-600">
                        {formatBytes(document.size_bytes)} ·{" "}
                        {document.chunk_count} chunks · {document.status}
                      </p>
                    </div>
                    <button
                      aria-label={`Delete ${document.filename}`}
                      className="grid size-9 place-items-center rounded-lg text-slate-600 transition hover:bg-red-500/10 hover:text-red-300"
                      onClick={() => void onDelete(document.id)}
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
