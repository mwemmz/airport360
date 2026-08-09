import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type Alert = {
  id: number;
  title: string;
  detail: string | null;
  severity: string;
  alert_type: string;
  trigger_key: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
};

export default function Alerts() {
  const list = useApi<Alert[]>("/alerts");
  const [error, setError] = useState<string | null>(null);

  async function create(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const data = new FormData(e.target as HTMLFormElement);
    const params = new URLSearchParams();
    data.forEach((v, k) => params.append(k, String(v)));
    try {
      await api(`/alerts?${params.toString()}`, { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function runAuto() {
    setError(null);
    try {
      await api("/alerts/auto", { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function resolve(id: number) {
    setError(null);
    try {
      await api(`/alerts/${id}/resolve`, { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Alerts"
        subtitle="Rules engine (CRITICAL incidents → alerts) with deduplication by trigger key."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card title="Create an alert">
          <form onSubmit={create} className="space-y-3">
            <input name="title" required placeholder="Title" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <textarea name="detail" placeholder="Detail" rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <select name="alert_type" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {["congestion", "incident", "maintenance", "baggage", "cargo", "general"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <select name="severity" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <button className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Create</button>
          </form>
          <button
            onClick={runAuto}
            className="mt-3 w-full rounded-md border border-brand-600 text-brand-600 px-4 py-2 text-sm hover:bg-brand-50"
          >
            Run auto rules (CRITICAL incidents)
          </button>
        </Card>

        <Card title="Active alerts" className="lg:col-span-2">
          <ErrorMessage message={error} />
          {list.loading ? (
            <Loading />
          ) : list.error ? (
            <ErrorMessage message={list.error} />
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Severity</th>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data?.map((a) => (
                    <tr key={a.id} className="border-b border-slate-100">
                      <td>
                        <Badge tone={statusTone(a.severity)}>{a.severity}</Badge>
                      </td>
                      <td className="text-xs">
                        <div className="font-medium">{a.title}</div>
                        <div className="text-slate-400">{a.detail}</div>
                      </td>
                      <td className="text-xs">{a.alert_type}</td>
                      <td>
                        <Badge tone={a.status === "Active" ? "amber" : "green"}>{a.status}</Badge>
                      </td>
                      <td>
                        {a.status === "Active" && (
                          <button onClick={() => resolve(a.id)} className="text-xs text-emerald-600 hover:underline">
                            Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          )}
        </Card>
      </div>
    </div>
  );
}
