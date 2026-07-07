import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { StatusBadge, TypeBadge, Confidence } from "@/components/Badges";
import FactDetail from "./FactDetail";

const TABS = ["active", "pending", "superseded", "archived", "all"];

export default function Facts() {
  const [status, setStatus] = useState("active");
  const [selected, setSelected] = useState(null);

  const { data: facts = [], isLoading } = useQuery({
    queryKey: ["facts", status],
    queryFn: async () => (await client.get(`/facts?status=${status}`)).data,
  });

  return (
    <div>
      <PageHeader overline="Layer 2" title="Fact Browser" testid="facts-header" />

      <div className="px-8 pt-6">
        <div className="flex gap-px bg-[#1F2A33] border border-[#1F2A33] w-fit">
          {TABS.map((t) => (
            <button
              key={t}
              data-testid={`tab-${t}`}
              onClick={() => setStatus(t)}
              className={`px-4 py-2 text-sm font-mono uppercase tracking-wider transition-colors ${
                status === t ? "bg-[#22D3EE] text-black" : "bg-[#0A0F14] text-neutral-400 hover:text-white"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="p-8">
        <div className="border border-[#1F2A33]">
          <div className="grid grid-cols-[110px_1fr_140px_120px] gap-4 px-4 py-3 border-b border-[#1F2A33] font-mono text-[10px] uppercase tracking-wider text-neutral-500">
            <span>Type</span>
            <span>Fact</span>
            <span>Confidence</span>
            <span>Status</span>
          </div>
          {isLoading ? (
            <div className="p-10 text-center text-neutral-600 text-sm">Loading…</div>
          ) : facts.length === 0 ? (
            <div className="p-10 text-center text-neutral-600 text-sm" data-testid="facts-empty">No {status} facts.</div>
          ) : (
            <div className="divide-y divide-[#1F2A33]" data-testid="facts-list">
              {facts.map((f) => (
                <button
                  key={f.id}
                  data-testid={`fact-row-${f.id}`}
                  onClick={() => setSelected(f.id)}
                  className="w-full grid grid-cols-[110px_1fr_140px_120px] gap-4 px-4 py-3 items-center text-left hover:bg-[#111820] transition-colors"
                >
                  <TypeBadge type={f.type} />
                  <span className="font-mono text-sm text-neutral-300 truncate">
                    {f.key.replace(/_/g, " ")}: <span className="text-white">{f.value}</span>
                  </span>
                  <Confidence value={f.confidence} />
                  <StatusBadge status={f.status} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <FactDetail factId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
