import { useState } from "react";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable } from "../components/ui";
import { useApi } from "../useApi";

type Bag = {
  id: number;
  bag_id: string;
  passenger_reference: string;
  flight_number: string | null;
  origin: string;
  destination: string;
  status: string;
  current_location: string | null;
  exception_type: string | null;
  risk_score: number;
  risk_label: string;
  risk_reasons: string[];
};

function riskTone(score: number) {
  if (score >= 0.6) return "red";
  if (score >= 0.4) return "amber";
  return "green";
}

export default function Baggage() {
  const all = useApi<Bag[]>("/baggage");
  const highRisk = useApi<Bag[]>("/baggage/high-risk");
  const [showHighRiskOnly, setShowHighRiskOnly] = useState(false);

  const rows = showHighRiskOnly ? highRisk.data ?? [] : all.data ?? [];

  return (
    <div>
      <PageHeader
        title="Baggage Tracking & Risk"
        subtitle="Prototype risk model (age, transfer time, scans, workload) — not validated against real mishandling data."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          onClick={() => setShowHighRiskOnly(false)}
          className={`rounded-md px-3 py-1.5 text-sm ${!showHighRiskOnly ? "bg-brand-600 text-white" : "bg-white/70 backdrop-blur-xl border border-slate-200 text-slate-600"}`}
        >
          All bags
        </button>
        <button
          onClick={() => setShowHighRiskOnly(true)}
          className={`rounded-md px-3 py-1.5 text-sm ${showHighRiskOnly ? "bg-brand-600 text-white" : "bg-white/70 backdrop-blur-xl border border-slate-200 text-slate-600"}`}
        >
          High risk ({highRisk.data?.length ?? "…"})
        </button>
      </div>

      {all.loading ? (
        <Loading />
      ) : all.error ? (
        <ErrorMessage message={all.error} />
      ) : (
        <Card>
          <ScrollTable>
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Bag</th>
                  <th>Passenger</th>
                  <th>Flight</th>
                  <th>Route</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((b) => (
                  <tr key={b.id} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{b.bag_id}</td>
                    <td className="font-mono text-xs">{b.passenger_reference}</td>
                    <td className="text-xs">{b.flight_number ?? "–"}</td>
                    <td className="font-mono text-xs">
                      {b.origin} → {b.destination}
                    </td>
                    <td>
                      <Badge tone={b.exception_type ? "red" : "green"}>{b.status}</Badge>
                      {b.exception_type && <div className="text-xs text-red-600 mt-1">{b.exception_type}</div>}
                    </td>
                    <td className="text-xs text-slate-500">{b.current_location ?? "–"}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <Badge tone={riskTone(b.risk_score)}>{(b.risk_score * 100).toFixed(0)}%</Badge>
                        <div className="text-xs text-slate-400 max-w-[160px]">{b.risk_reasons.join("; ")}</div>
                      </div>
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
