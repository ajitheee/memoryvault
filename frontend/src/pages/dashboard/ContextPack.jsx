import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { toast } from "sonner";
import { Copy, Loader2, Play } from "lucide-react";

export default function ContextPack() {
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState(1000);
  const [pack, setPack] = useState(null);

  const run = useMutation({
    mutationFn: async () => (await client.post("/context-pack", { query, token_budget: Number(budget) })).data,
    onSuccess: (d) => setPack(d),
    onError: () => toast.error("Failed to build context pack"),
  });

  const copy = () => {
    navigator.clipboard.writeText(pack.context);
    toast.success("Context pack copied");
  };

  const pct = pack ? Math.min(100, Math.round((pack.tokens_used / pack.token_budget) * 100)) : 0;

  return (
    <div>
      <PageHeader overline="build_context_pack" title="Context Pack Preview" testid="context-header" />
      <div className="p-8 grid lg:grid-cols-2 gap-8">
        <div className="border border-[#262626] p-6 space-y-4 h-fit">
          <div>
            <label className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Query</label>
            <input
              data-testid="context-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What should the model know about me for this task?"
              className="mt-1 w-full bg-[#050505] border border-[#262626] px-3 py-2.5 text-sm outline-none focus:border-white transition-colors"
            />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Token budget — {budget}</label>
            <input
              data-testid="context-budget"
              type="range"
              min="100"
              max="4000"
              step="100"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="mt-2 w-full accent-white"
            />
          </div>
          <button
            data-testid="context-run"
            onClick={() => run.mutate()}
            disabled={!query.trim() || run.isPending}
            className="w-full inline-flex items-center justify-center gap-2 bg-white text-black font-semibold py-2.5 hover:bg-neutral-200 transition-colors disabled:opacity-50"
          >
            {run.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Building…</> : <><Play className="w-4 h-4" /> Build Pack</>}
          </button>
        </div>

        <div className="border border-[#262626] p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Output</p>
            {pack && (
              <button data-testid="context-copy" onClick={copy} className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors">
                <Copy className="w-3.5 h-3.5" /> Copy
              </button>
            )}
          </div>

          {!pack ? (
            <div className="py-16 text-center text-neutral-600 text-sm">Run a query to preview the token-budgeted context.</div>
          ) : (
            <div className="space-y-4" data-testid="context-output">
              <div>
                <div className="flex justify-between font-mono text-xs text-neutral-500 mb-1">
                  <span>{pack.tokens_used} / {pack.token_budget} tokens · {pack.facts_included} facts</span>
                  <span>{pct}%</span>
                </div>
                <div className="h-2 bg-[#262626]">
                  <div className={`h-full ${pct > 90 ? "bg-amber-500" : "bg-white"}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
              <pre className="bg-[#050505] border border-[#262626] p-4 font-mono text-xs text-neutral-300 whitespace-pre-wrap overflow-x-auto max-h-[420px] overflow-y-auto">
                {pack.context}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
