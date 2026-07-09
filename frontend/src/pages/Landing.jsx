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
    <div className="min-h-screen bg-[#0A0F14] text-[#F5F5F5]">
      {/* Nav */}
      <header className="border-b border-[#1F2A33] sticky top-0 z-50 bg-[#0A0F14]/80 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2" data-testid="brand-logo">
            <div className="w-6 h-6 border border-[#22D3EE] flex items-center justify-center">
              <div className="w-2.5 h-2.5 bg-[#22D3EE]" />
            </div>
            <span className="font-heading font-extrabold tracking-tight text-lg">MEMORYVAULT</span>
          </div>
          <nav className="flex items-center gap-2">
            <Link data-testid="nav-login" to="/login" className="px-4 py-2 text-sm text-neutral-300 hover:text-white transition-colors">Log in</Link>
            <Link data-testid="nav-signup" to="/signup" className="px-4 py-2 text-sm bg-[#22D3EE] text-black font-semibold hover:bg-[#67E8F9] transition-colors">Initialize Vault</Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative border-b border-[#1F2A33] overflow-hidden">
        <img src={HERO_IMG} alt="" className="absolute inset-0 w-full h-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0A0F14]/50 via-[#0A0F14]/70 to-[#0A0F14]" />
        <div className="relative max-w-7xl mx-auto px-6 py-28 md:py-40">
          <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-400 mb-6">
            User-owned AI memory
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="font-heading font-black tracking-tighter leading-[0.95] text-5xl sm:text-7xl md:text-8xl max-w-4xl">
            Your AI forgets you<br />every morning.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="mt-8 text-base md:text-lg text-neutral-300 max-w-2xl leading-relaxed">
            You've told it your name, your work, your allergies, the way you like your answers — a hundred times. MemoryVault remembers for you, in a vault <span className="text-white font-medium">you own and can carry to any AI</span>. Not a chatbot's private notebook — a portable memory that's yours to read, correct, and take with you.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }} className="mt-10 flex flex-wrap gap-3">
            <Link data-testid="hero-cta" to="/signup" className="group inline-flex items-center gap-2 px-6 py-3 bg-[#22D3EE] text-black font-semibold hover:bg-[#67E8F9] transition-colors">
              Initialize Vault <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link data-testid="hero-login" to="/login" className="inline-flex items-center gap-2 px-6 py-3 border border-[#1F2A33] hover:bg-[#111820] transition-colors">
              Log in
            </Link>
          </motion.div>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.26 }} className="mt-10 font-mono text-xs uppercase tracking-[0.2em] text-neutral-500">
            Your photos move with you · your money moves with you · your memory should too
          </motion.p>
        </div>
      </section>

      {/* Manifesto */}
      <section className="border-b border-[#1F2A33] bg-[#0A0F14]">
        <div className="max-w-4xl mx-auto px-6 py-24">
          <p className="font-heading text-2xl sm:text-3xl md:text-4xl leading-snug tracking-tight text-neutral-200">
            When AI finally learns to remember you, read the fine print: it remembers you inside <span className="text-neutral-500">someone else's walls</span>. Years of teaching it who you are — your work, your habits, the way you think — gone with a policy change, a billing error, or a border.
            <br /><br />
            <span className="text-white">You didn't build a memory. You rented one.</span> MemoryVault gives it back: what a machine knows about you should be a file you own — inspectable, correctable, portable to any model you choose.
          </p>
        </div>
      </section>

      {/* Marquee */}
      <div className="border-b border-[#1F2A33] overflow-hidden py-4 bg-[#0A0F14]">
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
        <div className="grid md:grid-cols-3 gap-px bg-[#1F2A33] border border-[#1F2A33]">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              data-testid={`feature-${i}`}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#0A0F14] p-8 hover:bg-[#111820] transition-colors group"
            >
              <div className="flex items-center justify-between mb-6">
                <f.icon className="w-6 h-6 text-white" strokeWidth={1.5} />
                <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-500 border border-[#1F2A33] px-2 py-0.5">{f.tag}</span>
              </div>
              <h3 className="font-heading font-bold text-xl mb-3">{f.title}</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Flow */}
      <section className="border-t border-[#1F2A33] bg-[#0A0F14]">
        <div className="max-w-7xl mx-auto px-6 py-24">
          <h2 className="font-heading font-bold tracking-tight text-3xl sm:text-4xl mb-12">How it flows.</h2>
          <div className="grid md:grid-cols-4 gap-px bg-[#1F2A33] border border-[#1F2A33]">
            {[
              ["01", "Sign up", "Get an isolated vault + a per-vault MCP connection token."],
              ["02", "Connect", "Point Claude Desktop, Cursor or any MCP client at your vault."],
              ["03", "Remember", "save_memory ingests text; the LLM extracts typed facts."],
              ["04", "Recall", "search_memory & build_context_pack give continuity everywhere."],
            ].map(([n, t, b]) => (
              <div key={n} className="bg-[#0A0F14] p-8">
                <div className="font-mono text-4xl font-bold text-[#1F2A33] mb-4">{n}</div>
                <h3 className="font-heading font-semibold text-lg mb-2">{t}</h3>
                <p className="text-sm text-neutral-400 leading-relaxed">{b}</p>
              </div>
            ))}
          </div>
          <div className="mt-16 text-center">
            <Link data-testid="footer-cta" to="/signup" className="inline-flex items-center gap-2 px-8 py-4 bg-[#22D3EE] text-black font-semibold hover:bg-[#67E8F9] transition-colors">
              Start your vault — it's free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#1F2A33]">
        <div className="max-w-7xl mx-auto px-6 py-8 flex items-center justify-between flex-wrap gap-4">
          <span className="font-mono text-xs text-neutral-600">MEMORYVAULT · MODEL CONTEXT PROTOCOL</span>
          <span className="font-mono text-xs text-neutral-600">L1 EVENTS · L2 FACTS · L3 INDEX</span>
        </div>
      </footer>
    </div>
  );
}
