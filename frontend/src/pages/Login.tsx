import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ErrorMessage } from "../components/ui";
import { Lock, Mail, Plane, ShieldCheck, Sparkles, KeyRound } from "lucide-react";

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-slate-950">
      {/* Hero panel */}
      <div className="hidden lg:flex w-1/2 relative overflow-hidden bg-slate-950 flex-col justify-between p-12">
        <div className="absolute inset-0 bg-grid pointer-events-none" />
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-indigo-600/30 blur-3xl animate-floaty" />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-blue-600/20 blur-3xl animate-floaty" style={{ animationDelay: "2s" }} />
        <div className="absolute top-1/3 right-1/4 w-64 h-64 rounded-full bg-cyan-500/15 blur-3xl animate-floaty" style={{ animationDelay: "4s" }} />

        <div className="relative flex items-center gap-3 animate-fade-in">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-glow">
            <Plane className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="text-2xl font-extrabold tracking-tight text-white leading-none">Airport360</div>
            <div className="text-sm text-slate-400 mt-1">ZACL Digital Transformation Platform</div>
          </div>
        </div>

        <div className="relative max-w-md animate-fade-in-up">
          <h1 className="text-4xl font-extrabold tracking-tight text-white leading-tight">
            One platform for the <span className="text-gradient">modern airport</span>.
          </h1>
          <p className="mt-4 text-slate-400 leading-relaxed">
            HR, Procurement, Finance, BI and Capacity Building — unified with AI-assisted
            decision support, simulated on anonymized data.
          </p>
          <div className="mt-8 space-y-3">
            {[
              { icon: Sparkles, text: "AI Assistant with rule-driven recommendations" },
              { icon: ShieldCheck, text: "Role-based access across 18 modules" },
              { icon: KeyRound, text: "Multi-site operations & capacity building" },
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-3 text-sm text-slate-300">
                <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                  <f.icon className="w-4 h-4 text-indigo-400" />
                </div>
                {f.text}
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-xs text-slate-500 animate-fade-in">
          Phase 1 · Simulated/anonymized data · © 2026 Airport360
        </div>
      </div>

      {/* Form panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 relative">
        <div className="absolute inset-0 bg-dots opacity-50 pointer-events-none lg:hidden" />
        <div className="w-full max-w-md relative animate-fade-in-up">
          <div className="lg:hidden flex items-center gap-2.5 mb-8 justify-center">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-glow">
              <Plane className="w-5 h-5 text-white" />
            </div>
            <div className="text-xl font-extrabold text-white">Airport360</div>
          </div>

          <div className="bg-white rounded-2xl shadow-2xl shadow-indigo-950/40 p-8 border border-white/10">
            <div className="mb-6">
              <h2 className="text-2xl font-extrabold text-slate-900">Welcome back</h2>
              <p className="text-sm text-slate-500 mt-1">Sign in to continue to your dashboard</p>
            </div>

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">Email address</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    className="input pl-10"
                    placeholder="you@airport360.com"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    className="input pl-10"
                    placeholder="••••••••"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              <ErrorMessage message={error} />

              <button
                type="submit"
                disabled={busy}
                className="btn-primary w-full disabled:opacity-70"
              >
                {busy ? (
                  <>
                    <span className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                    Signing in…
                  </>
                ) : (
                  "Sign in"
                )}
              </button>
            </form>

            <div className="mt-6 rounded-xl bg-slate-50 border border-slate-200 p-3.5 text-xs text-slate-500">
              <div className="font-bold text-slate-600 mb-2 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5" /> Demo accounts · password: Demo1234!
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
                <div>admin.ku@airport360.com</div>
                <div className="text-slate-400">Administrator</div>
                <div>executive.ku@airport360.com</div>
                <div className="text-slate-400">Executive</div>
                <div>hr.ku@airport360.com</div>
                <div className="text-slate-400">HR Officer · site 1</div>
                <div>finance.ku@airport360.com</div>
                <div className="text-slate-400">Finance Officer · site 1</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
