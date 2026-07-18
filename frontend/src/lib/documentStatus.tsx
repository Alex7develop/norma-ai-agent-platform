const STATUS_STYLES: Record<string, string> = {
  pending: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  processing: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  completed: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
  failed: "border-red-400/25 bg-red-400/10 text-red-200",
};

export function DocumentStatusBadge({ status }: { status: string }) {
  const style =
    STATUS_STYLES[status] ?? "border-white/10 bg-white/[0.04] text-slate-400";
  return (
    <span
      className={`inline-flex rounded-md border px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide ${style}`}
    >
      {status}
    </span>
  );
}
