import { FormEvent, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";

import {
  ApiError,
  type AuthSession,
  login,
  register,
} from "../lib/api";

interface AuthScreenProps {
  onAuthenticated: (session: AuthSession) => void;
}

type Mode = "login" | "register";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("My workspace");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session =
        mode === "login"
          ? await login({ email, password })
          : await register({
              email,
              password,
              display_name: displayName,
              workspace_name: workspaceName,
            });
      onAuthenticated(session);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-[#080c14] px-4 text-slate-200">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,#164e6355,transparent_45%)]" />
      <div className="relative w-full max-w-md rounded-3xl border border-white/8 bg-[#0d1320]/95 p-8 shadow-2xl shadow-black/40 backdrop-blur">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-950">
            <Sparkles className="size-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-white">
              Norma AI
            </h1>
            <p className="text-xs text-slate-500">
              Sign in to your knowledge workspace
            </p>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 rounded-xl border border-white/8 bg-white/[0.02] p-1">
          {(["login", "register"] as const).map((value) => (
            <button
              className={`rounded-lg px-3 py-2 text-sm transition ${
                mode === value
                  ? "bg-cyan-400/15 text-cyan-200"
                  : "text-slate-500 hover:text-slate-300"
              }`}
              key={value}
              type="button"
              onClick={() => {
                setMode(value);
                setError(null);
              }}
            >
              {value === "login" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>

        <form className="space-y-4" onSubmit={submit}>
          {mode === "register" && (
            <>
              <label className="block space-y-1.5">
                <span className="text-xs text-slate-500">Display name</span>
                <input
                  className="w-full rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2.5 text-sm outline-none transition focus:border-cyan-400/30"
                  required
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs text-slate-500">Workspace name</span>
                <input
                  className="w-full rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2.5 text-sm outline-none transition focus:border-cyan-400/30"
                  required
                  value={workspaceName}
                  onChange={(event) => setWorkspaceName(event.target.value)}
                />
              </label>
            </>
          )}
          <label className="block space-y-1.5">
            <span className="text-xs text-slate-500">Email</span>
            <input
              className="w-full rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2.5 text-sm outline-none transition focus:border-cyan-400/30"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs text-slate-500">Password</span>
            <input
              className="w-full rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2.5 text-sm outline-none transition focus:border-cyan-400/30"
              type="password"
              required
              minLength={mode === "register" ? 12 : 1}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {mode === "register" && (
              <span className="block text-[10px] text-slate-600">
                At least 12 characters
              </span>
            )}
          </label>

          {error && (
            <p className="rounded-xl border border-red-400/15 bg-red-400/5 px-3 py-2 text-xs text-red-200">
              {error}
            </p>
          )}

          <button
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
            disabled={busy}
            type="submit"
          >
            {busy && <LoaderCircle className="size-4 animate-spin" />}
            {mode === "login" ? "Continue" : "Create workspace"}
          </button>
        </form>
      </div>
    </div>
  );
}
