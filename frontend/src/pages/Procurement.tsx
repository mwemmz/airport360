import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { Badge, Card, ErrorMessage, Loading, PageHeader, statusTone } from "../components/ui";
import { api } from "../api";
import { useApi } from "../useApi";

type Requisition = {
  id: number;
  requisition_number: string;
  site_id: number;
  department_id: number;
  requested_by_employee_id: number;
  title: string;
  category: string;
  estimated_amount: number;
  status: string;
  approved_by: string | null;
  created_at: string;
};
type Vendor = { id: number; site_id: number; name: string; category: string };
type Employee = { id: number; first_name: string; last_name: string };
type Department = { id: number; name: string };
type PurchaseOrder = { id: number; po_number: string; requisition_id: number; vendor_id: number; total_amount: number; status: string };

export default function Procurement() {
  const { user } = useAuth();
  const role = user?.role.name ?? "";
  const canRequest = ["Administrator", "HR Officer", "Staff"].includes(role);
  const canApprove = ["Administrator", "Department Head"].includes(role);
  const canFinance = ["Administrator", "Finance Officer"].includes(role);

  const reqs = useApi<Requisition[]>("/procurement/requisitions");
  const vendors = useApi<Vendor[]>("/procurement/vendors");
  const employees = useApi<Employee[]>("/hr/employees");
  const departments = useApi<Department[]>("/hr/departments");
  const pos = useApi<PurchaseOrder[]>("/procurement/purchase-orders?list=1");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function submitRequisition(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/procurement/requisitions", {
        method: "POST",
        body: JSON.stringify({
          department_id: Number(fd.get("department_id")),
          requested_by_employee_id: Number(fd.get("requested_by_employee_id")),
          title: String(fd.get("title")),
          category: String(fd.get("category")),
          estimated_amount: Number(fd.get("estimated_amount")),
          description: String(fd.get("description")) || null,
        }),
      });
      setMessage("Requisition submitted for approval.");
      reqs.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function approve(id: number) {
    setError(null);
    try {
      await api(`/procurement/requisitions/${id}/approve`, { method: "POST" });
      setMessage("Requisition approved.");
      reqs.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function reject(id: number) {
    setError(null);
    try {
      await api(`/procurement/requisitions/${id}/reject`, { method: "POST" });
      setMessage("Requisition rejected.");
      reqs.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function raisePO(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/procurement/purchase-orders", {
        method: "POST",
        body: JSON.stringify({
          requisition_id: Number(fd.get("requisition_id")),
          vendor_id: Number(fd.get("vendor_id")),
          total_amount: Number(fd.get("total_amount")),
        }),
      });
      setMessage("Purchase order issued.");
      reqs.refresh();
      pos.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function receive(id: number) {
    setError(null);
    try {
      await api(`/procurement/purchase-orders/${id}/receive`, { method: "POST" });
      setMessage("Purchase order marked received.");
      pos.refresh();
      reqs.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const pending = (reqs.data ?? []).filter((r) => r.status === "Submitted");

  return (
    <div>
      <PageHeader title="Procurement" subtitle="Requisition → approval → purchase order → receipt. Site-aware approval routing." />
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Requisitions" className="lg:col-span-2">
          {reqs.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Number</th>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(reqs.data ?? []).map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{r.requisition_number}</td>
                    <td>{r.title}</td>
                    <td>{r.category}</td>
                    <td>{r.estimated_amount.toLocaleString()}</td>
                    <td><Badge tone={statusTone(r.status)}>{r.status}</Badge></td>
                    <td>
                      {canApprove && r.status === "Submitted" && (
                        <div className="flex gap-2">
                          <button onClick={() => approve(r.id)} className="rounded bg-emerald-600 px-2 py-1 text-xs text-white">Approve</button>
                          <button onClick={() => reject(r.id)} className="rounded bg-red-600 px-2 py-1 text-xs text-white">Reject</button>
                        </div>
                      )}
                      {canFinance && r.status === "Approved" && (
                        <form onSubmit={raisePO} className="flex gap-1">
                          <input type="hidden" name="requisition_id" value={r.id} />
                          <select name="vendor_id" required className="rounded border border-slate-300 px-1 py-1 text-xs">
                            {(vendors.data ?? []).map((v) => (
                              <option key={v.id} value={v.id}>{v.name}</option>
                            ))}
                          </select>
                          <input name="total_amount" type="number" placeholder="Amt" required className="rounded border border-slate-300 px-1 py-1 text-xs w-20" />
                          <button className="rounded bg-brand-600 px-2 py-1 text-xs text-white">Issue PO</button>
                        </form>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <div className="space-y-6">
          {canRequest && (
            <Card title="New requisition">
              <form onSubmit={submitRequisition} className="space-y-3">
                <input name="title" placeholder="Title" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
                <input name="category" placeholder="Category (e.g. IT Equipment)" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
                <input name="estimated_amount" type="number" step="0.01" placeholder="Estimated amount" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
                <select name="department_id" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                  {(departments.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
                <select name="requested_by_employee_id" required className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                  {(employees.data ?? []).map((emp) => (
                    <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>
                  ))}
                </select>
                <textarea name="description" placeholder="Description" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" rows={2} />
                <button className="w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white">Submit</button>
              </form>
            </Card>
          )}

          {canApprove && (
            <Card title={`Awaiting approval (${pending.length})`}>
              <ul className="text-sm space-y-2">
                {pending.map((r) => (
                  <li key={r.id} className="text-xs text-slate-600">
                    {r.requisition_number} · {r.title} · {r.estimated_amount.toLocaleString()}
                  </li>
                ))}
                {pending.length === 0 && <li className="text-xs text-slate-400">None.</li>}
              </ul>
            </Card>
          )}
        </div>
      </div>

      {canFinance && (
        <div className="mt-6">
          <Card title="Purchase orders">
            {pos.loading ? (
              <Loading />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">PO</th>
                    <th>Vendor</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(pos.data ?? []).map((po) => (
                    <tr key={po.id} className="border-b border-slate-100">
                      <td className="py-2 font-mono text-xs">{po.po_number}</td>
                      <td>{vendors.data?.find((v) => v.id === po.vendor_id)?.name ?? po.vendor_id}</td>
                      <td>{po.total_amount.toLocaleString()}</td>
                      <td><Badge tone={statusTone(po.status)}>{po.status}</Badge></td>
                      <td>
                        {po.status === "Issued" && (
                          <button onClick={() => receive(po.id)} className="rounded bg-emerald-600 px-2 py-1 text-xs text-white">Receive</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
