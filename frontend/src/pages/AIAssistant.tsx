import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Card, ErrorMessage, PageHeader } from "../components/ui";
import { useApi } from "../useApi";
import {
  ArrowUp,
  Bot,
  CheckCircle2,
  Info,
  Lightbulb,
  Sparkles,
  TrendingUp,
  User,
  Wand2,
} from "lucide-react";

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

type ChatMessage = { role: "user" | "assistant"; answer?: Answer; question: string };

const SUGGESTIONS = [
  "Predict the security queue",
  "What is the current operational status?",
  "How is our budget utilization?",
  "Show procurement anomalies",
];

function TypeWriter({ text, speed = 8 }: { text: string; speed?: number }) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    setShown("");
    if (!text) return;
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return <span>{shown}</span>;
}

function AssistantAvatar() {
  return (
    <div className="shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
      <Bot className="w-5 h-5 text-white" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center shadow-lg shadow-slate-500/20">
      <User className="w-5 h-5 text-white" />
    </div>
  );
}

function AnswerCard({ answer }: { answer: Answer }) {
  return (
    <div className="space-y-3 animate-fade-in-up">
      <div className="text-sm leading-relaxed text-slate-800">
        <TypeWriter text={answer.answer} />
      </div>

      {answer.facts.length > 0 && (
        <div className="rounded-xl border border-blue-100/80 bg-blue-50/60 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-blue-700 mb-1.5">
            <Info className="w-3.5 h-3.5" /> Facts
          </div>
          {answer.facts.map((f, i) => (
            <div key={i} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-blue-400">•</span> {f}
            </div>
          ))}
        </div>
      )}

      {answer.predictions.length > 0 && (
        <div className="rounded-xl border border-cyan-100/80 bg-cyan-50/60 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-cyan-700 mb-1.5">
            <TrendingUp className="w-3.5 h-3.5" /> Predictions
          </div>
          {answer.predictions.map((p, i) => (
            <div key={i} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-cyan-400">→</span> {p}
            </div>
          ))}
        </div>
      )}

      {answer.recommendations.length > 0 && (
        <div className="rounded-xl border border-amber-100/80 bg-amber-50/60 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-amber-700 mb-1.5">
            <Lightbulb className="w-3.5 h-3.5" /> Recommendations
          </div>
          {answer.recommendations.map((r, i) => (
            <div key={i} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-amber-400">•</span> {r}
            </div>
          ))}
        </div>
      )}

      {answer.tagging && (
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <Wand2 className="w-3 h-3" /> {answer.tagging}
        </div>
      )}
    </div>
  );
}

