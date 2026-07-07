import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatusBadge, TypeBadge, Confidence } from "@/components/Badges";
import { toast } from "sonner";
import { Check, X, Clock, GitBranch } from "lucide-react";

export default function FactDetail({ factId, onClose }) {
  const qc = useQueryClient();
  const { data: fact } = useQuery({
    queryKey: ["fact", factId],
    queryFn: async () => (await client.get(`/facts/${factId}`)).data,
    enabled: !!factId,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["facts"] });
    qc.invalidateQueries({ queryKey: ["pending"] });
    qc.invalidateQueries({ queryKey: ["stats"] });
  };

  const confirm = useMutation({
    mutationFn: async () => (await client.post(`/facts/${factId}/confirm`)).data,
    onSuccess: () => { toast.success("Fact confirmed"); invalidate(); onClose(); },
  });
  const reject = useMutation({
    mutationFn: async () => (await client.post(`/facts/${factId}/reject`)).data,
    onSuccess: () => { toast.success("Fact rejected & archived"); invalidate(); onClose(); },
  });

  return (
    <Sheet open={!!factId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="bg-[#0A0A0A] border-l border-[#262626] text-[#F5F5F5] w-full sm:max-w-md overflow-y-auto" data-testid="fact-detail">
        <SheetHeader>
          <SheetTitle className="font-heading text-xl text-white">Fact Detail</SheetTitle>
        </SheetHeader>

        {!fact ? (
          <div className="py-10 text-center text-neutral-600 text-sm">Loading…</div>
        ) : (
          <div className="mt-6 space-y-6">
            <div className="flex items-center gap-2 flex-wrap">
              <TypeBadge type={fact.type} />
              <StatusBadge status={fact.status} />
              {fact.high_stakes && (
                <span className="font-mono text-[10px] uppercase tracking-wider border border-amber-500/40 text-amber-400 bg-amber-500/10 px-2 py-0.5">high-stakes</span>
              )}
            </div>

            <div>
              <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 mb-1">{fact.key.replace(/_/g, " ")}</p>
              <p className="text-xl font-heading font-semibold">{fact.value}</p>
            </div>

            <div>
              <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 mb-2">Confidence</p>
              <Confidence value={fact.confidence} />
            </div>

            <div className="border-t border-[#262626] pt-4 space-y-3">
              <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-2"><Clock className="w-3.5 h-3.5" /> Provenance & Timeline</p>
              <div className="font-mono text-xs text-neutral-400 space-y-1.5">
                <Row k="fact_id" v={fact.id} />
                <Row k="model" v={fact.provenance?.model} />
                <Row k="source_role" v={fact.provenance?.role} />
                <Row k="event_id" v={fact.provenance?.event_id} />
                <Row k="valid_from" v={fact.valid_from} />
                <Row k="valid_to" v={fact.valid_to || "— (current)"} />
                <Row k="usage_count" v={String(fact.usage_count)} />
                <Row k="last_used" v={fact.last_used_at || "never"} />
              </div>
            </div>

            {(fact.supersedes?.length > 0 || fact.superseded_by) && (
              <div className="border-t border-[#262626] pt-4">
                <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-2 mb-2"><GitBranch className="w-3.5 h-3.5" /> Supersession</p>
                {fact.superseded_by && <p className="font-mono text-xs text-neutral-400">superseded_by: {fact.superseded_by}</p>}
                {fact.supersedes?.map((id) => (
                  <p key={id} className="font-mono text-xs text-neutral-400">supersedes: {id}</p>
                ))}
              </div>
            )}

            <div className="border-t border-[#262626] pt-4">
              <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 mb-2">Canonical Text</p>
              <div className="bg-[#050505] border border-[#262626] p-3 font-mono text-xs text-neutral-400">{fact.canonical_text}</div>
            </div>

            {fact.status === "pending" && (
              <div className="flex gap-2 border-t border-[#262626] pt-4">
                <button
                  data-testid="confirm-fact-button"
                  onClick={() => confirm.mutate()}
                  disabled={confirm.isPending}
                  className="flex-1 inline-flex items-center justify-center gap-2 bg-emerald-500 text-black font-semibold py-2.5 hover:bg-emerald-400 transition-colors disabled:opacity-60"
                >
                  <Check className="w-4 h-4" /> Confirm
                </button>
                <button
                  data-testid="reject-fact-button"
                  onClick={() => reject.mutate()}
                  disabled={reject.isPending}
                  className="flex-1 inline-flex items-center justify-center gap-2 border border-red-500/50 text-red-400 py-2.5 hover:bg-red-950/40 transition-colors disabled:opacity-60"
                >
                  <X className="w-4 h-4" /> Reject
                </button>
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex gap-2">
      <span className="text-neutral-600 shrink-0">{k}:</span>
      <span className="text-neutral-300 break-all">{v}</span>
    </div>
  );
}
