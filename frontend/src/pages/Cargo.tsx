import { useState } from "react";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type Shipment = {
  id: number;
  awb_number: string;
  origin: string;
  destination: string;
  status: string;
  weight_kg: number;
  storage_location: string | null;
  delayed: boolean;
  registered_at: string;
  released_at: string | null;
};

export default function Cargo() {
  const all = useApi<Shipment[]>("/cargo");
  const delayed = useApi<Shipment[]>("/cargo?delayed_only=true");
  const [showDelayed, setShowDelayed] = useState(false);

  const rows = showDelayed ? delayed.data ?? [] : all.data ?? [];

  return (
    <div>
      <PageHeader title="Cargo" subtitle="Shipment status and delay tracking — simulated data." />

      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setShowDelayed(false)}
          className={`rounded-md px-3 py-1.5 text-sm ${!showDelayed ? "bg-brand-600 text-white" : "bg-white/70 backdrop-blur-xl border border-slate-200 text-slate-600"}`}
        >
          All
        </button>
        <button
          onClick={() => setShowDelayed(true)}
          className={`rounded-md px-3 py-1.5 text-sm ${showDelayed ? "bg-brand-600 text-white" : "bg-white/70 backdrop-blur-xl border border-slate-200 text-slate-600"}`}
        >
          Delayed only ({delayed.data?.length ?? "…"})
        </button>
      </div>

      {all.loading ? (
        <Loading />
      ) : all.error ? (
        <ErrorMessage message={all.error} />
      ) : (
        <Card>
          <ScrollTable>
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">AWB</th>
                  <th>Route</th>
                  <th>Status</th>
                  <th>Weight (kg)</th>
                  <th>Location</th>
                  <th>Registered</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{c.awb_number}</td>
                    <td className="font-mono text-xs">
                      {c.origin} → {c.destination}
                    </td>
                    <td>
                      <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                      {c.delayed && <Badge tone="red">Delayed</Badge>}
                    </td>
                    <td>{c.weight_kg}</td>
                    <td className="text-xs text-slate-500">{c.storage_location ?? "–"}</td>
                    <td className="text-xs text-slate-400">{new Date(c.registered_at).toLocaleString()}</td>
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
