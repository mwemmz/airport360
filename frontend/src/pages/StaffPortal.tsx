import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE } from "../api";
import { Badge, Card, ErrorMessage, Loading } from "../components/ui";
import {
  CalendarDays,
  ClipboardList,
  Clock,
  Fingerprint,
  LogOut,
  Plane,
  ShieldCheck,
} from "lucide-react";

const PORTAL_TOKEN_KEY = "airport360_staff_portal_token";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type HomeData = {
  employee: { id: number; employee_number: string; first_name: string; last_name: string; job_title: string };
  today: { date: string; clock_in: string | null; clock_out: string | null; clocked_in: boolean };
  upcoming_shifts: number;
  next_shift: string | null;
  open_cases: number;
  balance: BalanceRow[];
};

type BalanceRow = {
  leave_type_id: number;
  leave_type: string;
  leave_type_code: string;
  year: number;
  available_days: number;
  taken_days: number;
};

type ShiftRow = {
  assignment_id: number;
  work_date: string;
  status: string;
  shift: { id: number; name: string; start_time: string; end_time: string; is_night: boolean };
};

type LeaveType = {
  id: number;
  code: string;
  name: string;
  category: string;
  paid: boolean;
  accrual_days_per_month: number;
  grant_days_per_year: number | null;
};

type CaseRow = {
  id: number;
  case_number: string;
  category: string;
  severity: string;
  status: string;
  title: string;
  opened_at: string;
};

/* ------------------------------------------------------------------ */
/* Local API helper (shared-terminal token, separate from the main app) */
/* ------------------------------------------------------------------ */

