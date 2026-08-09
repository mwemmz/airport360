import { useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, Stat, statusTone } from "../components/ui";
import { useApi } from "../useApi";

type RiskLevel = { level: string; score: number; rule: string; components: Record<string, number> };
type TimelineEvent = { ts: string; kind: string; severity: string | null; title: string; detail: string };
type Overview = {
  site_id: number;
  passenger_count: number;
  current_queue_length: number;
  avg_wait_minutes: number;
  active_incidents: number;
  open_maintenance: number;
  baggage_exceptions: number;
  cargo_in_processing: number;
  flights: {
    flight_number: string;
    airline: string;
    origin: string;
    destination: string;
    scheduled_departure: string;
    status: string;
    gate: string | null;
  }[];
  risk_level: RiskLevel;
  timeline: TimelineEvent[];
};

function toneFor(level: string) {
  if (level === "CRITICAL") return "red";
  if (level === "HIGH") return "amber";
  if (level === "MEDIUM") return "blue";
  return "green";
}

export default function CommandCenter() {
  const overview = useApi<Overview>("/ops/overview");
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState(false);

  async function refreshTimeline() {
    setAction(true);
    setError(null);
    try {
      await api<Overview>("/ops/overview");
      overview.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAction(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Command Center"
        subtitle="Operational KPIs, risk level and event timeline — computed from simulated data, no hardcoded numbers."
      />

      {overview.loading ? (
        <Loading />
      ) : overview.error ? (
        <ErrorMessage message={overview.error} />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 md:gap-4 mb-6">
            <Stat label="Passengers" value={overview.data?.passenger_count ?? "–"} />
            <Stat label="Queue length" value={overview.data?.current_queue_length ?? "–"} />
            <Stat label="Avg wait (min)" value={overview.data?.avg_wait_minutes ?? "–"} />
            <Stat label="Active incidents" value={overview.data?.active_incidents ?? "–"} />
            <Stat label="Open maintenance" value={overview.data?.open_maintenance ?? "–"} />
            <Stat label="Baggage exceptions" value={overview.data?.baggage_exceptions ?? "–"} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <Card title="Risk level" className="lg:col-span-1">
              {overview.data && (
                <>
                  <div className="flex items-center gap-3">
                    <span className="text-3xl font-bold text-slate-900">{overview.data.risk_level.level}</span>
                    <Badge tone={toneFor(overview.data.risk_level.level)}>{overview.data.risk_level.score} pts</Badge>
                  </div>
                  <div className="mt-3 space-y-1">
                    {Object.entries(overview.data.risk_level.components).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-sm">
                        <span className="text-slate-500">{k.replace(/_/g, " ")}</span>
                        <span className="font-medium">{v}</span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-xs text-slate-400">{overview.data.risk_level.rule}</p>
                </>
              )}
            </Card>

            <Card title="Upcoming flights" className="lg:col-span-2">
              <ScrollTable>
                <table className="w-full min-w-[560px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Flight</th>
                      <th>Route</th>
                      <th>Departure</th>
                      <th>Gate</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(overview.data?.flights ?? []).map((f) => (
                      <tr key={f.flight_number} className="border-b border-slate-100">
                        <td className="py-2">
                          <div className="font-mono text-xs">{f.flight_number}</div>
                          <div className="text-xs text-slate-400">{f.airline}</div>
                        </td>
                        <td className="font-mono text-xs">
                          {f.origin} → {f.destination}
                        </td>
                        <td className="text-xs">{new Date(f.scheduled_departure).toLocaleString()}</td>
                        <td className="text-xs">{f.gate ?? "–"}</td>
                        <td>
                          <Badge tone={statusTone(f.status)}>{f.status}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            </Card>
          </div>

          <Card title="Event timeline (merged incidents · alerts · flights · predictions)">
            <button
              onClick={refreshTimeline}
              disabled={action}
              className="mb-3 text-xs text-brand-600 hover:underline disabled:opacity-50"
            >
              {action ? "Refreshing…" : "Refresh"}
            </button>
            <ErrorMessage message={error} />
            <ScrollTable>
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Time</th>
                    <th>Type</th>
                    <th>Event</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {(overview.data?.timeline ?? []).map((e, i) => (
                    <tr key={i} className="border-b border-slate-100">
                      <td className="py-2 text-xs whitespace-nowrap">{new Date(e.ts).toLocaleString()}</td>
                      <td>
                        <Badge tone={e.severity ? statusTone(e.severity) : "slate"}>{e.kind}</Badge>
                      </td>
                      <td className="text-xs font-medium">{e.title}</td>
                      <td className="text-xs text-slate-500">{e.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          </Card>
        </>
      )}
    </div>
  );
}
