import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Database, GitBranch, Timer, ShieldCheck, Terminal, ArrowRight, Boxes } from "lucide-react";

const HERO_IMG =
  "https://images.unsplash.com/photo-1639066648921-82d4500abf1a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTV8MHwxfHNlYXJjaHwxfHxzZXJ2ZXIlMjByYWNrfGVufDB8fHxibGFja3wxNzgzNDUxOTI0fDA&ixlib=rb-4.1.0&q=85";

const MARQUEE = [
  "MODEL CONTEXT PROTOCOL",
  "CLAUDE DESKTOP",
  "CURSOR",
  "GPT APPS",
  "JSON EXPORT",
  "TEMPORAL SUPERSESSION",
  "EMBEDDING RETRIEVAL",
];

const FEATURES = [
  { icon: Terminal, title: "MCP Server", tag: "headline", body: "Standards-compliant tools — search_memory, get_profile, save_memory, build_context_pack, confirm_fact — over Streamable HTTP. Point any client at your vault." },
  { icon: GitBranch, title: "Layered Memory", tag: "L1 · L2 · L3", body: "Append-only event log, typed facts with temporal validity + supersession, and a rebuildable vector index." },
  { icon: Database, title: "LLM Fact Extraction", tag: "Claude Opus 4.5", body: "Structured extraction with confidence scoring. Health, money & contact facts are gated to a pending confirmation queue." },
  { icon: Timer, title: "Active Forgetting", tag: "decay", body: "Archive stale, low-confidence, unused facts on demand. Your vault stays lean and trustworthy over time." },
  { icon: ShieldCheck, title: "You Own It", tag: "export", body: "Full-fidelity JSON export of every event and fact. Portable, inspectable, yours — no lock-in." },
  { icon: Boxes, title: "Context Packs", tag: "token budget", body: "Get a token-budgeted context string ready to prepend to any model prompt, tuned to the person." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#F5F5F5]">
      {/* Nav */}
      <header className="border-b border-[#262626] sticky top-0 z-50 bg-[#0A0A0A]/80 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2" data-testid="brand-logo">
            <div className="w-6 h-6 border border-white flex items-center justify-center">
              <div className="w-2.5 h-2.5 bg-white" />
            </div>
            <span className="font-heading font-extrabold tracking-tight text-lg">MEMORYVAULT</span>
          </div>
          <nav className="flex items-center gap-2">
            <Link data-testid="nav-login" to="/login" className="px-4 py-2 text-sm text-neutral-300 hover:text-white transition-colors">Log in</Link>
            <Link data-testid="nav-signup" to="/signup" className="px-4 py-2 text-sm bg-white text-black font-semibold hover:bg-neutral-200 transition-colors">Initialize Vault</Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative border-b border-[#262626] overflow-hidden">
        <img src={HERO_IMG} alt="" className="absolute inset-0 w-full h-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0A0A0A]/50 via-[#0A0A0A]/70 to-[#0A0A0A]" />
        <div className="relative max-w-7xl mx-auto px-6 py-28 md:py-40">
          <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-400 mb-6">
            Production MCP · User-owned AI memory
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="font-heading font-black tracking-tighter leading-[0.95] text-5xl sm:text-7xl md:text-8xl max-w-4xl">
            A memory your AI<br />actually keeps.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="mt-8 text-base md:text-lg text-neutral-300 max-w-2xl leading-relaxed">
            MemoryVault ingests your interactions, extracts typed facts with confidence and provenance, handles supersession and decay, and serves a token-budgeted context pack to any model — over a real Model Context Protocol server.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }} className="mt-10 flex flex-wrap gap-3">
            <Link data-testid="hero-cta" to="/signup" className="group inline-flex items-center gap-2 px-6 py-3 bg-white text-black font-semibold hover:bg-neutral-200 transition-colors">
              Initialize Vault <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link data-testid="hero-login" to="/login" className="inline-flex items-center gap-2 px-6 py-3 border border-[#262626] hover:bg-[#141414] transition-colors">
              Log in
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Marquee */}
      <div className="border-b border-[#262626] overflow-hidden py-4 bg-[#0A0A0A]">
        <div className="flex whitespace-nowrap animate-marquee w-max">
          {[...MARQUEE, ...MARQUEE].map((m, i) => (
            <span key={i} className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-500 mx-8 flex items-center gap-8">
              {m} <span className="text-neutral-700">/</span>
            </span>
          ))}
        </div>
      </div>

      {/* Features bento */}
      <section className="max-w-7xl mx-auto px-6 py-24">
        <div className="flex items-end justify-between mb-12 flex-wrap gap-4">
          <h2 className="font-heading font-bold tracking-tight text-3xl sm:text-4xl max-w-lg">The engine behind portable memory.</h2>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-500">06 core systems</p>
        </div>
        <div className="grid md:grid-cols-3 gap-px bg-[#262626] border border-[#262626]">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              data-testid={`feature-${i}`}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#0A0A0A] p-8 hover:bg-[#111] transition-colors group"
            >
              <div className="flex items-center justify-between mb-6">
                <f.icon className="w-6 h-6 text-white" strokeWidth={1.5} />
                <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 border border-[#262626] px-2 py-0.5">{f.tag}</span>
              </div>
              <h3 className="font-heading font-bold text-xl mb-3">{f.title}</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Flow */}
      <section className="border-t border-[#262626] bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <h2 className="font-heading font-bold tracking-tight text-3xl sm:text-4xl mb-12">How it flows.</h2>
          <div className="grid md:grid-cols-4 gap-px bg-[#262626] border border-[#262626]">
            {[
              ["01", "Sign up", "Get an isolated vault + a per-vault MCP connection token."],
              ["02", "Connect", "Point Claude Desktop, Cursor or any MCP client at your vault."],
              ["03", "Remember", "save_memory ingests text; the LLM extracts typed facts."],
              ["04", "Recall", "search_memory & build_context_pack give continuity everywhere."],
            ].map(([n, t, b]) => (
              <div key={n} className="bg-[#0A0A0A] p-8">
                <div className="font-mono text-4xl font-bold text-[#262626] mb-4">{n}</div>
                <h3 className="font-heading font-semibold text-lg mb-2">{t}</h3>
                <p className="text-sm text-neutral-400 leading-relaxed">{b}</p>
              </div>
            ))}
          </div>
          <div className="mt-16 text-center">
            <Link data-testid="footer-cta" to="/signup" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-black font-semibold hover:bg-neutral-200 transition-colors">
              Start your vault — it's free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#262626]">
        <div className="max-w-7xl mx-auto px-6 py-8 flex items-center justify-between flex-wrap gap-4">
          <span className="font-mono text-xs text-neutral-600">MEMORYVAULT · MODEL CONTEXT PROTOCOL</span>
          <span className="font-mono text-xs text-neutral-600">L1 EVENTS · L2 FACTS · L3 INDEX</span>
        </div>
      </footer>
    </div>
  );
}
