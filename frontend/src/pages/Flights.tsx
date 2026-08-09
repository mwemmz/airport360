import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type Flight = {
  id: number;
  flight_number: string;
  airline: string;
  origin: string;
  destination: string;
  scheduled_departure: string;
  status: string;
  gate: string | null;
  terminal: string | null;
  passengers_booked: number;
};

const STATUSES = ["Scheduled", "Boarding", "Departed", "Arrived", "Delayed", "Cancelled"];

export default function Flights() {
  const list = useApi<Flight[]>("/flights");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const rows = (list.data ?? []).filter(
    (f) =>
      !search ||
      f.flight_number.toLowerCase().includes(search.toLowerCase()) ||
      f.origin.toLowerCase().includes(search.toLowerCase()) ||
      f.destination.toLowerCase().includes(search.toLowerCase())
  );

  async function setStatus(flight: Flight, status: string) {
    setError(null);
    try {
      await api(`/flights/${flight.id}/status?status=${encodeURIComponent(status)}`, { method: "PATCH" });
      list.refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    list.refresh();
  }

  return (
    <div>
      <PageHeader title="Flights" subtitle="Live schedule with status updates — simulated data." />

      <form onSubmit={onSubmit} className="mb-4 flex flex-col sm:flex-row gap-2 max-w-md">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search flight / route…"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button className="rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Filter</button>
      </form>
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
                  <th className="py-2">Flight</th>
                  <th>Route</th>
                  <th>Departure</th>
                  <th>Gate</th>
                  <th>Booked</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((f) => (
                  <tr key={f.id} className="border-b border-slate-100">
                    <td className="py-2">
                      <div className="font-mono text-xs">{f.flight_number}</div>
                      <div className="text-xs text-slate-400">{f.airline}</div>
                    </td>
                    <td className="font-mono text-xs">
                      {f.origin} → {f.destination}
                    </td>
                    <td className="text-xs whitespace-nowrap">{new Date(f.scheduled_departure).toLocaleString()}</td>
                    <td className="text-xs">{f.gate ?? "–"}</td>
                    <td className="text-xs">{f.passengers_booked}</td>
                    <td>
                      <Badge tone={statusTone(f.status)}>{f.status}</Badge>
                    </td>
                    <td>
                      <select
                        value={f.status}
                        onChange={(e) => setStatus(f, e.target.value)}
                        className="rounded border border-slate-300 px-1 py-1 text-xs"
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
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
