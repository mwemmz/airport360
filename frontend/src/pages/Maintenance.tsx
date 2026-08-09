import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type Request = {
  id: number;
  request_number: string;
  category: string;
  priority: string;
  status: string;
  location: string;
  description: string | null;
  technician: string | null;
  cost: number;
  reported_at: string;
  resolved_at: string | null;
};

type RepeatFailure = {
  repeat_key: string;
  category: string;
  location: string;
  resolutions: number;
  recommendation: string;
};

export default function Maintenance() {
  const list = useApi<Request[]>("/maintenance");
  const repeats = useApi<RepeatFailure[]>("/maintenance/repeat-failures");
  const [error, setError] = useState<string | null>(null);

  async function create(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const data = new FormData(e.target as HTMLFormElement);
    const params = new URLSearchParams();
    data.forEach((v, k) => params.append(k, String(v)));
    try {
      await api(`/maintenance?${params.toString()}`, { method: "POST" });
      list.refresh();
      repeats.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function resolve(id: number) {
    setError(null);
    try {
      await api(`/maintenance/${id}/resolve`, { method: "POST" });
      list.refresh();
      repeats.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Maintenance"
        subtitle="Requests, resolution and repeat-failure detection (same location resolved 2+ times → replacement review)."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card title="Raise a request">
          <form onSubmit={create} className="space-y-3">
            <select name="category" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {["toilet", "water", "electricity", "lighting", "escalator", "elevator", "HVAC", "seating", "signage", "other"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <input name="location" required placeholder="Location (e.g. Toilet Block A)" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <textarea name="description" placeholder="Issue description" rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <select name="priority" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {["High", "Medium", "Low"].map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <button className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Raise</button>
          </form>
        </Card>

        <Card title="Repeat failures (replacement review)" className="lg:col-span-2">
          <ErrorMessage message={error} />
          {repeats.loading ? (
            <Loading />
          ) : repeats.error ? (
            <ErrorMessage message={repeats.error} />
          ) : (repeats.data ?? []).length === 0 ? (
            <div className="text-sm text-slate-500">No repeat failures detected.</div>
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Category</th>
                    <th>Location</th>
                    <th>Resolutions</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {repeats.data?.map((r) => (
                    <tr key={r.repeat_key} className="border-b border-slate-100">
                      <td className="py-2">{r.category}</td>
                      <td className="text-xs">{r.location}</td>
                      <td>
                        <Badge tone="amber">{r.resolutions}</Badge>
                      </td>
                      <td className="text-xs text-slate-500">{r.recommendation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          )}
        </Card>
      </div>

      <Card title="All requests">
        {list.loading ? (
          <Loading />
        ) : list.error ? (
          <ErrorMessage message={list.error} />
        ) : (
          <ScrollTable>
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Ref</th>
                  <th>Category</th>
                  <th>Location</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Reported</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {list.data?.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{r.request_number}</td>
                    <td>{r.category}</td>
                    <td className="text-xs text-slate-500">{r.location}</td>
                    <td>
                      <Badge tone={statusTone(r.priority)}>{r.priority}</Badge>
                    </td>
                    <td>
                      <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                    </td>
                    <td className="text-xs text-slate-400">{new Date(r.reported_at).toLocaleString()}</td>
                    <td>
                      {r.status !== "Resolved" && (
                        <button onClick={() => resolve(r.id)} className="text-xs text-emerald-600 hover:underline">
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
  );
}
