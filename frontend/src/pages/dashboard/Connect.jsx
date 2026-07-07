import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { toast } from "sonner";
import { Copy, RefreshCw, Download, Plug, Terminal, CloudUpload, Package } from "lucide-react";

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

  const stdioSnippet = JSON.stringify(
    {
      mcpServers: {
        "memoryvault-local": {
          command: "python",
          args: ["/app/backend/mcp_stdio.py"],
          env: {
            MCP_TOKEN: token,
            MONGO_URL: "mongodb://localhost:27017",
            DB_NAME: "test_database",
            EMERGENT_LLM_KEY: "sk-emergent-...",
          },
        },
      },
    },
    null,
    2
  );

  const { data: bundles = [] } = useQuery({
    queryKey: ["export-bundles"],
    queryFn: async () => (await client.get("/export/bundles")).data,
  });

  const createBundle = useMutation({
    mutationFn: async () => (await client.post("/export/bundle")).data,
    onSuccess: () => { toast.success("Cloud export bundle created"); qc.invalidateQueries({ queryKey: ["export-bundles"] }); },
    onError: () => toast.error("Bundle creation failed"),
  });

  const downloadBundle = async (b) => {
    const res = await client.get(`/export/bundle/${b.id}/download`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `memoryvault-${b.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
        <div className="border border-[#1F2A33] p-6">
          <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 mb-2 flex items-center gap-2"><Plug className="w-3.5 h-3.5" /> HTTP Endpoint</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#070B0F] border border-[#1F2A33] px-3 py-2.5 font-mono text-sm text-neutral-300 break-all" data-testid="mcp-endpoint">{endpoint}</code>
            <button data-testid="copy-endpoint" onClick={() => copy(endpoint, "Endpoint")} className="border border-[#1F2A33] p-2.5 hover:border-[#22D3EE]/50 transition-colors"><Copy className="w-4 h-4" /></button>
          </div>
        </div>

        <div className="border border-[#1F2A33] p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">Vault MCP Token</p>
            <button data-testid="reveal-token" onClick={() => setRevealed((r) => !r)} className="text-xs text-neutral-400 hover:text-white">{revealed ? "Hide" : "Reveal"}</button>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#070B0F] border border-[#1F2A33] px-3 py-2.5 font-mono text-sm text-neutral-300 break-all" data-testid="mcp-token">
              {revealed ? token : token.replace(/./g, "•").slice(0, 40)}
            </code>
            <button data-testid="copy-token" onClick={() => copy(token, "Token")} className="border border-[#1F2A33] p-2.5 hover:border-[#22D3EE]/50 transition-colors"><Copy className="w-4 h-4" /></button>
            <button data-testid="regen-token" onClick={() => regen.mutate()} className="border border-[#1F2A33] p-2.5 hover:border-[#22D3EE]/50 transition-colors"><RefreshCw className={`w-4 h-4 ${regen.isPending ? "animate-spin" : ""}`} /></button>
          </div>
          <p className="text-xs text-neutral-600 mt-2">Send as <span className="font-mono text-neutral-400">Authorization: Bearer &lt;token&gt;</span>. Regenerating invalidates old clients.</p>
        </div>

        <div className="border border-[#1F2A33] p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-2"><Terminal className="w-3.5 h-3.5" /> Client config (Claude Desktop / Cursor)</p>
            <button data-testid="copy-config" onClick={() => copy(configSnippet, "Config")} className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white"><Copy className="w-3.5 h-3.5" /> Copy</button>
          </div>
          <pre className="bg-[#070B0F] border border-[#1F2A33] p-4 font-mono text-xs text-neutral-300 overflow-x-auto" data-testid="mcp-config">{configSnippet}</pre>
          <p className="text-xs text-neutral-600 mt-3">Exposes tools: <span className="font-mono text-neutral-400">search_memory, get_profile, save_memory, build_context_pack, confirm_fact, list_pending</span>.</p>
        </div>

        <div className="border border-[#1F2A33] p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 flex items-center gap-2"><Terminal className="w-3.5 h-3.5" /> Local stdio transport (fully offline)</p>
            <button data-testid="copy-stdio" onClick={() => copy(stdioSnippet, "Local config")} className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white"><Copy className="w-3.5 h-3.5" /> Copy</button>
          </div>
          <pre className="bg-[#070B0F] border border-[#1F2A33] p-4 font-mono text-xs text-neutral-300 overflow-x-auto" data-testid="mcp-stdio-config">{stdioSnippet}</pre>
          <p className="text-xs text-neutral-600 mt-3">Runs <span className="font-mono text-neutral-400">mcp_stdio.py</span> directly against your DB — no HTTP hop, privacy-first for local single-user setups. Replace <span className="font-mono text-amber-400/80">sk-emergent-...</span> with your actual Emergent LLM key.</p>
        </div>

        <div className="border border-[#1F2A33] p-6">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div>
              <p className="font-heading font-semibold text-lg flex items-center gap-2"><Package className="w-4 h-4" /> Cloud export bundles</p>
              <p className="text-sm text-neutral-400">Snapshot your full vault to object storage — durable, re-downloadable.</p>
            </div>
            <button data-testid="create-bundle" onClick={() => createBundle.mutate()} disabled={createBundle.isPending} className="inline-flex items-center gap-2 border border-[#1F2A33] px-4 py-2 text-sm hover:border-[#22D3EE]/50 transition-colors disabled:opacity-50">
              <CloudUpload className={`w-4 h-4 ${createBundle.isPending ? "animate-pulse" : ""}`} /> New Bundle
            </button>
          </div>
          {bundles.length === 0 ? (
            <p className="text-sm text-neutral-600">No cloud bundles yet.</p>
          ) : (
            <div className="divide-y divide-[#1F2A33] border border-[#1F2A33]" data-testid="bundles-list">
              {bundles.map((b) => (
                <div key={b.id} className="flex items-center gap-4 px-4 py-3">
                  <span className="font-mono text-[10px] text-neutral-600 shrink-0">{b.id.slice(0, 8)}</span>
                  <span className="font-mono text-xs text-neutral-500 flex-1 truncate">{new Date(b.created_at).toLocaleString()} · {b.facts} facts · {b.events} events · {(b.size / 1024).toFixed(1)} KB</span>
                  <button data-testid={`download-bundle-${b.id}`} onClick={() => downloadBundle(b)} className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors">
                    <Download className="w-3.5 h-3.5" /> Download
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border border-[#1F2A33] p-6 flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="font-heading font-semibold text-lg">Instant JSON export</p>
            <p className="text-sm text-neutral-400">Download the full vault right now, no storage round-trip.</p>
          </div>
          <button data-testid="connect-export" onClick={doExport} className="inline-flex items-center gap-2 bg-[#22D3EE] text-black font-semibold px-5 py-2.5 hover:bg-[#67E8F9] transition-colors">
            <Download className="w-4 h-4" /> Export Vault
          </button>
        </div>
      </div>
    </div>
  );
}
