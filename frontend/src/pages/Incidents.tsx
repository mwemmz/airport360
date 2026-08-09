import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type Incident = {
  id: number;
  incident_number: string;
  category: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  location: string | null;
  assigned_to: string | null;
  source: string;
  escalation_logged: boolean;
  reported_at: string;
  resolved_at: string | null;
};

const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function Incidents() {
  const list = useApi<Incident[]>("/incidents");
  const [error, setError] = useState<string | null>(null);

  async function createIncident(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const data = new FormData(e.target as HTMLFormElement);
    const params = new URLSearchParams();
    data.forEach((v, k) => params.append(k, String(v)));
    try {
      await api(`/incidents?${params.toString()}`, { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function escalate(id: number) {
    setError(null);
    try {
      await api(`/incidents/${id}/escalate`, { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function resolve(id: number) {
    setError(null);
    try {
      await api(`/incidents/${id}/resolve`, { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Incidents"
        subtitle="Report, escalate (CRITICAL > 2h, HIGH > 4h open) and resolve. CRITICAL incidents feed the alerts rules engine."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card title="Report an incident">
          <form onSubmit={createIncident} className="space-y-3">
            <input name="title" required placeholder="Title" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <textarea name="description" placeholder="Description" rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <select name="category" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {["security", "medical", "fire", "equipment", "passenger issue", "operational disruption", "other"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select name="severity" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <input name="location" placeholder="Location" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <button className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Report</button>
          </form>
        </Card>

        <Card title="Active incidents" className="lg:col-span-2">
          <ErrorMessage message={error} />
          {list.loading ? (
            <Loading />
          ) : list.error ? (
            <ErrorMessage message={list.error} />
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Ref</th>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Escalated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data?.map((i) => (
                    <tr key={i.id} className="border-b border-slate-100">
                      <td className="py-2 font-mono text-xs">{i.incident_number}</td>
                      <td>
                        <Badge tone={statusTone(i.severity)}>{i.severity}</Badge>
                      </td>
                      <td className="text-xs">
                        <div className="font-medium">{i.title}</div>
                        <div className="text-slate-400">{i.category}</div>
                      </td>
                      <td>
                        <Badge tone={i.status === "Resolved" ? "green" : "amber"}>{i.status}</Badge>
                      </td>
                      <td className="text-xs">{i.escalation_logged ? "Yes" : "No"}</td>
                      <td className="space-x-2">
                        {i.status !== "Resolved" && (
                          <>
                            <button onClick={() => escalate(i.id)} className="text-xs text-amber-600 hover:underline">
                              Escalate
                            </button>
                            <button onClick={() => resolve(i.id)} className="text-xs text-emerald-600 hover:underline">
                              Resolve
                            </button>
                          </>
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
