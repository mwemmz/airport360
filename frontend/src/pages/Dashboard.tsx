import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card, ErrorMessage, Loading, PageHeader, Stat } from "../components/ui";
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

export default function Dashboard() {
  const overview = useApi<Overview>("/bi/overview");
  const trend = useApi<TrendPoint[]>("/bi/spend-trend?days=60");
  const categories = useApi<CategoryRow[]>("/bi/spend-by-category");
  const budgets = useApi<BudgetRow[]>("/bi/budget-vs-actual");
  const anomalies = useApi<Anomaly[]>("/bi/anomalies?days=60");
  const capacity = useApi<CapOverview>("/bi/capacity-building");

  return (
    <div>
      <PageHeader
        title="Business Intelligence"
        subtitle="Cross-module dashboard — all figures computed from seeded data, no hardcoded numbers."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Stat label="Active headcount" value={overview.data?.headcount ?? "–"} />
        <Stat label="Trainings completed" value={overview.data?.trainings_completed ?? "–"} />
        <Stat label="Total requisitions" value={overview.data?.total_requisitions ?? "–"} />
        <Stat
          label="Budget utilization"
          value={overview.data ? `${overview.data.budget_utilization}%` : "–"}
          hint={`Spend ${overview.data?.total_spend ?? 0} of ${overview.data?.total_budget ?? 0}`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Spend trend (60 days)">
          {trend.loading ? <Loading /> : trend.error ? <ErrorMessage message={trend.error} /> : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trend.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="amount" stroke="#2563eb" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Spend by category">
          {categories.loading ? <Loading /> : categories.error ? <ErrorMessage message={categories.error} /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={categories.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="amount" fill="#1e40af" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Budget vs actual">
          {budgets.loading ? <Loading /> : budgets.error ? <ErrorMessage message={budgets.error} /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={budgets.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="allocated" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="spent" fill="#16a34a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Capacity building status">
          {capacity.loading ? <Loading /> : capacity.error ? <ErrorMessage message={capacity.error} /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={(capacity.data?.by_status ?? []).map((r) => ({ name: r.status, count: r.count }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Procurement spend anomaly flags (rule-based)">
          {anomalies.loading ? (
            <Loading />
          ) : anomalies.error ? (
            <ErrorMessage message={anomalies.error} />
          ) : (anomalies.data ?? []).length === 0 ? (
            <div className="text-sm text-slate-500">No anomalies flagged in the current window.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Expense</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Date</th>
                  <th>Flag</th>
                </tr>
              </thead>
              <tbody>
                {(anomalies.data ?? []).map((a) => (
                  <tr key={a.expense_number} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{a.expense_number}</td>
                    <td>{a.category}</td>
                    <td>{a.amount.toFixed(2)}</td>
                    <td>{a.expense_date}</td>
                    <td>
                      <Badge tone="red">Anomaly</Badge>
                      <div className="text-xs text-slate-400 mt-1 max-w-md">{a.flag.rule}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
