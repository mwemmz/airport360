import { FormEvent, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, Stat } from "../components/ui";
import { useApi } from "../useApi";

type Partner = { id: number; name: string; website: string; certified: boolean; security_endorsed: boolean; commission_rate: number };
type Analytics = {
  total_referrals: number;
  estimated_commission: number;
  by_partner: { partner: string; referrals: number }[];
  tag: string;
};

export default function Bookings() {
  const { user } = useAuth();
  const canManage = user?.role.name === "Administrator" || user?.role.name === "Executive";

  const partners = useApi<Partner[]>("/travel-agencies");
  const analytics = useApi<Analytics>("/bookings/analytics");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function addPartner(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const data = new FormData(e.target as HTMLFormElement);
    const params = new URLSearchParams();
    data.forEach((v, k) => params.append(k, String(v)));
    try {
      await api(`/travel-agencies?${params.toString()}`, { method: "POST" });
      setMessage("Agency added.");
      (e.target as HTMLFormElement).reset();
      partners.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function refer(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const data = new FormData(e.target as HTMLFormElement);
    const params = new URLSearchParams();
    data.forEach((v, k) => params.append(k, String(v)));
    try {
      await api(`/bookings/referrals?${params.toString()}`, { method: "POST" });
      analytics.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Booking Marketplace"
        subtitle="Referral logging to certified travel agencies — no PNR or payment data stored, booking happens on the airline's own checkout."
      />

      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card title="Log a referral">
          <form onSubmit={refer} className="space-y-3">
            <select name="partner_id" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="">Select agency…</option>
              {(partners.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.certified ? "(certified)" : ""}
                </option>
              ))}
            </select>
            <input name="airline" required placeholder="Airline" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <input name="origin" required placeholder="Origin (IATA)" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <input name="destination" required placeholder="Destination (IATA)" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <input name="passenger_reference" required placeholder="Passenger reference" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <input name="redirect_url" required placeholder="https://agency.example.com/book" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <button className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Log referral</button>
          </form>
          <ErrorMessage message={error} />
        </Card>

        {canManage && (
          <Card title="Add agency partner">
            <form onSubmit={addPartner} className="space-y-3">
              <input name="name" required placeholder="Agency name" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              <input name="website" required placeholder="https://agency.example.com" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              <input name="commission_rate" type="number" step="0.01" min="0" placeholder="Commission rate (%)" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              <div className="flex items-center gap-4">
                <label className="text-xs font-semibold text-slate-500 flex items-center gap-1.5">
                  <input name="certified" type="checkbox" className="rounded" /> Certified
                </label>
                <label className="text-xs font-semibold text-slate-500 flex items-center gap-1.5">
                  <input name="security_endorsed" type="checkbox" className="rounded" /> Security endorsed
                </label>
              </div>
              <button className="w-full rounded-md bg-brand-600 text-white px-4 py-2 text-sm hover:bg-brand-700">Add agency</button>
            </form>
          </Card>
        )}

        <Card title="Referral analytics" className={canManage ? "" : "lg:col-span-2"}>
          {analytics.loading ? (
            <Loading />
          ) : analytics.error ? (
            <ErrorMessage message={analytics.error} />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <Stat label="Total referrals" value={analytics.data?.total_referrals ?? "–"} />
                <Stat label="Est. commission" value={analytics.data?.estimated_commission ?? "–"} />
              </div>
              <ScrollTable>
                <table className="w-full min-w-[360px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Agency</th>
                      <th>Referrals</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(analytics.data?.by_partner ?? []).map((p) => (
                      <tr key={p.partner} className="border-b border-slate-100">
                        <td className="py-2">{p.partner}</td>
                        <td>{p.referrals}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
              <p className="mt-3 text-xs text-slate-400">{analytics.data?.tag}</p>
            </>
          )}
        </Card>
      </div>
      <Card title="Certified agency partners">
        {partners.loading ? (
          <Loading />
        ) : partners.error ? (
          <ErrorMessage message={partners.error} />
        ) : (
          <ScrollTable>
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Agency</th>
                  <th>Website</th>
                  <th>Commission</th>
                  <th>Certified</th>
                  <th>Security endorsed</th>
                </tr>
              </thead>
              <tbody>
                {partners.data?.map((p) => (
                  <tr key={p.id} className="border-b border-slate-100">
                    <td className="py-2 font-medium">{p.name}</td>
                    <td className="text-xs">
                      <a href={p.website} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline">
                        {p.website}
                      </a>
                    </td>
                    <td className="text-xs tabular-nums">{(p.commission_rate ?? 0).toFixed(1)}%</td>
                    <td>
                      <Badge tone={p.certified ? "green" : "slate"}>{p.certified ? "Yes" : "No"}</Badge>
                    </td>
                    <td>
                      <Badge tone={p.security_endorsed ? "green" : "slate"}>{p.security_endorsed ? "Yes" : "No"}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollTable>
        )}
      </Card>
    </div>
  );
}
