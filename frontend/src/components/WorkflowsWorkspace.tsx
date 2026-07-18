import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  FileText,
  LoaderCircle,
  Menu,
  Rocket,
  Search,
} from "lucide-react";

import type {
  WorkflowArtifact,
  WorkflowRun,
  WorkflowRunSummary,
} from "../lib/api";

import { ArtifactReader } from "./ArtifactReader";

export type WorkflowKind = "launch_strategy" | "research_brief";

const LAUNCH_PIPELINE = [
  "queued",
  "retrieve",
  "research",
  "planning",
  "spec",
  "content",
  "persist",
  "done",
] as const;

const BRIEF_PIPELINE = [
  "queued",
  "retrieve",
  "research",
  "persist",
  "done",
] as const;

interface WorkflowsWorkspaceProps {
  runs: WorkflowRunSummary[];
  activeRun: WorkflowRun | null;
  enqueueing: boolean;
  onEnqueue: (
    brief: string,
    productName: string | undefined,
    workflowKind: WorkflowKind,
  ) => Promise<void>;
  onSelectRun: (runId: string) => Promise<void>;
  onOpenNav?: () => void;
}

function statusLabel(run: WorkflowRunSummary | WorkflowRun): string {
  if (run.status === "running" || run.status === "pending") {
    return run.current_step ? `${run.status} · ${run.current_step}` : run.status;
  }
  return run.status;
}

function normalizeStep(step: string | null | undefined): string {
  if (!step) return "queued";
  if (step === "starting") return "queued";
  if (step === "failed") return "persist";
  return step;
}

