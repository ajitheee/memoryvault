import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { TypeBadge, StatusBadge } from "@/components/Badges";
import { toast } from "sonner";
import { Send, Loader2, Sparkles } from "lucide-react";

const SAMPLES = [
  "My name is Jordan and I prefer TypeScript over JavaScript. I work as a backend engineer.",
  "I just moved to Lisbon and I'm training for a marathon in October.",
  "My account balance is around 12k and my card ends in 4412.",
];

export default function Ingest() {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [role, setRole] = useState("user");
  const [result, setResult] = useState(null);

  const save = useMutation({
    mutationFn: async () => (await client.post("/memory/save", { text, role })).data,
    onSuccess: (d) => {
      setResult(d);
      setText("");
      toast.success(`Extracted ${d.extracted} fact(s) · ${d.pending} pending`);
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["pending"] });
      qc.invalidateQueries({ queryKey: ["facts"] });
    },
    onError: () => toast.error("Extraction failed"),
  });

  return (
    <div>
      <PageHeader overline="save_memory · L1 → L2" title="Ingest Memory" testid="ingest-header" />
      <div className="p-8 grid lg:grid-cols-2 gap-8">
        <div className="border border-[#1F2A33] p-6">
          <div className="flex items-center gap-2 mb-4">
            {["user", "assistant", "system"].map((r) => (
              <button
                key={r}
                data-testid={`role-${r}`}
                onClick={() => setRole(r)}
                className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider border transition-colors ${
                  role === r ? "bg-[#22D3EE] text-black border-[#22D3EE]" : "border-[#1F2A33] text-neutral-400 hover:text-white"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <textarea
            data-testid="ingest-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder="Paste a message. The LLM extractor will pull durable facts…"
            className="w-full bg-[#070B0F] border border-[#1F2A33] p-4 text-sm outline-none focus:border-[#22D3EE] transition-colors resize-none font-mono"
          />
          <button
            data-testid="ingest-submit"
            onClick={() => save.mutate()}
            disabled={!text.trim() || save.isPending}
            className="mt-4 w-full inline-flex items-center justify-center gap-2 bg-[#22D3EE] text-black font-semibold py-2.5 hover:bg-[#67E8F9] transition-colors disabled:opacity-50"
          >
            {save.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Extracting…</> : <><Send className="w-4 h-4" /> Ingest & Extract</>}
          </button>

          <div className="mt-5 space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5" /> Try a sample</p>
            {SAMPLES.map((s, i) => (
              <button
                key={i}
                data-testid={`sample-${i}`}
                onClick={() => setText(s)}
                className="block w-full text-left text-xs text-neutral-400 border border-[#1F2A33] p-2 hover:border-[#22D3EE]/40 hover:text-white transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="border border-[#1F2A33] p-6">
          <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 mb-4">Extraction result</p>
          {!result ? (
            <div className="py-16 text-center text-neutral-600 text-sm">Ingest a message to see extracted facts.</div>
          ) : (
            <div className="space-y-4" data-testid="ingest-result">
              <div className="flex gap-4 font-mono text-sm">
                <span className="text-neutral-400">extracted <span className="text-white">{result.extracted}</span></span>
                <span className="text-neutral-400">pending <span className="text-amber-400">{result.pending}</span></span>
                <span className="text-neutral-400">model <span className="text-white">{result.model}</span></span>
              </div>
              <div className="space-y-px bg-[#1F2A33] border border-[#1F2A33]">
                {result.facts.map((f) => (
                  <div key={f.id} className="bg-[#0A0F14] p-3 flex items-center gap-3">
                    <TypeBadge type={f.type} />
                    <span className="font-mono text-sm text-neutral-300 flex-1 truncate">
                      {f.key.replace(/_/g, " ")}: <span className="text-white">{f.value}</span>
                    </span>
                    <StatusBadge status={f.status} />
                  </div>
                ))}
                {result.facts.length === 0 && (
                  <div className="bg-[#0A0F14] p-4 text-sm text-neutral-600">No durable facts found in this message.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
