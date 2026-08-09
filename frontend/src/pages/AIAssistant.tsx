import { FormEvent, useState } from "react";
import { api } from "../api";
import { Card, ErrorMessage, Loading, PageHeader } from "../components/ui";
import { useApi } from "../useApi";

type Answer = {
  answer: string;
  facts: string[];
  predictions: string[];
  recommendations: string[];
  tagging: string;
};

type Recommendation = {
  recommendation: string;
  rule: string;
  triggered_by: Record<string, number>;
  type: string;
};

export default function AIAssistant() {
  const recs = useApi<Recommendation[]>("/ai/recommendations");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const a = await api<Answer>(`/ai/answer?question=${encodeURIComponent(question)}`);
      setAnswer(a);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="AI Assistant"
        subtitle="Rule-based assistant over your simulated platform data — every value retrieved from the DB or a model run, no LLM."
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Ask about operations">
          <form onSubmit={ask} className="space-y-3">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder='e.g. "predict the security queue" or "what is the current status?"'
              rows={3}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              disabled={busy}
              className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700 disabled:opacity-50"
            >
              {busy ? "Thinking…" : "Ask"}
            </button>
          </form>
          <ErrorMessage message={error} />
          {answer && (
            <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-800">{answer.answer}</p>
              {answer.predictions.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-semibold text-blue-700 uppercase">Predictions</div>
                  {answer.predictions.map((p, i) => (
                    <p key={i} className="mt-1 text-sm text-slate-700">{p}</p>
                  ))}
                </div>
              )}
              {answer.recommendations.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-semibold text-amber-700 uppercase">Recommendations</div>
                  {answer.recommendations.map((r, i) => (
                    <p key={i} className="mt-1 text-sm text-slate-700">{r}</p>
                  ))}
                </div>
              )}
              <p className="mt-3 text-xs text-slate-400">{answer.tagging}</p>
            </div>
          )}
        </Card>

        <Card title="Rule-driven recommendations">
          {recs.loading ? (
            <Loading />
          ) : recs.error ? (
            <ErrorMessage message={recs.error} />
          ) : (
            <div className="space-y-3">
              {recs.data?.map((r, i) => (
                <div key={i} className="rounded-md border border-slate-200 p-4">
                  <div className="text-sm font-semibold text-slate-800">{r.recommendation}</div>
                  <div className="mt-1 text-xs text-slate-500">Rule: {r.rule}</div>
                  {Object.keys(r.triggered_by).length > 0 && (
                    <div className="mt-2 text-xs text-slate-400">
                      Triggered by: {Object.entries(r.triggered_by).map(([k, v]) => `${k}=${v}`).join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
