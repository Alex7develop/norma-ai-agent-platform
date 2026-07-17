import { FormEvent, useState } from "react";
import {
  ArrowUp,
  Bot,
  Database,
  LoaderCircle,
  Menu,
  Paperclip,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";

import type { AssistantSource, WorkflowRun } from "../lib/api";

import { LaunchStrategyPanel } from "./LaunchStrategyPanel";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: AssistantSource[];
  model?: string;
}

interface ChatWorkspaceProps {
  messages: ChatMessage[];
  thinking: boolean;
  documentsCount: number;
  launchRunning: boolean;
  launchRun: WorkflowRun | null;
  onSend: (question: string) => Promise<void>;
  onLaunchStrategy: (brief: string, productName?: string) => Promise<void>;
}

const suggestions = [
  "Summarize the knowledge in this workspace",
  "What are the key architecture decisions?",
  "Which technologies does this project use?",
];

export function ChatWorkspace({
  messages,
  thinking,
  documentsCount,
  launchRunning,
  launchRun,
  onSend,
  onLaunchStrategy,
}: ChatWorkspaceProps) {
  const [question, setQuestion] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (!value || thinking) return;
    setQuestion("");
    await onSend(value);
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-[#0b101a]">
      <LaunchStrategyPanel
        running={launchRunning}
        run={launchRun}
        onRun={onLaunchStrategy}
      />
      <header className="flex h-[68px] shrink-0 items-center border-b border-white/7 px-4 sm:px-6">
        <button className="mr-3 text-slate-500 lg:hidden">
          <Menu className="size-5" />
        </button>
        <div className="flex items-center gap-3">
          <div className="relative grid size-9 place-items-center rounded-xl border border-cyan-400/15 bg-cyan-400/8 text-cyan-300">
            <Bot className="size-4" />
            <span className="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full border-2 border-[#0b101a] bg-emerald-400" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100">
              Knowledge Assistant
            </h1>
            <p className="mt-0.5 text-[10px] text-slate-600">
              Gemini 3.5 Flash · grounded by BGE-M3
            </p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2 rounded-lg border border-white/7 bg-white/[0.025] px-2.5 py-1.5 text-[10px] text-slate-500">
          <ShieldCheck className="size-3 text-emerald-400" />
          Workspace isolated
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 sm:px-8">
          {messages.length === 0 ? (
            <div className="my-auto py-16 text-center">
              <div className="mx-auto grid size-14 place-items-center rounded-2xl border border-cyan-400/15 bg-gradient-to-br from-cyan-400/10 to-blue-500/5 shadow-2xl shadow-cyan-950/30">
                <Sparkles className="size-6 text-cyan-300" />
              </div>
              <h2 className="mt-6 text-xl font-semibold tracking-tight text-slate-100">
                Turn knowledge into answers
              </h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                Ask Norma about your documents. Every response is grounded in
                your workspace and includes its sources.
              </p>
              <div className="mx-auto mt-7 grid max-w-xl gap-2 sm:grid-cols-3">
                {suggestions.map((suggestion) => (
                  <button
                    className="rounded-xl border border-white/7 bg-white/[0.025] px-3 py-3 text-left text-[11px] leading-4 text-slate-500 transition hover:border-cyan-400/20 hover:bg-cyan-400/[0.025] hover:text-slate-300"
                    key={suggestion}
                    onClick={() => void onSend(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-7 py-8">
              {messages.map((message) => (
                <article
                  className={`flex gap-3.5 ${
                    message.role === "user" ? "justify-end" : ""
                  }`}
                  key={message.id}
                >
                  {message.role === "assistant" && (
                    <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-cyan-400/10 text-cyan-300">
                      <Bot className="size-3.5" />
                    </div>
                  )}
                  <div
                    className={`max-w-[82%] ${
                      message.role === "user"
                        ? "rounded-2xl rounded-tr-md bg-blue-600 px-4 py-3 text-white"
                        : "min-w-0 pt-1"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-[13px] leading-6">
                      {message.content}
                    </p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-4 border-t border-white/7 pt-3">
                        <p className="mb-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.12em] text-slate-600">
                          <Database className="size-3" />
                          Sources
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {message.sources.map((source) => (
                            <div
                              className="rounded-lg border border-white/7 bg-white/[0.025] px-2.5 py-1.5 text-[10px] text-slate-500"
                              key={`${source.citation}-${source.chunk_index}`}
                            >
                              <span className="mr-1.5 font-semibold text-cyan-400">
                                [{source.citation}]
                              </span>
                              {source.filename ?? "Knowledge source"}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  {message.role === "user" && (
                    <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-white/7 text-slate-400">
                      <User className="size-3.5" />
                    </div>
                  )}
                </article>
              ))}
              {thinking && (
                <div className="flex items-center gap-3 text-xs text-slate-600">
                  <div className="grid size-8 place-items-center rounded-lg bg-cyan-400/10 text-cyan-300">
                    <LoaderCircle className="size-3.5 animate-spin" />
                  </div>
                  Retrieving knowledge and reasoning…
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 px-4 pb-5 sm:px-8">
        <form className="mx-auto max-w-3xl" onSubmit={submit}>
          <div className="rounded-2xl border border-white/10 bg-[#111827] p-2 shadow-2xl shadow-black/25 transition focus-within:border-cyan-400/25">
            <textarea
              className="max-h-36 min-h-12 w-full resize-none bg-transparent px-3 py-2 text-sm leading-5 text-slate-200 outline-none placeholder:text-slate-600"
              placeholder={
                documentsCount
                  ? "Ask anything about your knowledge…"
                  : "Upload a document, then ask Norma a question…"
              }
              rows={1}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="flex items-center px-1 pb-0.5">
              <button
                type="button"
                className="grid size-8 place-items-center rounded-lg text-slate-600 transition hover:bg-white/5 hover:text-slate-400"
              >
                <Paperclip className="size-4" />
              </button>
              <span className="ml-1 text-[10px] text-slate-700">
                Enter to send · Shift + Enter for new line
              </span>
              <button
                className="ml-auto grid size-8 place-items-center rounded-lg bg-cyan-400 text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
                disabled={!question.trim() || thinking}
                type="submit"
              >
                {thinking ? (
                  <LoaderCircle className="size-4 animate-spin" />
                ) : (
                  <ArrowUp className="size-4" />
                )}
              </button>
            </div>
          </div>
          <p className="mt-2 text-center text-[9px] text-slate-700">
            Norma uses retrieved context and can make mistakes. Verify important
            information.
          </p>
        </form>
      </div>
    </main>
  );
}
