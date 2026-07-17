import { FormEvent, useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  LoaderCircle,
  Rocket,
} from "lucide-react";

import type { WorkflowRun } from "../lib/api";

interface LaunchStrategyPanelProps {
  running: boolean;
  run: WorkflowRun | null;
  onRun: (brief: string, productName?: string) => Promise<void>;
}

export function LaunchStrategyPanel({
  running,
  run,
  onRun,
}: LaunchStrategyPanelProps) {
  const [brief, setBrief] = useState(
    "I want to open a network of coffee shops in Australia.",
  );
  const [productName, setProductName] = useState("");
  const [openKind, setOpenKind] = useState<string | null>("pack");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = brief.trim();
    if (!value || running) return;
    await onRun(value, productName.trim() || undefined);
  }

  return (
    <section className="shrink-0 border-b border-white/7 bg-[#0a0f18] px-4 py-4 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <div className="mb-3 flex items-center gap-2">
          <div className="grid size-7 place-items-center rounded-lg border border-amber-400/20 bg-amber-400/10 text-amber-300">
            <Rocket className="size-3.5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Launch Strategy
            </h2>
            <p className="text-[10px] text-slate-600">
              Research · competitors · positioning · roadmap · marketing → KB
            </p>
          </div>
        </div>

        <form className="space-y-2" onSubmit={(event) => void submit(event)}>
          <input
            className="w-full rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-amber-400/30"
            placeholder="Product name (optional)"
            value={productName}
            onChange={(event) => setProductName(event.target.value)}
            disabled={running}
          />
          <textarea
            className="min-h-20 w-full resize-y rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs leading-5 text-slate-200 outline-none placeholder:text-slate-600 focus:border-amber-400/30"
            placeholder="Describe the initiative…"
            value={brief}
            onChange={(event) => setBrief(event.target.value)}
            disabled={running}
          />
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] text-slate-600">
              Agents synthesize a pack and save it into your knowledge base.
            </p>
            <button
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-amber-400 px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
              disabled={!brief.trim() || running}
              type="submit"
            >
              {running ? (
                <>
                  <LoaderCircle className="size-3.5 animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <Rocket className="size-3.5" />
                  Run agents
                </>
              )}
            </button>
          </div>
        </form>

        {run && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              {run.status === "completed" ? (
                <CheckCircle2 className="size-3.5 text-emerald-400" />
              ) : (
                <LoaderCircle className="size-3.5 animate-spin text-amber-300" />
              )}
              <span>
                {run.product_name ?? "Launch pack"} · {run.status}
                {run.pack_filename ? ` · saved as ${run.pack_filename}` : ""}
              </span>
            </div>
            <div className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-white/7 bg-black/20 p-2">
              {run.artifacts.map((artifact) => {
                const open = openKind === artifact.kind;
                return (
                  <div key={artifact.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[11px] text-slate-400 transition hover:bg-white/[0.04] hover:text-slate-200"
                      onClick={() =>
                        setOpenKind(open ? null : artifact.kind)
                      }
                    >
                      {open ? (
                        <ChevronDown className="size-3.5 shrink-0" />
                      ) : (
                        <ChevronRight className="size-3.5 shrink-0" />
                      )}
                      <span className="font-medium capitalize">
                        {artifact.kind}
                      </span>
                      <span className="truncate text-slate-600">
                        {artifact.title}
                      </span>
                    </button>
                    {open && (
                      <pre className="mx-2 mb-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-black/30 px-3 py-2 text-[10px] leading-4 text-slate-400">
                        {artifact.content_md || "—"}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
