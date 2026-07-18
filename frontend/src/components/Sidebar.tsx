import { FormEvent, useState } from "react";
import {
  Bot,
  Boxes,
  FileText,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Plus,
  Settings,
  Sparkles,
} from "lucide-react";

import type { AuthUser, AuthWorkspace, Project } from "../lib/api";

export type AppView = "assistant" | "workflows" | "knowledge";

const navigation: {
  id: AppView;
  label: string;
  icon: typeof Bot;
}[] = [
  { id: "assistant", label: "Assistant", icon: Bot },
  { id: "workflows", label: "Workflows", icon: Boxes },
  { id: "knowledge", label: "Knowledge", icon: FileText },
];

interface SidebarProps {
  user: AuthUser;
  workspaces: AuthWorkspace[];
  workspaceId: string;
  projects: Project[];
  projectId: string | null;
  spaceId: string | null;
  activeView: AppView;
  mobileOpen: boolean;
  onClose: () => void;
  onNavigate: (view: AppView) => void;
  onSelectWorkspace: (workspaceId: string) => void;
  onSelectProject: (projectId: string) => void;
  onSelectSpace: (spaceId: string) => void;
  onCreateProject: (name: string) => Promise<void>;
  onCreateSpace: (name: string) => Promise<void>;
  onLogout: () => void;
}

