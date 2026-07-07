import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ArrowRight, Loader2 } from "lucide-react";

export default function Auth({ mode = "login" }) {
  const isSignup = mode === "signup";
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = isSignup
      ? await register(email, password, name)
      : await login(email, password);
    setLoading(false);
    if (res.ok) navigate("/app");
    else setError(res.error);
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#F5F5F5] grid-bg flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-10 justify-center" data-testid="auth-brand">
          <div className="w-6 h-6 border border-white flex items-center justify-center">
            <div className="w-2.5 h-2.5 bg-white" />
          </div>
          <span className="font-heading font-extrabold tracking-tight text-lg">MEMORYVAULT</span>
        </Link>

        <div className="border border-[#262626] bg-[#0A0A0A] p-8">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-500 mb-2">
            {isSignup ? "Initialize" : "Access"}
          </p>
          <h1 className="font-heading font-bold text-2xl mb-6">
            {isSignup ? "Create your vault" : "Enter your vault"}
          </h1>

          <form onSubmit={submit} className="space-y-4">
            {isSignup && (
              <div>
                <label className="font-mono text-xs uppercase tracking-wider text-neutral-500">Name</label>
                <input
                  data-testid="auth-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 w-full bg-[#111] border border-[#262626] px-3 py-2.5 text-sm outline-none focus:border-white transition-colors"
                  placeholder="Alex Rivera"
                />
              </div>
            )}
            <div>
              <label className="font-mono text-xs uppercase tracking-wider text-neutral-500">Email</label>
              <input
                data-testid="auth-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full bg-[#111] border border-[#262626] px-3 py-2.5 text-sm outline-none focus:border-white transition-colors"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="font-mono text-xs uppercase tracking-wider text-neutral-500">Password</label>
              <input
                data-testid="auth-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full bg-[#111] border border-[#262626] px-3 py-2.5 text-sm outline-none focus:border-white transition-colors"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div data-testid="auth-error" className="border border-red-500/40 bg-red-500/10 text-red-400 text-sm px-3 py-2 font-mono">
                {error}
              </div>
            )}

            <button
              data-testid="auth-submit"
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-white text-black font-semibold py-2.5 hover:bg-neutral-200 transition-colors disabled:opacity-60"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>{isSignup ? "Initialize Vault" : "Log in"} <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-neutral-500 mt-6">
          {isSignup ? "Already have a vault? " : "No vault yet? "}
          <Link
            data-testid="auth-toggle"
            to={isSignup ? "/login" : "/signup"}
            className="text-white underline underline-offset-4 hover:text-neutral-300"
          >
            {isSignup ? "Log in" : "Initialize one"}
          </Link>
        </p>
      </div>
    </div>
  );
}
