import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card, EmptyState, ErrorMessage, PageHeader, Stat } from "../components/ui";
import { AlertTriangle, Banknote, FileText, GraduationCap, Layers, PiggyBank, TrendingUp, Users } from "lucide-react";
import { useApi } from "../useApi";

type Overview = {
  headcount: number;
  trainings_completed: number;
  total_requisitions: number;
  pending_approvals: number;
  total_spend: number;
  total_budget: number;
  budget_utilization: number;
};
type TrendPoint = { date: string; amount: number };
type CategoryRow = { category: string; amount: number };
type BudgetRow = { category: string; allocated: number; spent: number; utilization_pct: number };
type Anomaly = {
  expense_number: string;
  category: string;
  amount: number;
  expense_date: string;
  flag: { is_anomaly: boolean; threshold: number; rule: string };
};
type CapOverview = { by_status: { status: string; count: number }[]; by_module: { module: string; count: number }[] };

const PIE_COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#10b981", "#f43f5e"];

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { name?: string; value?: number; color?: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl bg-slate-900/95 border border-white/10 px-3 py-2 text-xs text-white shadow-xl">
      <div className="font-semibold mb-1 text-slate-300">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-bold">{p.value?.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function formatK(v: number) {
  return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`;
}

export default function Dashboard() {
  const overview = useApi<Overview>("/bi/overview");
  const trend = useApi<TrendPoint[]>("/bi/spend-trend?days=60");
  const categories = useApi<CategoryRow[]>("/bi/spend-by-category");
  const budgets = useApi<BudgetRow[]>("/bi/budget-vs-actual");
  const anomalies = useApi<Anomaly[]>("/bi/anomalies?days=60");
  const capacity = useApi<CapOverview>("/bi/capacity-building");

  const loading = overview.loading;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Business Intelligence"
        subtitle="Cross-module dashboard — all figures computed from seeded data, no hardcoded numbers."
      />

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 stagger">
        {loading ? (
          <>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="glass-card p-5">
                <div className="skeleton h-3 w-20 mb-3" />
                <div className="skeleton h-8 w-16" />
              </div>
            ))}
          </>
        ) : (
          <>
            <Stat label="Active headcount" value={overview.data?.headcount ?? "–"} icon={<Users className="w-5 h-5" />} tone="indigo" />
            <Stat label="Trainings completed" value={overview.data?.trainings_completed ?? "–"} icon={<GraduationCap className="w-5 h-5" />} tone="emerald" />
            <Stat label="Total requisitions" value={overview.data?.total_requisitions ?? "–"} icon={<FileText className="w-5 h-5" />} tone="cyan" />
            <Stat
              label="Budget utilization"
              value={overview.data ? `${overview.data.budget_utilization}%` : "–"}
              hint={overview.data ? `${formatK(overview.data.total_spend)} of ${formatK(overview.data.total_budget)}` : undefined}
              icon={<PiggyBank className="w-5 h-5" />}
              tone="amber"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Spend trend (60 days)" actions={<TrendingUp className="w-4 h-4 text-indigo-500" />}>
          {trend.loading ? <div className="h-60 skeleton" /> : trend.error ? <ErrorMessage message={trend.error} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend.data ?? []}>
                <defs>
                  <linearGradient id="trend" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} minTickGap={30} />
                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={formatK} width={44} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Spend by category" actions={<Banknote className="w-4 h-4 text-cyan-500" />}>
          {categories.loading ? <div className="h-60 skeleton" /> : categories.error ? <ErrorMessage message={categories.error} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={categories.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="category" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={formatK} width={44} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(99,102,241,0.05)" }} />
                <Bar dataKey="amount" radius={[6, 6, 0, 0]} maxBarSize={42}>
                  {categories.data?.map((_, i) => (
                    <Cell key={i} fill={["#6366f1", "#818cf8", "#06b6d4", "#22d3ee", "#f59e0b", "#34d399"][i % 6]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Budget vs actual" actions={<Layers className="w-4 h-4 text-emerald-500" />}>
          {budgets.loading ? <div className="h-60 skeleton" /> : budgets.error ? <ErrorMessage message={budgets.error} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={budgets.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="category" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={formatK} width={44} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(16,185,129,0.05)" }} />
                <Bar dataKey="allocated" name="Allocated" fill="#cbd5e1" radius={[6, 6, 0, 0]} maxBarSize={22} />
                <Bar dataKey="spent" name="Spent" fill="#10b981" radius={[6, 6, 0, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Capacity building status" actions={<Layers className="w-4 h-4 text-amber-500" />}>
          {capacity.loading ? <div className="h-60 skeleton" /> : capacity.error ? <ErrorMessage message={capacity.error} /> : (
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={capacity.data?.by_status ?? []}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius={52}
                    outerRadius={80}
                    paddingAngle={3}
                    strokeWidth={2}
                  >
                    {(capacity.data?.by_status ?? []).map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2.5 w-full sm:w-40">
                {(capacity.data?.by_status ?? []).map((r, i) => (
                  <div key={r.status} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-slate-500">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      {r.status}
                    </span>
                    <span className="font-bold text-slate-800">{r.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      <Card
        title="Procurement spend anomaly flags (rule-based)"
        actions={<Badge tone="red" dot>Rule-based</Badge>}
      >
        {anomalies.loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-10 w-full" />
            ))}
          </div>
        ) : anomalies.error ? (
          <ErrorMessage message={anomalies.error} />
        ) : (anomalies.data ?? []).length === 0 ? (
          <EmptyState title="No anomalies flagged" hint="No anomalies detected in the current window." />
        ) : (
          <div className="overflow-x-auto -mx-5 px-5 md:mx-0 md:px-0">
            <table className="w-full text-sm min-w-[560px]">
              <thead>
                <tr className="text-left text-xs text-slate-400 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-2.5 pr-2 font-semibold">Expense</th>
                  <th className="py-2.5 px-2 font-semibold">Category</th>
                  <th className="py-2.5 px-2 font-semibold">Amount</th>
                  <th className="py-2.5 px-2 font-semibold">Date</th>
                  <th className="py-2.5 pl-2 font-semibold">Flag</th>
                </tr>
              </thead>
              <tbody>
                {(anomalies.data ?? []).map((a) => (
                  <tr key={a.expense_number} className="border-b border-slate-100 hover:bg-indigo-50/40 transition-colors">
                    <td className="py-3 pr-2 font-mono text-xs text-slate-500">{a.expense_number}</td>
                    <td className="py-3 px-2">{a.category}</td>
                    <td className="py-3 px-2 font-semibold tabular-nums">${a.amount.toFixed(2)}</td>
                    <td className="py-3 px-2 text-slate-500">{a.expense_date}</td>
                    <td className="py-3 pl-2">
                      <Badge tone="red" dot>Anomaly</Badge>
                      <div className="text-[11px] text-slate-400 mt-1 max-w-md">{a.flag.rule}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {!loading && overview.data && overview.data.pending_approvals > 0 && (
        <div className="glass-card card-glow flex items-start gap-3 rounded-2xl border border-amber-200/70 bg-amber-50/50 p-4 animate-fade-in">
          <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800">
            <span className="font-bold">{overview.data.pending_approvals}</span> requisition{overview.data.pending_approvals === 1 ? "" : "s"} awaiting approval.
          </div>
        </div>
      )}
    </div>
  );
}
