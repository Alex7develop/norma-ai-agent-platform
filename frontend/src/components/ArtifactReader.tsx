import { useEffect } from "react";
import { Maximize2, Minimize2, X } from "lucide-react";

interface ArtifactReaderProps {
  title: string;
  kind?: string;
  content: string;
  expanded?: boolean;
  onExpand?: () => void;
  onCollapse?: () => void;
  onClose?: () => void;
}

export function ArtifactReader({
  title,
  kind,
  content,
  expanded = false,
  onExpand,
  onCollapse,
  onClose,
}: ArtifactReaderProps) {
  useEffect(() => {
    if (!expanded) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onCollapse?.();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded, onCollapse]);

  const body = (
    <div
      className={`flex min-h-0 flex-col bg-[#0b101a] ${
        expanded
          ? "fixed inset-4 z-50 rounded-2xl border border-white/10 shadow-2xl shadow-black/60"
          : "h-full"
      }`}
    >
      <header className="flex shrink-0 items-center gap-3 border-b border-white/7 px-4 py-3">
        <div className="min-w-0 flex-1">
          {kind && (
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-amber-400/80">
              {kind.replaceAll("_", " ")}
            </p>
          )}
          <h3 className="truncate text-sm font-semibold text-slate-100">
            {title}
          </h3>
        </div>
        {expanded ? (
          <button
            type="button"
            className="grid size-8 place-items-center rounded-lg text-slate-500 transition hover:bg-white/5 hover:text-slate-200"
            onClick={onCollapse}
            aria-label="Exit fullscreen"
          >
            <Minimize2 className="size-4" />
          </button>
        ) : (
          onExpand && (
            <button
              type="button"
              className="grid size-8 place-items-center rounded-lg text-slate-500 transition hover:bg-white/5 hover:text-slate-200"
              onClick={onExpand}
              aria-label="Expand reader"
            >
              <Maximize2 className="size-4" />
            </button>
          )
        )}
        {onClose && (
          <button
            type="button"
            className="grid size-8 place-items-center rounded-lg text-slate-500 transition hover:bg-white/5 hover:text-slate-200"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        )}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-8">
        <pre className="mx-auto max-w-3xl whitespace-pre-wrap font-sans text-[13px] leading-7 text-slate-300">
          {content || "—"}
        </pre>
      </div>
    </div>
  );

  if (expanded) {
    return (
      <>
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm"
          aria-label="Close fullscreen"
          onClick={onCollapse}
        />
        {body}
      </>
    );
  }

  return body;
}
