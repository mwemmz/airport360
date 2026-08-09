import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ErrorMessage } from "../components/ui";

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
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Airport360</h1>
          <p className="text-sm text-slate-500 mt-1">
            ZACL Digital Transformation Platform
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Simulated/anonymized data — Phase 1: HR · Procurement · Finance · BI · Capacity Building
          </p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <input
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <ErrorMessage message={error} />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="mt-6 rounded-md bg-slate-50 border border-slate-200 p-3 text-xs text-slate-500">
          <div className="font-semibold text-slate-600 mb-1">Demo accounts (password: Demo1234!)</div>
          <div>admin.ku@airport360.com · Administrator</div>
          <div>executive.ku@airport360.com · Executive</div>
          <div>hr.ku@airport360.com · HR Officer (site 1)</div>
          <div>finance.ku@airport360.com · Finance Officer (site 1)</div>
          <div>depthead.ku@airport360.com · Department Head (site 1)</div>
          <div>staff.ku@airport360.com · Staff (site 1)</div>
          <div>hr.nm@airport360.com · HR Officer (site 2)</div>
        </div>
      </div>
    </div>
  );
}
