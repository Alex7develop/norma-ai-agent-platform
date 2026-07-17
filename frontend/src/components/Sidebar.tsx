import {
  Bot,
  Boxes,
  FileText,
  LayoutDashboard,
  LogOut,
  Settings,
  Sparkles,
} from "lucide-react";

import type { AuthUser, AuthWorkspace } from "../lib/api";

const navigation = [
  { label: "Assistant", icon: Bot, active: true },
  { label: "Knowledge", icon: FileText },
  { label: "Workflows", icon: Boxes, badge: "Soon" },
];

interface SidebarProps {
  user: AuthUser;
  workspace: AuthWorkspace;
  onLogout: () => void;
}

export function Sidebar({ user, workspace, onLogout }: SidebarProps) {
  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-white/7 bg-[#090d16] px-3 py-4 lg:flex">
      <div className="flex items-center gap-3 px-3 py-2">
        <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-950">
          <Sparkles className="size-4 text-white" />
        </div>
        <div>
          <p className="text-[15px] font-semibold tracking-tight text-white">
            Norma AI
          </p>
          <p className="text-[11px] text-slate-500">Knowledge OS</p>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3 rounded-xl border border-white/8 bg-white/[0.035] px-3 py-2.5 text-left">
        <div className="grid size-8 place-items-center rounded-lg bg-indigo-500/15 text-indigo-300">
          <LayoutDashboard className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-slate-200">
            {workspace.name}
          </p>
          <p className="truncate text-[10px] text-slate-500">{user.email}</p>
        </div>
      </div>

      <nav className="mt-6 space-y-1">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
          Workspace
        </p>
        {navigation.map(({ label, icon: Icon, active, badge }) => (
          <button
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
              active
                ? "bg-cyan-400/8 text-cyan-200"
                : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
            }`}
            key={label}
          >
            <Icon className="size-4" />
            <span>{label}</span>
            {badge && (
              <span className="ml-auto rounded-md border border-white/8 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-slate-600">
                {badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="mt-auto">
        <div className="mx-2 mb-3 rounded-xl border border-cyan-400/10 bg-cyan-400/[0.035] p-3">
          <div className="flex items-center gap-2 text-xs font-medium text-cyan-200">
            <span className="size-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
            Signed in as {user.display_name}
          </div>
          <p className="mt-1.5 text-[10px] leading-4 text-slate-600">
            Knowledge is isolated to your workspace membership.
          </p>
        </div>
        <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-300">
          <Settings className="size-4" />
          Settings
        </button>
        <button
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/[0.04] hover:text-red-300"
          onClick={onLogout}
        >
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