function formatElapsed(startedAt: string, nowMs: number): string {
  const started = new Date(startedAt).getTime();
  const seconds = Math.max(0, Math.floor((nowMs - started) / 1000));
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

function workflowLabel(type: string): string {
  if (type === "research_brief") return "Research Brief";
  return "Launch Strategy";
}

export function WorkflowsWorkspace({
  runs,
  activeRun,
  enqueueing,
  onEnqueue,
  onSelectRun,
  onOpenNav,
}: WorkflowsWorkspaceProps) {
  const [workflowKind, setWorkflowKind] =
    useState<WorkflowKind>("launch_strategy");
  const [brief, setBrief] = useState(
    "I want to open a network of coffee shops in Australia.",
  );
  const [productName, setProductName] = useState("");
  const [selection, setSelection] = useState<{
    runId: string;
    kind: string;
  } | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());

  const artifacts = useMemo(() => activeRun?.artifacts ?? [], [activeRun]);
  const selectedKind =
    activeRun && selection?.runId === activeRun.id ? selection.kind : "pack";

  const selected: WorkflowArtifact | null = useMemo(() => {
    if (!artifacts.length) return null;
    return (
      artifacts.find((item) => item.kind === selectedKind) ??
      artifacts.find((item) => item.kind === "pack") ??
      artifacts[0]
    );
  }, [artifacts, selectedKind]);

  const busy =
    enqueueing ||
    activeRun?.status === "pending" ||
    activeRun?.status === "running";

  const pipeline =
    (activeRun?.workflow_type === "research_brief"
      ? BRIEF_PIPELINE
      : workflowKind === "research_brief"
        ? BRIEF_PIPELINE
        : LAUNCH_PIPELINE) as readonly string[];

  const displayType = activeRun?.workflow_type ?? workflowKind;
  const currentStep = normalizeStep(activeRun?.current_step);
  const currentIndex = pipeline.indexOf(currentStep);

  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [busy]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = brief.trim();
    if (!value || busy) return;
    setFullscreen(false);
    setSelection(null);
    await onEnqueue(value, productName.trim() || undefined, workflowKind);
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-[#0b101a]">
      <header className="flex h-[68px] shrink-0 items-center border-b border-white/7 px-4 sm:px-6">
        {onOpenNav && (
          <button
            type="button"
            className="mr-3 text-slate-500 transition hover:text-slate-300 lg:hidden"
            onClick={onOpenNav}
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </button>
        )}
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl border border-amber-400/20 bg-amber-400/10 text-amber-300">
            {displayType === "research_brief" ? (
              <Search className="size-4" />
            ) : (
              <Rocket className="size-4" />
            )}
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">Workflows</h1>
            <p className="mt-0.5 text-[10px] text-slate-600">
              {workflowLabel(displayType)} · async agents · history
            </p>
          </div>
        </div>
        {activeRun && (
          <div className="ml-auto flex items-center gap-2 text-[11px] text-slate-500">
            {activeRun.status === "completed" ? (
              <CheckCircle2 className="size-3.5 text-emerald-400" />
            ) : activeRun.status === "failed" ? (
              <AlertCircle className="size-3.5 text-red-400" />
            ) : (
              <LoaderCircle className="size-3.5 animate-spin text-amber-300" />
            )}
            <span className="max-w-[320px] truncate">
              {activeRun.product_name ?? "Run"} · {statusLabel(activeRun)}
              {busy ? ` · ${formatElapsed(activeRun.created_at, nowMs)}` : ""}
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
            <div className="grid grid-cols-2 gap-1 rounded-lg border border-white/8 bg-white/[0.02] p-1">
              <button
                type="button"
                disabled={busy}
                className={`rounded-md px-2 py-1.5 text-[10px] font-medium transition ${
                  workflowKind === "launch_strategy"
                    ? "bg-amber-400/15 text-amber-100"
                    : "text-slate-500 hover:text-slate-300"
                }`}
                onClick={() => setWorkflowKind("launch_strategy")}
              >
                Launch Strategy
              </button>
              <button
                type="button"
                disabled={busy}
                className={`rounded-md px-2 py-1.5 text-[10px] font-medium transition ${
                  workflowKind === "research_brief"
                    ? "bg-amber-400/15 text-amber-100"
                    : "text-slate-500 hover:text-slate-300"
                }`}
                onClick={() => setWorkflowKind("research_brief")}
              >
                Research Brief
              </button>
            </div>
            <input
              className="w-full rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-amber-400/30"
              placeholder="Product name (optional)"
              value={productName}
              onChange={(event) => setProductName(event.target.value)}
              disabled={busy}
            />
            <textarea
              className="min-h-28 w-full resize-y rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs leading-5 text-slate-200 outline-none placeholder:text-slate-600 focus:border-amber-400/30"
              placeholder="Describe the initiative…"
              value={brief}
              onChange={(event) => setBrief(event.target.value)}
              disabled={busy}
            />
            <button
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-amber-400 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
              disabled={!brief.trim() || busy}
              type="submit"
            >
              {busy ? (
                <>
                  <LoaderCircle className="size-3.5 animate-spin" />
                  {activeRun?.current_step
                    ? `Working · ${activeRun.current_step}`
                    : "Queued…"}
                </>
              ) : (
                <>
                  {workflowKind === "research_brief" ? (
                    <Search className="size-3.5" />
                  ) : (
                    <Rocket className="size-3.5" />
                  )}
                  Run{" "}
                  {workflowKind === "research_brief" ? "brief" : "agents"}
                </>
              )}
            </button>
          </form>

          {(busy || activeRun?.status === "failed") && activeRun && (
            <div className="shrink-0 border-b border-white/7 px-4 py-3">
              {activeRun.status === "failed" && activeRun.error && (
                <div className="mb-3 flex items-start gap-2 rounded-lg border border-red-400/20 bg-red-400/5 px-3 py-2 text-[11px] text-red-200">
                  <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
                  <span>{activeRun.error}</span>
                </div>
              )}
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                Pipeline
                {busy
                  ? ` · ${formatElapsed(activeRun.created_at, nowMs)}`
                  : ""}
              </p>
              <ol className="space-y-1">
                {pipeline.map((step, index) => {
                  const done =
                    activeRun.status === "completed" ||
                    (currentIndex >= 0 && index < currentIndex);
                  const current =
                    busy &&
                    (currentIndex === index ||
                      (currentIndex < 0 && step === "queued"));
                  return (
                    <li
                      key={step}
                      className={`flex items-center gap-2 text-[11px] ${
                        current
                          ? "text-amber-200"
                          : done
                            ? "text-emerald-300/80"
                            : "text-slate-600"
                      }`}
                    >
                      {done ? (
                        <CheckCircle2 className="size-3" />
                      ) : current ? (
                        <LoaderCircle className="size-3 animate-spin" />
                      ) : (
                        <Circle className="size-3" />
                      )}
                      <span className="capitalize">{step}</span>
                    </li>
                  );
                })}
              </ol>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
              Run history
            </p>
            {runs.length === 0 ? (
              <div className="px-2 py-8 text-center">
                <FileText className="mx-auto size-6 text-slate-700" />
                <p className="mt-3 text-xs text-slate-500">No runs yet.</p>
              </div>
            ) : (
              <ul className="space-y-1">
                {runs.map((item) => {
                  const active = activeRun?.id === item.id;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={`flex w-full flex-col rounded-lg px-3 py-2.5 text-left transition ${
                          active
                            ? "bg-amber-400/10 text-amber-100"
                            : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                        }`}
                        onClick={() => void onSelectRun(item.id)}
                      >
                        <span className="truncate text-xs font-medium">
                          {item.product_name || item.brief.slice(0, 48)}
                        </span>
                        <span className="mt-0.5 text-[10px] opacity-70">
                          {workflowLabel(item.workflow_type)} ·{" "}
                          {statusLabel(item)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}

            {activeRun && artifacts.length > 0 && (
              <>
                <p className="mt-5 px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                  Artifacts
                </p>
                <ul className="space-y-1">
                  {artifacts.map((artifact) => {
                    const active = selected?.id === artifact.id;
                    return (
                      <li key={artifact.id}>
                        <button
                          type="button"
                          className={`flex w-full flex-col rounded-lg px-3 py-2 text-left transition ${
                            active
                              ? "bg-white/[0.06] text-slate-100"
                              : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
                          }`}
                          onClick={() => {
                            setSelection({
                              runId: activeRun.id,
                              kind: artifact.kind,
                            });
                            setFullscreen(false);
                          }}
                        >
                          <span className="text-[10px] uppercase tracking-[0.12em] opacity-70">
                            {artifact.kind.replaceAll("_", " ")}
                          </span>
                          <span className="mt-0.5 truncate text-xs">
                            {artifact.title}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </>
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
                  {busy
                    ? "Agents are working in the background…"
                    : "Select a run or start Launch Strategy / Research Brief"}
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  Completed packs open here at full height.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
