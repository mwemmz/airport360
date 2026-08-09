import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { Badge, Card, ErrorMessage, Loading, PageHeader, statusTone } from "../components/ui";
import { api } from "../api";
import { useApi } from "../useApi";

type Activity = {
  id: number;
  site_id: number;
  activity_type: string;
  title: string;
  participant_category: string;
  participants_count: number;
  module_area: string;
  status: string;
  start_date: string;
  end_date: string | null;
  notes: string | null;
};

export default function CapacityBuilding() {
  const { user } = useAuth();
  const canEdit = user?.role.name === "Administrator" || user?.role.name === "HR Officer";

  const activities = useApi<Activity[]>("/capacity-building");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function addActivity(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/capacity-building", {
        method: "POST",
        body: JSON.stringify({
          activity_type: String(fd.get("activity_type")),
          title: String(fd.get("title")),
          participant_category: String(fd.get("participant_category")),
          participants_count: Number(fd.get("participants_count")) || 0,
          module_area: String(fd.get("module_area")),
          status: String(fd.get("status")),
          start_date: String(fd.get("start_date")),
          end_date: String(fd.get("end_date")) || null,
        }),
      });
      setMessage("Activity recorded.");
      activities.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Capacity Building"
        subtitle="Partnership progress tracking — who worked on which part of the platform, and training program status per site."
      />
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Activities" className="lg:col-span-2">
          {activities.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Title</th>
                  <th>Type</th>
                  <th>Module</th>
                  <th>Participants</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(activities.data ?? []).map((a) => (
                  <tr key={a.id} className="border-b border-slate-100">
                    <td className="py-2">{a.title}</td>
                    <td>{a.activity_type}</td>
                    <td>{a.module_area}</td>
                    <td>{a.participants_count}</td>
                    <td><Badge tone={statusTone(a.status)}>{a.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {canEdit && (
          <Card title="Record activity">
            <form onSubmit={addActivity} className="space-y-3">
              <input name="title" placeholder="Title" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <select name="activity_type" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option>Workshop</option>
                <option>Project Work</option>
                <option>Certification</option>
                <option>Internship</option>
              </select>
              <select name="module_area" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option>HR</option>
                <option>Procurement</option>
                <option>Finance</option>
                <option>BI</option>
                <option>Platform Core</option>
              </select>
              <select name="participant_category" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option>Student</option>
                <option>Staff</option>
              </select>
              <input name="participants_count" type="number" placeholder="Participants" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <select name="status" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option>Planned</option>
                <option>In Progress</option>
                <option>Completed</option>
              </select>
              <input name="start_date" type="date" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="end_date" type="date" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <button className="w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white">Record</button>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}
