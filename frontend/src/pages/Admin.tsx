import { FormEvent, useState } from "react";
import { Badge, Card, ErrorMessage, Loading, PageHeader } from "../components/ui";
import { api } from "../api";
import { useApi } from "../useApi";

type UserRow = { id: number; email: string; full_name: string; role: { id: number; name: string }; site_id: number; active: boolean };
type SiteRow = { id: number; code: string; name: string; city: string; country: string; active: boolean };
type AuditRow = { id: number; user_id: number; action: string; entity_type: string; entity_id: number | null; detail: string | null; created_at: string };

export default function Admin() {
  const users = useApi<UserRow[]>("/users");
  const sites = useApi<SiteRow[]>("/sites");
  const audit = useApi<AuditRow[]>("/audit");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function createUser(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/users", {
        method: "POST",
        body: JSON.stringify({
          email: String(fd.get("email")),
          full_name: String(fd.get("full_name")),
          password: String(fd.get("password")),
          role: String(fd.get("role")),
          site_id: Number(fd.get("site_id")),
        }),
      });
      setMessage("User created.");
      users.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function createSite(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/sites", {
        method: "POST",
        body: JSON.stringify({
          code: String(fd.get("code")),
          name: String(fd.get("name")),
          city: String(fd.get("city")),
          country: String(fd.get("country")),
          iata_code: String(fd.get("iata_code")) || null,
        }),
      });
      setMessage("Site created.");
      sites.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function toggleUser(u: UserRow) {
    setError(null);
    setMessage(null);
    try {
      await api(`/users/${u.id}/status?active=${!u.active}`, { method: "PATCH" });
      setMessage(`User "${u.email}" ${u.active ? "deactivated" : "reactivated"}.`);
      users.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader title="Administration" subtitle="Users, roles, sites, and audit log." />
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={`Users (${users.data?.length ?? 0})`}>
          {users.loading ? (
            <Loading />
          ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b">
                <th className="py-2">Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Site</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(users.data ?? []).map((u) => (
                <tr key={u.id} className="border-b border-slate-100">
                  <td className="py-2">{u.full_name}</td>
                  <td className="text-xs">{u.email}</td>
                  <td>{u.role.name}</td>
                  <td>{u.site_id}</td>
                  <td>
                    <button
                      onClick={() => toggleUser(u)}
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset transition-colors ${
                        u.active
                          ? "bg-emerald-50 text-emerald-700 ring-emerald-200 hover:bg-emerald-100"
                          : "bg-rose-50 text-rose-700 ring-rose-200 hover:bg-rose-100"
                      }`}
                      title="Click to toggle active status"
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${u.active ? "bg-emerald-500" : "bg-rose-500"}`} />
                      {u.active ? "Active" : "Inactive"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          )}
        </Card>

        <Card title="Create user">
          <form onSubmit={createUser} className="grid grid-cols-2 gap-3">
            <input name="full_name" placeholder="Full name" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="email" type="email" placeholder="Email" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="password" type="password" placeholder="Password (min 8)" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <select name="role" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
              <option>Administrator</option>
              <option>Executive</option>
              <option>Finance Officer</option>
              <option>HR Officer</option>
              <option>Department Head</option>
              <option>Staff</option>
            </select>
            <select name="site_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
              {(sites.data ?? []).map((s) => (
                <option key={s.id} value={s.id}>{s.code} — {s.name}</option>
              ))}
            </select>
            <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Create</button>
          </form>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <Card title={`Sites (${sites.data?.length ?? 0})`}>
          {sites.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Code</th>
                  <th>Name</th>
                  <th>City</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                {(sites.data ?? []).map((s) => (
                  <tr key={s.id} className="border-b border-slate-100">
                    <td className="py-2 font-semibold">{s.code}</td>
                    <td>{s.name}</td>
                    <td>{s.city}, {s.country}</td>
                    <td>{s.active ? <Badge tone="green">Active</Badge> : <Badge tone="red">Inactive</Badge>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Add site">
          <form onSubmit={createSite} className="grid grid-cols-2 gap-3">
            <input name="code" placeholder="Code (e.g. KU)" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="name" placeholder="Name" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="city" placeholder="City" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="country" placeholder="Country" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="iata_code" placeholder="IATA code" className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Add</button>
          </form>
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Audit log">
          {audit.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">When</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {(audit.data ?? []).slice(0, 50).map((a) => (
                  <tr key={a.id} className="border-b border-slate-100">
                    <td className="py-2 text-xs text-slate-500">{new Date(a.created_at).toLocaleString()}</td>
                    <td className="text-xs">#{a.user_id}</td>
                    <td className="font-mono text-xs">{a.action}</td>
                    <td className="text-xs">{a.entity_type}</td>
                    <td className="text-xs text-slate-500">{a.detail ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
