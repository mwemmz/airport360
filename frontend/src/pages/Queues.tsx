import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, Stat } from "../components/ui";
import { useApi } from "../useApi";

type Queue = {
  id: number;
  queue_type: string;
  location: string;
  current_length: number;
  avg_wait_minutes: number;
  open_counters: number;
  processing_rate: number;
  recorded_at: string;
};

type Prediction = {
  predicted_length: number;
  congestion_level: string;
  horizon_minutes: number;
  model_name: string;
  model_version: string;
  metrics: Record<string, number>;
};

export default function Queues() {
  const queues = useApi<Queue[]>("/queues");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runPrediction(e: FormEvent) {
    e.preventDefault();
    setPredicting(true);
    setError(null);
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    const queueType = data.get("queueType");
    const horizon = data.get("horizon");
    try {
      const p = await api<Prediction>(
        `/predictions/queue?queue_type=${encodeURIComponent(String(queueType))}&horizon_minutes=${encodeURIComponent(String(horizon))}`
      );
      setPrediction(p);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPredicting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Queues & Predictions"
        subtitle="Observed queue samples and the prototype LinearRegression queue model."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card title="Run a queue prediction">
          <form onSubmit={runPrediction} className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-slate-500">Queue type</label>
              <select name="queueType" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                <option value="security">Security</option>
                <option value="checkin">Check-in</option>
                <option value="immigration">Immigration</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500">Horizon (minutes)</label>
              <input
                name="horizon"
                type="number"
                defaultValue={30}
                min={5}
                max={120}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              disabled={predicting}
              className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700 disabled:opacity-50"
            >
              {predicting ? "Training & predicting…" : "Predict"}
            </button>
            <p className="text-xs text-slate-400">Trains a fresh baseline model on the seeded queue history.</p>
          </form>
          <ErrorMessage message={error} />
          {prediction && (
            <div className="mt-4 rounded-xl border border-white/70 bg-white/60 backdrop-blur-xl p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-700">Prediction</span>
                <Badge tone={prediction.congestion_level === "HIGH" || prediction.congestion_level === "CRITICAL" ? "red" : prediction.congestion_level === "MEDIUM" ? "amber" : "green"}>
                  {prediction.congestion_level}
                </Badge>
              </div>
              <div className="mt-2 text-3xl font-bold text-slate-900">{prediction.predicted_length}</div>
              <div className="text-xs text-slate-500">people in {prediction.horizon_minutes} minutes</div>
              <div className="mt-2 text-xs text-slate-400">
                {prediction.model_name} · {prediction.model_version}
              </div>
            </div>
          )}
        </Card>

        <Card title="Observed queues" className="lg:col-span-2">
          {queues.loading ? (
            <Loading />
          ) : queues.error ? (
            <ErrorMessage message={queues.error} />
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <Stat label="Latest length" value={queues.data?.[0]?.current_length ?? "–"} />
                <Stat label="Latest wait (min)" value={queues.data?.[0]?.avg_wait_minutes ?? "–"} />
                <Stat label="Open counters" value={queues.data?.[0]?.open_counters ?? "–"} />
              </div>
              <ScrollTable>
                <table className="w-full min-w-[520px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Queue</th>
                      <th>Location</th>
                      <th>Length</th>
                      <th>Wait (min)</th>
                      <th>Counters</th>
                      <th>Recorded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queues.data?.map((q) => (
                      <tr key={q.id} className="border-b border-slate-100">
                        <td className="py-2 font-medium">{q.queue_type}</td>
                        <td className="text-xs text-slate-500">{q.location}</td>
                        <td>{q.current_length}</td>
                        <td>{q.avg_wait_minutes}</td>
                        <td>{q.open_counters}</td>
                        <td className="text-xs text-slate-400">{new Date(q.recorded_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
