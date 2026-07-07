import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { toast } from "sonner";
import { Copy, RefreshCw, Download, Plug, Terminal } from "lucide-react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export default function Connect() {
  const qc = useQueryClient();
  const [revealed, setRevealed] = useState(false);

  const { data: info } = useQuery({
    queryKey: ["mcp-info"],
    queryFn: async () => (await client.get("/mcp/info")).data,
  });

  const regen = useMutation({
    mutationFn: async () => (await client.post("/mcp/token/regenerate")).data,
    onSuccess: () => { toast.success("MCP token regenerated"); qc.invalidateQueries({ queryKey: ["mcp-info"] }); },
  });

  const endpoint = `${BACKEND}/api/mcp`;
  const token = info?.mcp_token || "";

  const copy = (val, label) => {
    navigator.clipboard.writeText(val);
    toast.success(`${label} copied`);
  };

  const configSnippet = JSON.stringify(
    {
      mcpServers: {
        memoryvault: {
          type: "http",
          url: endpoint,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2
  );

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
      <PageHeader overline="Model Context Protocol" title="MCP Connect" testid="connect-header" />
      <div className="p-8 space-y-8 max-w-3xl">
        <div className="border border-[#262626] p-6">
          <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 mb-2 flex items-center gap-2"><Plug className="w-3.5 h-3.5" /> HTTP Endpoint</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#050505] border border-[#262626] px-3 py-2.5 font-mono text-sm text-neutral-300 break-all" data-testid="mcp-endpoint">{endpoint}</code>
            <button data-testid="copy-endpoint" onClick={() => copy(endpoint, "Endpoint")} className="border border-[#262626] p-2.5 hover:border-white/50 transition-colors"><Copy className="w-4 h-4" /></button>
          </div>
        </div>

        <div className="border border-[#262626] p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Vault MCP Token</p>
            <button data-testid="reveal-token" onClick={() => setRevealed((r) => !r)} className="text-xs text-neutral-400 hover:text-white">{revealed ? "Hide" : "Reveal"}</button>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#050505] border border-[#262626] px-3 py-2.5 font-mono text-sm text-neutral-300 break-all" data-testid="mcp-token">
              {revealed ? token : token.replace(/./g, "•").slice(0, 40)}
            </code>
            <button data-testid="copy-token" onClick={() => copy(token, "Token")} className="border border-[#262626] p-2.5 hover:border-white/50 transition-colors"><Copy className="w-4 h-4" /></button>
            <button data-testid="regen-token" onClick={() => regen.mutate()} className="border border-[#262626] p-2.5 hover:border-white/50 transition-colors"><RefreshCw className={`w-4 h-4 ${regen.isPending ? "animate-spin" : ""}`} /></button>
          </div>
          <p className="text-xs text-neutral-600 mt-2">Send as <span className="font-mono text-neutral-400">Authorization: Bearer &lt;token&gt;</span>. Regenerating invalidates old clients.</p>
        </div>

        <div className="border border-[#262626] p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-2"><Terminal className="w-3.5 h-3.5" /> Client config (Claude Desktop / Cursor)</p>
            <button data-testid="copy-config" onClick={() => copy(configSnippet, "Config")} className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white"><Copy className="w-3.5 h-3.5" /> Copy</button>
          </div>
          <pre className="bg-[#050505] border border-[#262626] p-4 font-mono text-xs text-neutral-300 overflow-x-auto" data-testid="mcp-config">{configSnippet}</pre>
          <p className="text-xs text-neutral-600 mt-3">Exposes tools: <span className="font-mono text-neutral-400">search_memory, get_profile, save_memory, build_context_pack, confirm_fact, list_pending</span>.</p>
        </div>

        <div className="border border-[#262626] p-6 flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="font-heading font-semibold text-lg">Data ownership</p>
            <p className="text-sm text-neutral-400">Full-fidelity JSON export of every event and fact.</p>
          </div>
          <button data-testid="connect-export" onClick={doExport} className="inline-flex items-center gap-2 bg-white text-black font-semibold px-5 py-2.5 hover:bg-neutral-200 transition-colors">
            <Download className="w-4 h-4" /> Export Vault
          </button>
        </div>
      </div>
    </div>
  );
}
