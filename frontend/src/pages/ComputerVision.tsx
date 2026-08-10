import { FormEvent, useRef, useState } from "react";
import { apiUpload } from "../api";
import { Badge, Card, ErrorMessage, PageHeader, Stat } from "../components/ui";
import { Eye, Film, ScanLine, ShieldCheck, Video, Users, Waves } from "lucide-react";

type CvResult = {
  filename: string;
  frames_processed: number;
  avg_people: number;
  max_people: number;
  estimated_queue_length: number;
  occupancy_pct: number;
  density_level: string;
  retention: string;
  temp_input_deleted: boolean;
  tag: string;
  privacy: string;
};

export default function ComputerVision() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CvResult | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function analyze(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await apiUpload<CvResult>("/computer-vision/analyze", file);
      setResult(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const densityTone =
    result?.density_level === "HIGH" || result?.density_level === "CRITICAL"
      ? "red"
      : result?.density_level === "MEDIUM"
        ? "amber"
        : "green";

  return (
    <div>
      <PageHeader
        title="Computer Vision"
        subtitle="Privacy-preserving crowd and queue analysis. Upload a CCTV-style clip — frames are processed in memory and never stored, no facial recognition."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Analyze a video clip">
          <form onSubmit={analyze} className="space-y-4">
            <div
              onClick={() => inputRef.current?.click()}
              className="cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 bg-white/50 hover:border-indigo-400 hover:bg-indigo-50/40 transition-colors px-6 py-10 text-center"
            >
              <input
                ref={inputRef}
                type="file"
                accept="video/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <Film className="w-8 h-8 text-indigo-400 mx-auto mb-3" />
              {file ? (
                <div>
                  <div className="text-sm font-semibold text-slate-700">{file.name}</div>
                  <div className="text-xs text-slate-400 mt-1">{(file.size / (1024 * 1024)).toFixed(1)} MB — click to change</div>
                </div>
              ) : (
                <>
                  <div className="text-sm font-semibold text-slate-600">Click to upload a video</div>
                  <div className="text-xs text-slate-400 mt-1">MP4 / WebM / MOV · max 30 MB</div>
                </>
              )}
            </div>
            <button
              disabled={!file || busy}
              className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {busy ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  Analyzing…
                </>
              ) : (
                <>
                  <ScanLine className="w-4 h-4" /> Analyze clip
                </>
              )}
            </button>
            <p className="text-xs text-slate-400 leading-relaxed">
              HOG person detector — aggregate metrics only. Video is written to a temp dir and deleted immediately after
              processing.
            </p>
          </form>
          <ErrorMessage message={error} />
        </Card>

        <div className="lg:col-span-2">
          {!result ? (
            <Card title="Analysis results">
              <div className="flex flex-col items-center justify-center py-14 text-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-4">
                  <Video className="w-7 h-7 text-white" />
                </div>
                <div className="text-sm font-semibold text-slate-600">No analysis yet</div>
                <div className="text-xs text-slate-400 mt-1 max-w-xs">
                  Upload a clip to get crowd density, queue length and occupancy estimates.
                </div>
              </div>
            </Card>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Stat label="Density" value={result.density_level} tone="indigo" icon={<Waves className="w-4 h-4" />} hint="HIGH ≥12 · MEDIUM ≥6" />
                <Stat label="Avg people" value={result.avg_people} tone="cyan" icon={<Users className="w-4 h-4" />} hint="per frame" />
                <Stat label="Peak people" value={result.max_people} tone="emerald" icon={<Eye className="w-4 h-4" />} hint="max in one frame" />
                <Stat label="Est. queue" value={result.estimated_queue_length} tone="amber" icon={<ScanLine className="w-4 h-4" />} hint="people minus last 2" />
              </div>

              <Card title="Clip summary">
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Source file</dt>
                    <dd className="font-medium text-slate-700 text-right">{result.filename}</dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Frames processed</dt>
                    <dd className="font-medium text-slate-700">{result.frames_processed}</dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Occupancy</dt>
                    <dd className="font-medium text-slate-700">{result.occupancy_pct}%</dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Density level</dt>
                    <dd>
                      <Badge tone={densityTone} dot>{result.density_level}</Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Retention</dt>
                    <dd className="font-medium text-slate-700">{result.retention}</dd>
                  </div>
                  <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Temp input deleted</dt>
                    <dd>
                      <Badge tone={result.temp_input_deleted ? "green" : "red"}>{result.temp_input_deleted ? "Yes" : "No"}</Badge>
                    </dd>
                  </div>
                </dl>
              </Card>

              <div className="flex items-start gap-2 rounded-xl border border-blue-100/80 bg-blue-50/60 p-3 text-xs text-slate-600">
                <ShieldCheck className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                <span>
                  <span className="font-semibold text-blue-700">{result.tag}</span> · {result.privacy}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