export default function AIAssistant() {
  const recs = useApi<Recommendation[]>("/ai/recommendations");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    setQuestion("");
    try {
      const a = await api<Answer>(`/ai/answer?question=${encodeURIComponent(q)}`);
      setMessages((m) => [...m, { role: "assistant", answer: a, question: q }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    setMessages((m) => [...m, { role: "user", question }]);
    void ask(question);
  }

  function quick(q: string) {
    setMessages((m) => [...m, { role: "user", question: q }]);
    void ask(q);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Assistant"
        subtitle="Ask about operations and get instant answers backed by live platform data."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat panel */}
        <Card className="lg:col-span-2 p-0 overflow-hidden flex flex-col h-[640px]">
          {/* Chat header */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-200/60 bg-gradient-to-r from-indigo-50/80 to-blue-50/60">
            <AssistantAvatar />
            <div className="flex-1">
              <div className="text-sm font-bold text-slate-800 flex items-center gap-2">
                Airport360 Copilot
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" /> Online
                </span>
              </div>
              <div className="text-[11px] text-slate-500">Rule-based engine · answers computed from your data</div>
            </div>
            <Sparkles className="w-5 h-5 text-indigo-400 animate-floaty" />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-gradient-to-b from-slate-50/50 to-transparent">
            {messages.length === 0 && !busy && (
              <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-glow mb-4 animate-floaty">
                  <Sparkles className="w-8 h-8 text-white" />
                </div>
                <div className="text-lg font-extrabold text-slate-800">Ask me anything</div>
                <div className="text-sm text-slate-500 mt-1 max-w-sm">
                  Predictions, queue status, budget, anomalies and more — all from your simulated data.
                </div>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => quick(s)}
                      className="glass-card card-glow px-3.5 py-2 text-xs font-semibold text-slate-600 rounded-xl"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end animate-fade-in-up">
                  <div className="flex items-end gap-2 max-w-[80%]">
                    <div className="rounded-2xl rounded-br-md bg-gradient-to-r from-indigo-600 to-blue-600 text-white px-4 py-2.5 text-sm shadow-lg shadow-indigo-500/25">
                      {m.question}
                    </div>
                    <UserAvatar />
                  </div>
                </div>
              ) : (
                <div key={i} className="flex justify-start animate-fade-in-up">
                  <div className="flex items-start gap-2 max-w-[85%]">
                    <AssistantAvatar />
                    <div className="rounded-2xl rounded-bl-md border border-white/70 bg-white/70 backdrop-blur-xl px-4 py-3 shadow-sm">
                      {m.answer && <AnswerCard answer={m.answer} />}
                    </div>
                  </div>
                </div>
              )
            )}

            {busy && (
              <div className="flex justify-start animate-fade-in-up">
                <div className="flex items-start gap-2">
                  <AssistantAvatar />
                  <div className="rounded-2xl rounded-bl-md border border-white/70 bg-white/70 backdrop-blur-xl px-4 py-3.5 shadow-sm">
                    <div className="flex items-center gap-1.5">
                      <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                      <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                      <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <ErrorMessage message={error} />

          {/* Composer */}
          <form onSubmit={submit} className="p-4 border-t border-slate-200/60 bg-white/40 backdrop-blur-xl">
            <div className="flex items-end gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about operations, budgets, queues…"
                className="input flex-1"
              />
              <button
                type="submit"
                disabled={busy || !question.trim()}
                aria-label="Send"
                className="btn-primary !p-3.5 rounded-xl shrink-0 disabled:opacity-50"
              >
                <ArrowUp className="w-5 h-5" />
              </button>
            </div>
          </form>
        </Card>

        {/* Side panel */}
        <div className="space-y-6">
          <Card
            title="Recommendations"
            actions={<CheckCircle2 className="w-4 h-4 text-emerald-500" />}
          >
            {recs.loading ? (
              <div className="space-y-3">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="skeleton h-16 w-full" />
                ))}
              </div>
            ) : recs.error ? (
              <ErrorMessage message={recs.error} />
            ) : recs.data?.length === 0 ? (
              <div className="text-sm text-slate-500">No recommendations right now.</div>
            ) : (
              <div className="space-y-3">
                {recs.data?.map((r, i) => (
                  <div key={i} className="rounded-xl border border-white/70 bg-white/60 backdrop-blur-xl p-3.5 card-glow">
                    <div className="flex items-start gap-2.5">
                      <div className="shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                        <Lightbulb className="w-4 h-4 text-white" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-slate-800 leading-snug">{r.recommendation}</div>
                        <div className="mt-1 text-[11px] text-slate-500">Rule: {r.rule}</div>
                        {Object.keys(r.triggered_by).length > 0 && (
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            {Object.entries(r.triggered_by).map(([k, v]) => (
                              <span key={k} className="rounded-full bg-slate-100 text-slate-600 px-2 py-0.5 text-[10px] font-semibold">
                                {k}={v}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Capabilities">
            <div className="space-y-3">
              {[
                { icon: TrendingUp, text: "Queue & wait-time predictions", tone: "text-cyan-600 bg-cyan-50" },
                { icon: Lightbulb, text: "Rule-driven recommendations", tone: "text-amber-600 bg-amber-50" },
                { icon: Info, text: "Live answers from platform data", tone: "text-blue-600 bg-blue-50" },
                { icon: Wand2, text: "Anomaly detection & tagging", tone: "text-indigo-600 bg-indigo-50" },
              ].map((c, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg ${c.tone} flex items-center justify-center shrink-0`}>
                    <c.icon className="w-4 h-4" />
                  </div>
                  <div className="text-xs font-medium text-slate-600">{c.text}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