export function Sidebar({
  user,
  workspaces,
  workspaceId,
  projects,
  projectId,
  spaceId,
  activeView,
  mobileOpen,
  onClose,
  onNavigate,
  onSelectWorkspace,
  onSelectProject,
  onSelectSpace,
  onCreateProject,
  onCreateSpace,
  onLogout,
}: SidebarProps) {
  const [projectName, setProjectName] = useState("");
  const [spaceName, setSpaceName] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  const [creatingSpace, setCreatingSpace] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [showSpaceForm, setShowSpaceForm] = useState(false);

  const workspace =
    workspaces.find((item) => item.id === workspaceId) ?? workspaces[0];
  const activeProject =
    projects.find((item) => item.id === projectId) ?? projects[0] ?? null;

  async function submitProject(event: FormEvent) {
    event.preventDefault();
    const name = projectName.trim();
    if (!name || creatingProject) return;
    setCreatingProject(true);
    try {
      await onCreateProject(name);
      setProjectName("");
      setShowProjectForm(false);
    } finally {
      setCreatingProject(false);
    }
  }

  async function submitSpace(event: FormEvent) {
    event.preventDefault();
    const name = spaceName.trim();
    if (!name || creatingSpace || !activeProject) return;
    setCreatingSpace(true);
    try {
      await onCreateSpace(name);
      setSpaceName("");
      setShowSpaceForm(false);
    } finally {
      setCreatingSpace(false);
    }
  }

  function navigate(view: AppView) {
    onNavigate(view);
    onClose();
  }

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/55 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-screen w-64 shrink-0 flex-col border-r border-white/7 bg-[#090d16] px-3 py-4 transition-transform lg:static lg:z-auto lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        } ${mobileOpen ? "flex" : "hidden lg:flex"}`}
      >
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

      <div className="mt-5 space-y-2 rounded-xl border border-white/8 bg-white/[0.035] px-3 py-2.5">
        <div className="flex items-center gap-3">
          <div className="grid size-8 place-items-center rounded-lg bg-indigo-500/15 text-indigo-300">
            <LayoutDashboard className="size-4" />
          </div>
          <div className="min-w-0 flex-1">
            {workspaces.length > 1 ? (
              <select
                className="w-full truncate bg-transparent text-xs font-medium text-slate-200 outline-none"
                value={workspaceId}
                onChange={(event) => onSelectWorkspace(event.target.value)}
              >
                {workspaces.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            ) : (
              <p className="truncate text-xs font-medium text-slate-200">
                {workspace?.name ?? "Workspace"}
              </p>
            )}
            <p className="truncate text-[10px] text-slate-500">{user.email}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-2 px-1">
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
            <FolderKanban className="size-3" />
            Project / Space
          </div>
        </div>
        <div className="flex items-center gap-1 px-1">
          <select
            className="min-w-0 flex-1 rounded-lg border border-white/8 bg-[#0f1522] px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
            value={activeProject?.id ?? ""}
            onChange={(event) => onSelectProject(event.target.value)}
            disabled={projects.length === 0}
          >
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            title="New project"
            className="grid size-8 shrink-0 place-items-center rounded-lg border border-white/8 text-slate-500 transition hover:border-cyan-400/30 hover:text-cyan-200"
            onClick={() => {
              setShowProjectForm((open) => !open);
              setShowSpaceForm(false);
            }}
          >
            <Plus className="size-3.5" />
          </button>
        </div>
        {showProjectForm && (
          <form className="flex gap-1 px-1" onSubmit={(e) => void submitProject(e)}>
            <input
              className="min-w-0 flex-1 rounded-lg border border-white/8 bg-[#0f1522] px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
              placeholder="Project name"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              autoFocus
            />
            <button
              type="submit"
              disabled={!projectName.trim() || creatingProject}
              className="rounded-lg bg-cyan-500/20 px-2 text-[10px] font-medium text-cyan-200 disabled:opacity-40"
            >
              Add
            </button>
          </form>
        )}
        <div className="flex items-center gap-1 px-1">
          <select
            className="min-w-0 flex-1 rounded-lg border border-white/8 bg-[#0f1522] px-2.5 py-2 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
            value={spaceId ?? ""}
            onChange={(event) => onSelectSpace(event.target.value)}
            disabled={!activeProject?.spaces.length}
          >
            {(activeProject?.spaces ?? []).map((space) => (
              <option key={space.id} value={space.id}>
                {space.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            title="New space"
            className="grid size-8 shrink-0 place-items-center rounded-lg border border-white/8 text-slate-500 transition hover:border-cyan-400/30 hover:text-cyan-200"
            disabled={!activeProject}
            onClick={() => {
              setShowSpaceForm((open) => !open);
              setShowProjectForm(false);
            }}
          >
            <Plus className="size-3.5" />
          </button>
        </div>
        {showSpaceForm && (
          <form className="flex gap-1 px-1" onSubmit={(e) => void submitSpace(e)}>
            <input
              className="min-w-0 flex-1 rounded-lg border border-white/8 bg-[#0f1522] px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-400/40"
              placeholder="Space name"
              value={spaceName}
              onChange={(event) => setSpaceName(event.target.value)}
              autoFocus
            />
            <button
              type="submit"
              disabled={!spaceName.trim() || creatingSpace}
              className="rounded-lg bg-cyan-500/20 px-2 text-[10px] font-medium text-cyan-200 disabled:opacity-40"
            >
              Add
            </button>
          </form>
        )}
      </div>

      <nav className="mt-6 space-y-1">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
          Navigate
        </p>
        {navigation.map(({ id, label, icon: Icon }) => {
          const active = activeView === id;
          return (
            <button
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-cyan-400/8 text-cyan-200"
                  : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
              }`}
              key={id}
              type="button"
              onClick={() => navigate(id)}
            >
              <Icon className="size-4" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto">
        <div className="mx-2 mb-3 rounded-xl border border-cyan-400/10 bg-cyan-400/[0.035] p-3">
          <div className="flex items-center gap-2 text-xs font-medium text-cyan-200">
            <span className="size-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
            Signed in as {user.display_name}
          </div>
          <p className="mt-1.5 text-[10px] leading-4 text-slate-600">
            Knowledge is isolated per project space.
          </p>
        </div>
        <button
          type="button"
          disabled
          title="Soon"
          className="flex w-full cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-700"
        >
          <Settings className="size-4" />
          Settings
        </button>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500 transition hover:bg-white/[0.04] hover:text-red-300"
          onClick={onLogout}
        >
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </aside>
    </>
  );
}
