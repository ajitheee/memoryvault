import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { StatusBadge, TypeBadge } from "@/components/Badges";
import { toast } from "sonner";
import { Timer, Download, RefreshCw, ArrowRight, Loader2 } from "lucide-react";

const STATS = [
  { key: "active", label: "Active", color: "text-emerald-400" },
  { key: "pending", label: "Pending", color: "text-amber-400" },
  { key: "superseded", label: "Superseded", color: "text-neutral-400" },
  { key: "archived", label: "Archived", color: "text-red-400" },
];

export default function Overview() {
  const qc = useQueryClient();
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: async () => (await client.get("/vault/stats")).data,
  });
  const { data: pending = [] } = useQuery({
    queryKey: ["pending"],
    queryFn: async () => (await client.get("/pending")).data,
  });

  const decay = useMutation({
    mutationFn: async () => (await client.post("/decay", { max_age_days: 60, min_confidence: 0.5 })).data,
    onSuccess: (d) => {
      toast.success(`Decay complete — ${d.archived} fact(s) archived`);
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const doExport = async () => {
    const { data } = await client.get("/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `memoryvault-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Vault exported");
  };

  return (
    <div>
      <PageHeader
        overline="Vault"
        title="Overview"
        testid="overview-header"
        actions={
          <>
            <button
              data-testid="decay-btn"
              onClick={() => decay.mutate()}
              disabled={decay.isPending}
              className="inline-flex items-center gap-2 border border-[#262626] px-3 py-2 text-sm text-neutral-300 hover:text-white hover:border-white/50 transition-colors disabled:opacity-50"
            >
              {decay.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Timer className="w-4 h-4" />} Run Decay
            </button>
            <button
              data-testid="export-btn"
              onClick={doExport}
              className="inline-flex items-center gap-2 border border-[#262626] px-3 py-2 text-sm text-neutral-300 hover:text-white hover:border-white/50 transition-colors"
            >
              <Download className="w-4 h-4" /> Export JSON
            </button>
          </>
        }
      />

      <div className="p-8 space-y-8">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#262626] border border-[#262626]" data-testid="stats-grid">
          {STATS.map((s) => (
            <div key={s.key} className="bg-[#0A0A0A] p-6">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-3">{s.label}</p>
              <p className={`font-mono text-4xl font-bold ${s.color}`} data-testid={`stat-${s.key}`}>
                {isLoading ? "—" : stats?.[s.key] ?? 0}
              </p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#262626] border border-[#262626]">
          <div className="bg-[#0A0A0A] p-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Total Facts</p>
            <p className="font-mono text-2xl font-bold" data-testid="stat-total">{stats?.total_facts ?? 0}</p>
          </div>
          <div className="bg-[#0A0A0A] p-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-3">Events (L1)</p>
            <p className="font-mono text-2xl font-bold" data-testid="stat-events">{stats?.events ?? 0}</p>
          </div>
          <div className="bg-[#0A0A0A] p-6 col-span-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-3">By Type (active)</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats?.by_type || {}).map(([t, c]) => (
                <span key={t} className="font-mono text-xs border border-[#262626] px-2 py-1 text-neutral-300">
                  {t} <span className="text-white">{c}</span>
                </span>
              ))}
              {!stats?.by_type || Object.keys(stats.by_type).length === 0 ? (
                <span className="text-sm text-neutral-600">No active facts yet.</span>
              ) : null}
            </div>
          </div>
        </div>

        {/* Pending queue preview */}
        <div className="border border-[#262626]">
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626]">
            <h2 className="font-heading font-semibold text-lg">Pending Confirmation Queue</h2>
            <Link to="/app/pending" data-testid="view-pending" className="text-sm text-neutral-400 hover:text-white inline-flex items-center gap-1">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {pending.length === 0 ? (
            <div className="p-10 text-center text-neutral-600 text-sm">Nothing awaiting confirmation. High-stakes facts land here.</div>
          ) : (
            <div className="divide-y divide-[#262626]">
              {pending.slice(0, 4).map((f) => (
                <div key={f.id} className="flex items-center gap-4 px-6 py-3">
                  <TypeBadge type={f.type} />
                  <span className="font-mono text-sm text-neutral-300 flex-1 truncate">
                    {f.key.replace(/_/g, " ")}: <span className="text-white">{f.value}</span>
                  </span>
                  <StatusBadge status={f.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
