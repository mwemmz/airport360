import { FormEvent, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorMessage, Loading, PageHeader, ScrollTable, Stat } from "../components/ui";
import { useApi } from "../useApi";

type Partner = { id: number; name: string; website: string; certified: boolean; security_endorsed: boolean };
type Analytics = {
  total_referrals: number;
  estimated_commission: number;
  by_partner: { partner: string; referrals: number }[];
  tag: string;
};

export default function Bookings() {
  const partners = useApi<Partner[]>("/bookings/partners");
  const analytics = useApi<Analytics>("/bookings/analytics");
  const [error, setError] = useState<string | null>(null);

  async function refer(e: FormEvent) {
    e.preventDefault();
    setError(null);
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

        <Card title="Referral analytics" className="lg:col-span-2">
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
