export const STATUS_STYLES = {
  active: "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
  pending: "border-amber-500/40 text-amber-400 bg-amber-500/10",
  superseded: "border-neutral-500/40 text-neutral-400 bg-neutral-500/10",
  archived: "border-red-500/40 text-red-400 bg-red-500/10",
};

export function StatusBadge({ status, testid }) {
  const cls = STATUS_STYLES[status] || STATUS_STYLES.superseded;
  return (
    <span
      data-testid={testid}
      className={`inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider border ${cls}`}
    >
      {status}
    </span>
  );
}

export function TypeBadge({ type }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider border border-[#262626] text-neutral-300 bg-[#141414]">
      {type}
    </span>
  );
}

export function Confidence({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 w-24">
      <div className="h-1.5 flex-1 bg-[#262626]">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[11px] text-neutral-400 w-8">{pct}%</span>
    </div>
  );
}
