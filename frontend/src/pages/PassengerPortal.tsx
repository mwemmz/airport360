import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, PageHeader, ScrollTable } from "../components/ui";

type FlightStatus = {
  flight_number: string;
  airline: string;
  origin: string;
  destination: string;
  scheduled_departure: string;
  status: string;
  gate: string | null;
  terminal: string | null;
};

type Bag = {
  bag_id: string;
  status: string;
  current_location: string | null;
  exception_type: string | null;
  history: { event: string; location: string; at: string }[];
};

export default function PassengerPortal() {
  const [reference, setReference] = useState("");
  const [flight, setFlight] = useState<FlightStatus | null>(null);
  const [bags, setBags] = useState<Bag[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function lookup(e: FormEvent) {
    e.preventDefault();
    if (!reference.trim()) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const [f, b] = await Promise.all([
        api<FlightStatus>(`/passenger/flight-status?reference=${encodeURIComponent(reference)}`),
        api<Bag[]>(`/passenger/baggage?reference=${encodeURIComponent(reference)}`),
      ]);
      setFlight(f);
      setBags(b);
    } catch (err) {
      setError((err as Error).message);
      setFlight(null);
      setBags(null);
    } finally {
      setBusy(false);
    }
  }

  async function submitComplaint(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNote(null);
    const data = new FormData(e.target as HTMLFormElement);
    const category = String(data.get("category") ?? "");
    const title = String(data.get("title") ?? "");
    const description = String(data.get("description") ?? "");
    try {
      await api(
        `/passenger/complaints?category=${encodeURIComponent(category)}&title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}&reference=${encodeURIComponent(reference)}`,
        { method: "POST" }
      );
      setNote("Complaint submitted — reference it with your passenger reference.");
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Passenger Portal"
        subtitle="Check your flight and baggage status, or submit feedback — using your passenger reference."
      />

      <Card title="Find your flight & baggage" className="mb-6">
        <form onSubmit={lookup} className="flex flex-col sm:flex-row gap-2 max-w-lg">
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value.toUpperCase())}
            placeholder="Passenger reference (e.g. PASS-KU-0001)"
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <button disabled={busy} className="rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700 disabled:opacity-50">
            {busy ? "Looking up…" : "Look up"}
          </button>
        </form>
        <ErrorMessage message={error} />

        {flight && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Flight</div>
              <div className="font-mono font-bold">{flight.flight_number}</div>
              <div className="text-xs text-slate-400">{flight.airline}</div>
            </div>
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Route</div>
              <div className="font-mono font-bold">{flight.origin} → {flight.destination}</div>
            </div>
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Gate / Terminal</div>
              <div className="font-bold">{flight.gate ?? "–"} / {flight.terminal ?? "–"}</div>
            </div>
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">Status</div>
              <Badge tone={flight.status === "Departed" || flight.status === "Arrived" ? "green" : flight.status === "Delayed" || flight.status === "Cancelled" ? "red" : "amber"}>
                {flight.status}
              </Badge>
            </div>
          </div>
        )}
      </Card>

      {bags && bags.length > 0 && (
        <Card title="Your baggage" className="mb-6">
          <div className="space-y-4">
            {bags.map((b) => (
              <div key={b.bag_id} className="rounded-md border border-slate-200 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-bold">{b.bag_id}</span>
                  <Badge tone={b.exception_type ? "red" : "green"}>{b.status}</Badge>
                  {b.exception_type && <Badge tone="red">{b.exception_type}</Badge>}
                </div>
                <div className="mt-1 text-xs text-slate-500">Now at: {b.current_location ?? "unknown"}</div>
                <ScrollTable>
                  <table className="w-full min-w-[360px] text-xs mt-2">
                    <thead>
                      <tr className="text-left text-slate-500 border-b">
                        <th className="py-1">Event</th>
                        <th>Location</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {b.history.map((h, i) => (
                        <tr key={i} className="border-b border-slate-100">
                          <td className="py-1">{h.event}</td>
                          <td>{h.location}</td>
                          <td className="text-slate-400">{new Date(h.at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollTable>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="Submit feedback">
        <form onSubmit={submitComplaint} className="space-y-3 max-w-lg">
          <select name="category" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
            {["baggage", "delay", "staff", "facilities", "cleanliness", "other"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <input name="title" required placeholder="Short title" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          <textarea name="description" placeholder="Tell us more…" rows={3} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          <button className="rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Submit feedback</button>
        </form>
        {note && <div className="mt-3 text-sm text-emerald-700">{note}</div>}
      </Card>
    </div>
  );
}
