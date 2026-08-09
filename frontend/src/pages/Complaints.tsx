import { useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type Complaint = {
  id: number;
  complaint_number: string;
  category: string;
  status: string;
  title: string;
  description: string | null;
  passenger_reference: string;
  linked_incident_id: number | null;
  submitted_at: string;
  resolved_at: string | null;
};

export default function Complaints() {
  const list = useApi<Complaint[]>("/complaints");
  const [error, setError] = useState<string | null>(null);

  async function resolve(id: number, createIncident: boolean) {
    setError(null);
    try {
      await api(`/complaints/${id}/resolve?create_incident=${createIncident}`, { method: "POST" });
      list.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Complaints"
        subtitle="Staff-facing complaint management. Resolving with 'create incident' links a passenger complaint to an operational incident."
      />

      <ErrorMessage message={error} />

      {list.loading ? (
        <Loading />
      ) : list.error ? (
        <ErrorMessage message={list.error} />
      ) : (
        <Card>
          <ScrollTable>
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Ref</th>
                  <th>Category</th>
                  <th>Title</th>
                  <th>Passenger</th>
                  <th>Status</th>
                  <th>Linked incident</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {list.data?.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{c.complaint_number}</td>
                    <td>{c.category}</td>
                    <td className="text-xs">
                      <div className="font-medium">{c.title}</div>
                      <div className="text-slate-400">{c.description}</div>
                    </td>
                    <td className="font-mono text-xs">{c.passenger_reference}</td>
                    <td>
                      <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                    </td>
                    <td className="text-xs">{c.linked_incident_id ? `#${c.linked_incident_id}` : "–"}</td>
                    <td className="space-x-2 whitespace-nowrap">
                      {c.status !== "Resolved" && (
                        <>
                          <button onClick={() => resolve(c.id, false)} className="text-xs text-emerald-600 hover:underline">
                            Resolve
                          </button>
                          <button onClick={() => resolve(c.id, true)} className="text-xs text-amber-600 hover:underline">
                            Resolve + incident
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollTable>
        </Card>
      )}
    </div>
  );
}
