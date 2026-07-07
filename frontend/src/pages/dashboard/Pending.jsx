import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { TypeBadge } from "@/components/Badges";
import { toast } from "sonner";
import { Check, X, ShieldAlert } from "lucide-react";

export default function Pending() {
  const qc = useQueryClient();
  const { data: pending = [], isLoading } = useQuery({
    queryKey: ["pending"],
    queryFn: async () => (await client.get("/pending")).data,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["pending"] });
    qc.invalidateQueries({ queryKey: ["facts"] });
    qc.invalidateQueries({ queryKey: ["stats"] });
  };

  const confirm = useMutation({
    mutationFn: async (id) => (await client.post(`/facts/${id}/confirm`)).data,
    onSuccess: () => { toast.success("Fact confirmed"); invalidate(); },
  });
  const reject = useMutation({
    mutationFn: async (id) => (await client.post(`/facts/${id}/reject`)).data,
    onSuccess: () => { toast.success("Fact rejected"); invalidate(); },
  });

  return (
    <div>
      <PageHeader overline="High-stakes gating" title="Pending Confirmation Queue" testid="pending-header" />
      <div className="p-8">
        {isLoading ? (
          <div className="p-10 text-center text-neutral-600 text-sm">Loading…</div>
        ) : pending.length === 0 ? (
          <div className="border border-[#1F2A33] p-16 text-center" data-testid="pending-empty">
            <ShieldAlert className="w-8 h-8 mx-auto text-neutral-700 mb-3" />
            <p className="text-neutral-500">Queue is clear. Health, money and contact facts require your confirmation before going active.</p>
          </div>
        ) : (
          <div className="space-y-px bg-[#1F2A33] border border-[#1F2A33]" data-testid="pending-list">
            {pending.map((f) => (
              <div key={f.id} data-testid={`pending-${f.id}`} className="bg-[#0A0F14] p-5 flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-3 flex-1 min-w-[240px]">
                  <TypeBadge type={f.type} />
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">{f.key.replace(/_/g, " ")}</p>
                    <p className="text-white font-medium">{f.value}</p>
                  </div>
                </div>
                <span className="font-mono text-xs text-neutral-500">conf {Math.round(f.confidence * 100)}%</span>
                <div className="flex gap-2">
                  <button
                    data-testid={`confirm-${f.id}`}
                    onClick={() => confirm.mutate(f.id)}
                    className="inline-flex items-center gap-1.5 bg-emerald-500 text-black font-semibold px-4 py-2 text-sm hover:bg-emerald-400 transition-colors"
                  >
                    <Check className="w-4 h-4" /> Confirm
                  </button>
                  <button
                    data-testid={`reject-${f.id}`}
                    onClick={() => reject.mutate(f.id)}
                    className="inline-flex items-center gap-1.5 border border-red-500/50 text-red-400 px-4 py-2 text-sm hover:bg-red-950/40 transition-colors"
                  >
                    <X className="w-4 h-4" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
