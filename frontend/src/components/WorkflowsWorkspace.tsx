import { FormEvent, useMemo, useState } from "react";
import {
  CheckCircle2,
  FileText,
  LoaderCircle,
  Rocket,
} from "lucide-react";

import type { WorkflowArtifact, WorkflowRun } from "../lib/api";

import { ArtifactReader } from "./ArtifactReader";

interface WorkflowsWorkspaceProps {
  running: boolean;
  run: WorkflowRun | null;
  onRun: (brief: string, productName?: string) => Promise<void>;
}

export function WorkflowsWorkspace({
  running,
  run,
  onRun,
}: WorkflowsWorkspaceProps) {
  const [brief, setBrief] = useState(
    "I want to open a network of coffee shops in Australia.",
  );
  const [productName, setProductName] = useState("");
  const [selection, setSelection] = useState<{
    runId: string;
    kind: string;
  } | null>(null);
  const [fullscreen, setFullscreen] = useState(false);

  const artifacts = useMemo(() => run?.artifacts ?? [], [run]);
  const selectedKind =
    run && selection?.runId === run.id ? selection.kind : "pack";

  const selected: WorkflowArtifact | null = useMemo(() => {
    if (!artifacts.length) return null;
    return (
      artifacts.find((item) => item.kind === selectedKind) ??
      artifacts.find((item) => item.kind === "pack") ??
      artifacts[0]
    );
  }, [artifacts, selectedKind]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = brief.trim();
    if (!value || running) return;
    setFullscreen(false);
    setSelection(null);
    await onRun(value, productName.trim() || undefined);
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-[#0b101a]">
      <header className="flex h-[68px] shrink-0 items-center border-b border-white/7 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl border border-amber-400/20 bg-amber-400/10 text-amber-300">
            <Rocket className="size-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">
              Launch Strategy
            </h1>
            <p className="mt-0.5 text-[10px] text-slate-600">
              Multi-agent pack · saved to knowledge + memory
            </p>
          </div>
        </div>
        {run && (
          <div className="ml-auto flex items-center gap-2 text-[11px] text-slate-500">
            {run.status === "completed" ? (
              <CheckCircle2 className="size-3.5 text-emerald-400" />
            ) : (
              <LoaderCircle className="size-3.5 animate-spin text-amber-300" />
            )}
            <span className="max-w-[280px] truncate">
              {run.product_name ?? "Run"} · {run.status}
            </span>
          </div>
        )}
      </header>

      <div className="flex min-h-0 flex-1">
        <section className="flex w-full max-w-md shrink-0 flex-col border-r border-white/7 bg-[#0a0f18]">
          <form
            className="shrink-0 space-y-2 border-b border-white/7 p-4"
            onSubmit={(event) => void submit(event)}
          >
            <input
              className="w-full rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-amber-400/30"
              placeholder="Product name (optional)"
              value={productName}
              onChange={(event) => setProductName(event.target.value)}
              disabled={running}
            />
            <textarea
              className="min-h-28 w-full resize-y rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs leading-5 text-slate-200 outline-none placeholder:text-slate-600 focus:border-amber-400/30"
              placeholder="Describe the initiative…"
              value={brief}
              onChange={(event) => setBrief(event.target.value)}
              disabled={running}
            />
            <button
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-amber-400 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
              disabled={!brief.trim() || running}
              type="submit"
            >
              {running ? (
                <>
                  <LoaderCircle className="size-3.5 animate-spin" />
                  Agents running…
                </>
              ) : (
                <>
                  <Rocket className="size-3.5" />
                  Run agents
                </>
              )}
            </button>
          </form>

          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {!run ? (
              <div className="px-2 py-10 text-center">
                <FileText className="mx-auto size-6 text-slate-700" />
                <p className="mt-3 text-xs text-slate-500">
                  Artifacts will appear here after a run.
                </p>
              </div>
            ) : (
              <ul className="space-y-1">
                {artifacts.map((artifact) => {
                  const active = selected?.id === artifact.id;
                  return (
                    <li key={artifact.id}>
                      <button
                        type="button"
                        className={`flex w-full flex-col rounded-lg px-3 py-2.5 text-left transition ${
                          active
                            ? "bg-amber-400/10 text-amber-100"
                            : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                        }`}
                        onClick={() => {
                          setSelection({ runId: run.id, kind: artifact.kind });
                          setFullscreen(false);
                        }}
                      >
                        <span className="text-[10px] font-medium uppercase tracking-[0.12em] opacity-70">
                          {artifact.kind.replaceAll("_", " ")}
                        </span>
                        <span className="mt-0.5 truncate text-xs font-medium">
                          {artifact.title}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>

        <section className="min-w-0 flex-1">
          {selected ? (
            <ArtifactReader
              title={selected.title}
              kind={selected.kind}
              content={selected.content_md}
              expanded={fullscreen}
              onExpand={() => setFullscreen(true)}
              onCollapse={() => setFullscreen(false)}
            />
          ) : (
            <div className="grid h-full place-items-center px-6 text-center">
              <div>
                <Rocket className="mx-auto size-8 text-slate-700" />
                <p className="mt-4 text-sm text-slate-400">
                  Run Launch Strategy to generate a full pack
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  Select any section to read it at full height — use expand for
                  distraction-free view.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