function kapi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = localStorage.getItem(PORTAL_TOKEN_KEY);
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(`${API_BASE}/v1${path}`, { ...options, headers }).then(async (resp) => {
    if (resp.status === 401) {
      localStorage.removeItem(PORTAL_TOKEN_KEY);
      window.location.reload();
      throw new Error("Session expired");
    }
    if (!resp.ok) {
      let detail = `Request failed (${resp.status})`;
      try {
        const body = await resp.json();
        detail = Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : body.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return resp.json() as Promise<T>;
  });
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
}

/* ------------------------------------------------------------------ */
/* Login screen                                                        */
/* ------------------------------------------------------------------ */

function StaffPortalLogin({ onLogin }: { onLogin: () => void }) {
  const [employeeNumber, setEmployeeNumber] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await kapi<{ access_token: string }>("/auth/staff-portal", {
        method: "POST",
        body: JSON.stringify({ employee_number: employeeNumber, pin }),
      });
      localStorage.setItem(PORTAL_TOKEN_KEY, data.access_token);
      onLogin();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 bg-grid pointer-events-none" />
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-indigo-600/30 blur-3xl animate-floaty" />
      <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-cyan-500/15 blur-3xl animate-floaty" style={{ animationDelay: "2s" }} />

      <div className="relative w-full max-w-md mx-auto flex flex-col items-center justify-center p-6">
        <div className="w-full bg-white rounded-2xl shadow-2xl shadow-indigo-950/40 p-8 border border-white/10 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-glow">
              <Plane className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-xl font-extrabold tracking-tight text-slate-900 leading-none">Staff Portal</div>
              <div className="text-xs text-slate-500 mt-1">Shared shift terminal</div>
            </div>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">Employee number</label>
              <div className="relative">
                <ClipboardList className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  className="input pl-10"
                  placeholder="EMP-KU-1009"
                  value={employeeNumber}
                  onChange={(e) => setEmployeeNumber(e.target.value)}
                  autoFocus
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">PIN</label>
              <div className="relative">
                <Fingerprint className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  className="input pl-10 tracking-[0.3em]"
                  placeholder="••••"
                  type="password"
                  inputMode="numeric"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  required
                />
              </div>
            </div>

            <ErrorMessage message={error} />

            <button type="submit" disabled={busy} className="btn-primary w-full disabled:opacity-70">
              {busy ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  Checking…
                </>
              ) : (
                "Clock in to the portal"
              )}
            </button>
          </form>

          <div className="mt-5 rounded-xl bg-slate-50 border border-slate-200 p-3.5 text-xs text-slate-500">
            <div className="font-bold text-slate-600 mb-1 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" /> Frontline Staff only · demo
            </div>
            <div>Employee <span className="font-mono">EMP-KU-1009</span> · PIN <span className="font-mono">1234</span></div>
          </div>

          <Link to="/login" className="block mt-4 text-center text-xs font-semibold text-indigo-600 hover:text-indigo-700">
            ← Back to the full sign-in
          </Link>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Clock widget                                                        */
/* ------------------------------------------------------------------ */

function ClockWidget({ home, onChanged }: { home: HomeData; onChanged: () => void }) {
  const [busy, setBusy] = useState<"in" | "out" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function toggle(action: "in" | "out") {
    setBusy(action);
    setMessage(null);
    try {
      await kapi("/staff-portal/clock", { method: "POST", body: JSON.stringify({ action }) });
      setMessage(action === "in" ? "Clocked in — have a good shift." : "Clocked out — see you next shift.");
      onChanged();
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card
      title="Today"
      actions={
        <Badge tone={home.today.clocked_in ? "green" : "slate"} dot>
          {home.today.clocked_in ? "On duty" : "Not clocked in"}
        </Badge>
      }
    >
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-center">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Clock in</div>
          <div className="mt-1 text-2xl font-extrabold text-slate-900 tabular-nums">{fmtTime(home.today.clock_in)}</div>
        </div>
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-center">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Clock out</div>
          <div className="mt-1 text-2xl font-extrabold text-slate-900 tabular-nums">{fmtTime(home.today.clock_out)}</div>
        </div>
      </div>

      {message && (
        <div className="mb-4 text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">{message}</div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => toggle("in")}
          disabled={busy !== null || home.today.clocked_in}
          className="btn-primary disabled:opacity-50"
        >
          {busy === "in" ? "…" : <><Clock className="w-4 h-4" /> Clock in</>}
        </button>
        <button
          onClick={() => toggle("out")}
          disabled={busy !== null || !home.today.clocked_in}
          className="btn-disabled disabled:opacity-50"
        >
          {busy === "out" ? "…" : "Clock out"}
        </button>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Dashboard                                                           */
/* ------------------------------------------------------------------ */

const CASE_CATEGORIES = ["grievance", "disciplinary", "harassment", "performance", "wellness", "attendance", "other"];
const CASE_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function StaffPortalDashboard({ onLogout }: { onLogout: () => void }) {
  const [tab, setTab] = useState<"today" | "shifts" | "leave" | "cases">("today");
  const [home, setHome] = useState<HomeData | null>(null);
  const [shifts, setShifts] = useState<ShiftRow[] | null>(null);
  const [types, setTypes] = useState<LeaveType[] | null>(null);
  const [cases, setCases] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadHome() {
    try {
      setHome(await kapi<HomeData>("/staff-portal/home"));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function load() {
    setError(null);
    const [h, s, t, c] = await Promise.all([
      kapi<HomeData>("/staff-portal/home"),
      kapi<ShiftRow[]>("/staff-portal/shifts"),
      kapi<LeaveType[]>("/staff-portal/leave-types"),
      kapi<CaseRow[]>("/staff-portal/cases"),
    ]);
    setHome(h);
    setShifts(s);
    setTypes(t);
    setCases(c);
  }

  useEffect(() => {
    load().catch((e) => setError((e as Error).message));
  }, []);

  const balance = home?.balance ?? [];

  const tabs: { id: typeof tab; label: string }[] = [
    { id: "today", label: "Today" },
    { id: "shifts", label: `Shifts${home && home.upcoming_shifts > 0 ? ` (${home.upcoming_shifts})` : ""}` },
    { id: "leave", label: "Leave" },
    { id: "cases", label: `My cases${home && home.open_cases > 0 ? ` (${home.open_cases})` : ""}` },
  ];

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 bg-grid pointer-events-none" />
      <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-indigo-600/25 blur-3xl animate-blob" />
      <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-cyan-500/15 blur-3xl animate-blob" style={{ animationDelay: "2.5s" }} />

      <div className="relative max-w-4xl mx-auto p-4 md:p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-glow">
              <Plane className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-lg font-extrabold tracking-tight text-white leading-none">Staff Portal</div>
              {home && (
                <div className="text-xs text-slate-400 mt-1">
                  {home.employee.first_name} {home.employee.last_name} · {home.employee.job_title} · {home.employee.employee_number}
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" /> Sign out
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap animate-fade-in">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                tab === t.id
                  ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-900/40"
                  : "bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {error && <ErrorMessage message={error} />}

        {!home ? (
          <Loading label="Loading portal…" />
        ) : tab === "today" ? (
          <div className="grid gap-4 md:grid-cols-2 animate-fade-in-up">
            <ClockWidget home={home} onChanged={loadHome} />
            <Card title="Quick status">
              <ul className="space-y-3 text-sm">
                <li className="flex items-center justify-between">
                  <span className="text-slate-500">Upcoming shifts</span>
                  <span className="font-bold text-slate-800">{home.upcoming_shifts}</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="text-slate-500">Next shift</span>
                  <span className="font-bold text-slate-800">{fmtDate(home.next_shift)}</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="text-slate-500">Open HR cases</span>
                  <span className="font-bold text-slate-800">{home.open_cases}</span>
                </li>
              </ul>
              <div className="mt-4 pt-4 border-t border-slate-100">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">Leave balance</div>
                <div className="space-y-2">
                  {balance.map((b) => (
                    <div key={b.leave_type_id} className="flex items-center justify-between text-sm">
                      <span className="text-slate-600">{b.leave_type}</span>
                      <span className="font-bold text-slate-800 tabular-nums">{b.available_days} d</span>
                    </div>
                  ))}
                  {balance.length === 0 && <div className="text-xs text-slate-400">No leave balances yet.</div>}
                </div>
              </div>
            </Card>
          </div>
        ) : tab === "shifts" ? (
          <ShiftsTab shifts={shifts} />
        ) : tab === "leave" ? (
          <LeaveTab types={types} employeeId={home.employee.id} onChanged={load} />
        ) : (
          <CasesTab cases={cases} employeeId={home.employee.id} onChanged={load} />
        )}
      </div>
    </div>
  );
}

function ShiftsTab({ shifts }: { shifts: ShiftRow[] | null }) {
  if (!shifts) return <Loading label="Loading shifts…" />;
  if (shifts.length === 0) {
    return (
      <Card>
        <div className="text-center py-10">
          <CalendarDays className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <div className="text-sm font-semibold text-slate-500">No upcoming shifts</div>
        </div>
      </Card>
    );
  }
  return (
    <div className="space-y-3 animate-fade-in-up">
      {shifts.map((s) => (
        <Card key={s.assignment_id} title={fmtDate(s.work_date)} actions={<Badge tone={s.status === "Assigned" ? "blue" : "slate"}>{s.status}</Badge>}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-xs">
              {s.shift.is_night ? "NIGHT" : "DAY"}
            </div>
            <div>
              <div className="font-bold text-slate-800">{s.shift.name}</div>
              <div className="text-sm text-slate-500 tabular-nums">
                {s.shift.start_time.slice(0, 5)} – {s.shift.end_time.slice(0, 5)}
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function LeaveTab({ types, employeeId, onChanged }: { types: LeaveType[] | null; employeeId: number; onChanged: () => void }) {
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [balance, setBalance] = useState<BalanceRow[] | null>(null);

  useEffect(() => {
    kapi<BalanceRow[]>("/staff-portal/balance").then(setBalance).catch(() => setBalance([]));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget as HTMLFormElement);
    setBusy(true);
    setMessage(null);
    try {
      const r = await kapi<{ request_number: string; status: string }>("/staff-portal/leave", {
        method: "POST",
        body: JSON.stringify({
          employee_id: employeeId,
          leave_type_id: Number(fd.get("leave_type_id")),
          start_date: fd.get("start_date"),
          end_date: fd.get("end_date"),
          reason: fd.get("reason") || null,
        }),
      });
      setMessage(`Request ${r.request_number} submitted (${r.status}).`);
      onChanged();
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!types) return <Loading label="Loading leave types…" />;

  const minToday = new Date().toISOString().slice(0, 10);

  return (
    <div className="grid gap-4 md:grid-cols-2 animate-fade-in-up">
      <Card title="Request leave">
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Leave type</label>
            <select name="leave_type_id" className="input" required>
              {types.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} {t.accrual_days_per_month === 0 ? "· " + (t.grant_days_per_year ?? 0) + " days/year" : `· ${t.accrual_days_per_month} days/month`}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">From</label>
              <input name="start_date" type="date" className="input" min={minToday} required />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">To</label>
              <input name="end_date" type="date" className="input" min={minToday} required />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Reason (optional)</label>
            <textarea name="reason" rows={2} className="input resize-none" placeholder="Brief note for HR" />
          </div>
          {message && <div className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">{message}</div>}
          <button type="submit" disabled={busy} className="btn-primary w-full disabled:opacity-70">
            {busy ? "Submitting…" : "Submit request"}
          </button>
        </form>
      </Card>

      <Card title="Your balance">
        {balance === null ? (
          <Loading label="Loading balance…" />
        ) : balance.length === 0 ? (
          <div className="text-sm text-slate-500">No leave balances yet.</div>
        ) : (
          <div className="space-y-2">
            {balance.map((b) => (
              <div key={b.leave_type_id} className="flex items-center justify-between rounded-xl bg-slate-50 border border-slate-200 px-4 py-3">
                <div>
                  <div className="font-bold text-slate-800">{b.leave_type}</div>
                  <div className="text-[11px] text-slate-400">{b.year} · {b.taken_days} taken</div>
                </div>
                <Badge tone={b.available_days > 0 ? "green" : "red"}>{b.available_days} days</Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function CasesTab({ cases, employeeId, onChanged }: { cases: CaseRow[] | null; employeeId: number; onChanged: () => void }) {
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget as HTMLFormElement);
    setBusy(true);
    setMessage(null);
    try {
      const r = await kapi<{ case_number: string; status: string }>("/staff-portal/case", {
        method: "POST",
        body: JSON.stringify({
          employee_id: employeeId,
          category: fd.get("category"),
          severity: fd.get("severity"),
          title: fd.get("title"),
          description: fd.get("description") || null,
        }),
      });
      setMessage(`Case ${r.case_number} opened (${r.status}).`);
      onChanged();
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 animate-fade-in-up">
      <Card title="Raise an HR case">
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">Category</label>
              <select name="category" className="input" defaultValue="other">
                {CASE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">Severity</label>
              <select name="severity" className="input" defaultValue="MEDIUM">
                {CASE_SEVERITIES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Title</label>
            <input name="title" className="input" placeholder="Brief summary" required />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Details (optional)</label>
            <textarea name="description" rows={3} className="input resize-none" placeholder="What happened, when, who was involved…" />
          </div>
          {message && <div className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">{message}</div>}
          <button type="submit" disabled={busy} className="btn-primary w-full disabled:opacity-70">
            {busy ? "Opening…" : "Open case"}
          </button>
        </form>
      </Card>

      <Card title="Your cases">
        {cases === null ? (
          <Loading label="Loading cases…" />
        ) : cases.length === 0 ? (
          <div className="text-sm text-slate-500">No cases raised.</div>
        ) : (
          <div className="space-y-2">
            {cases.map((c) => (
              <div key={c.id} className="rounded-xl bg-slate-50 border border-slate-200 px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-bold text-indigo-600">{c.case_number}</span>
                  <Badge tone={c.status === "Resolved" || c.status === "Closed" ? "green" : c.status === "Logged" ? "blue" : "amber"}>{c.status}</Badge>
                </div>
                <div className="mt-1.5 font-semibold text-slate-800">{c.title}</div>
                <div className="mt-0.5 text-[11px] text-slate-400 capitalize">
                  {c.category} · {c.severity.toLowerCase()} · {fmtDate(c.opened_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function StaffPortal() {
  const [loggedIn, setLoggedIn] = useState(() => Boolean(localStorage.getItem(PORTAL_TOKEN_KEY)));

  function logout() {
    localStorage.removeItem(PORTAL_TOKEN_KEY);
    setLoggedIn(false);
  }

  if (!loggedIn) return <StaffPortalLogin onLogin={() => setLoggedIn(true)} />;
  return <StaffPortalDashboard onLogout={logout} />;
}
