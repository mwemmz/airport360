import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { Badge, Card, ErrorMessage, Loading, PageHeader } from "../components/ui";
import { api } from "../api";
import { useApi } from "../useApi";

type Expense = {
  id: number;
  expense_number: string;
  department_id: number;
  category: string;
  vendor: string;
  amount: number;
  expense_date: string;
  notes: string | null;
};
type BudgetRow = {
  id: number;
  category: string;
  fiscal_year: number;
  allocated: number;
  spent: number;
  utilization_pct: number;
};
type Department = { id: number; name: string };

export default function Finance() {
  const { user } = useAuth();
  const role = user?.role.name ?? "";
  const canEdit = ["Administrator", "Finance Officer"].includes(role);

  const expenses = useApi<Expense[]>("/finance/expenses");
  const budgets = useApi<BudgetRow[]>("/finance/budgets");
  const departments = useApi<Department[]>("/hr/departments");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingBudgetId, setEditingBudgetId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function addExpense(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/finance/expenses", {
        method: "POST",
        body: JSON.stringify({
          department_id: Number(fd.get("department_id")),
          category: String(fd.get("category")),
          vendor: String(fd.get("vendor")),
          amount: Number(fd.get("amount")),
          expense_date: String(fd.get("expense_date")),
        }),
      });
      setMessage("Expense recorded.");
      expenses.refresh();
      budgets.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addBudget(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    const params = new URLSearchParams({
      fiscal_year: String(fd.get("fiscal_year")),
      category: String(fd.get("category")),
      allocated: String(fd.get("allocated")),
      department_id: String(fd.get("department_id")),
    });
    try {
      await api(`/finance/budgets?${params}`, { method: "POST" });
      setMessage("Budget line added.");
      budgets.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveExpense(e: FormEvent) {
    e.preventDefault();
    if (editingId === null) return;
    setError(null);
    setMessage(null);
    setBusyId(editingId);
    const fd = new FormData(e.currentTarget as HTMLFormElement);
    try {
      await api(`/finance/expenses/${editingId}`, {
        method: "PUT",
        body: JSON.stringify({
          category: String(fd.get("category")),
          vendor: String(fd.get("vendor")),
          amount: Number(fd.get("amount")),
          expense_date: String(fd.get("expense_date")),
          notes: String(fd.get("notes") || null),
        }),
      });
      setMessage("Expense updated.");
      setEditingId(null);
      expenses.refresh();
      budgets.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function deleteExpense(id: number) {
    if (!window.confirm("Delete this expense? Budget spend will be adjusted.")) return;
    setError(null);
    setMessage(null);
    try {
      await api(`/finance/expenses/${id}`, { method: "DELETE" });
      setMessage("Expense deleted.");
      expenses.refresh();
      budgets.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveBudget(e: FormEvent) {
    e.preventDefault();
    if (editingBudgetId === null) return;
    setError(null);
    setMessage(null);
    setBusyId(editingBudgetId);
    const fd = new FormData(e.currentTarget as HTMLFormElement);
    try {
      await api(`/finance/budgets/${editingBudgetId}`, {
        method: "PUT",
        body: JSON.stringify({ allocated: Number(fd.get("allocated")) }),
      });
      setMessage("Budget updated.");
      setEditingBudgetId(null);
      budgets.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Finance"
        subtitle="Budget tracking and internal expense records. No payment processing, no PCI scope — record-keeping only."
      />
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Budget vs actual">
          {budgets.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Category</th>
                  <th>Allocated</th>
                  <th>Spent</th>
                  <th>Used</th>
                  {canEdit && <th></th>}
                </tr>
              </thead>
              <tbody>
                {(budgets.data ?? []).map((b) => (
                  <tr key={b.id} className="border-b border-slate-100">
                    <td className="py-2">{b.category}</td>
                    {editingBudgetId === b.id ? (
                      <>
                        <td className="py-2">
                          <form onSubmit={saveBudget} className="flex items-center gap-2">
                            <input name="allocated" type="number" step="0.01" defaultValue={b.allocated} required className="rounded border border-slate-300 px-2 py-1 text-sm w-28" />
                            <button disabled={busyId === b.id} className="rounded-md bg-emerald-600 px-2 py-1 text-xs text-white disabled:opacity-50">Save</button>
                            <button type="button" onClick={() => setEditingBudgetId(null)} className="rounded-md bg-slate-200 px-2 py-1 text-xs">Cancel</button>
                          </form>
                        </td>
                      </>
                    ) : (
                      <td className="py-2">{b.allocated.toLocaleString()}</td>
                    )}
                    <td>{b.spent.toLocaleString()}</td>
                    <td>
                      <Badge tone={b.utilization_pct > 85 ? "red" : b.utilization_pct > 60 ? "amber" : "green"}>
                        {b.utilization_pct}%
                      </Badge>
                    </td>
                    {canEdit && (
                      <td className="text-right">
                        {editingBudgetId !== b.id && (
                          <button onClick={() => setEditingBudgetId(b.id)} className="text-xs text-indigo-600 hover:underline">
                            Edit
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title={`Expenses (${expenses.data?.length ?? 0})`}>
          {expenses.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Number</th>
                  <th>Category</th>
                  <th>Vendor</th>
                  <th>Amount</th>
                  <th>Date</th>
                  {canEdit && <th></th>}
                </tr>
              </thead>
              <tbody>
                {(expenses.data ?? []).slice(0, 20).map((exp) => (
                  editingId === exp.id ? (
                    <tr key={exp.id} className="border-b border-slate-100 bg-slate-50">
                      <td className="py-2 font-mono text-xs" colSpan={canEdit ? 6 : 5}>
                        <form onSubmit={saveExpense} className="flex flex-wrap items-end gap-2">
                          <input name="category" defaultValue={exp.category} required placeholder="Category" className="rounded border border-slate-300 px-2 py-1 text-sm w-32" />
                          <input name="vendor" defaultValue={exp.vendor} required placeholder="Vendor" className="rounded border border-slate-300 px-2 py-1 text-sm w-36" />
                          <input name="amount" type="number" step="0.01" defaultValue={exp.amount} required placeholder="Amount" className="rounded border border-slate-300 px-2 py-1 text-sm w-28" />
                          <input name="expense_date" type="date" defaultValue={exp.expense_date} required className="rounded border border-slate-300 px-2 py-1 text-sm" />
                          <input name="notes" defaultValue={exp.notes ?? ""} placeholder="Notes" className="rounded border border-slate-300 px-2 py-1 text-sm flex-1 min-w-[120px]" />
                          <button disabled={busyId === exp.id} className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs text-white disabled:opacity-50">Save</button>
                          <button type="button" onClick={() => setEditingId(null)} className="rounded-md bg-slate-200 px-3 py-1.5 text-xs">Cancel</button>
                        </form>
                      </td>
                    </tr>
                  ) : (
                    <tr key={exp.id} className="border-b border-slate-100">
                      <td className="py-2 font-mono text-xs">{exp.expense_number}</td>
                      <td>{exp.category}</td>
                      <td>{exp.vendor}</td>
                      <td>{exp.amount.toLocaleString()}</td>
                      <td>{exp.expense_date}</td>
                      {canEdit && (
                        <td className="py-2 text-right whitespace-nowrap">
                          <button onClick={() => setEditingId(exp.id)} className="text-xs text-indigo-600 hover:underline mr-2">Edit</button>
                          <button onClick={() => deleteExpense(exp.id)} className="text-xs text-rose-600 hover:underline">Delete</button>
                        </td>
                      )}
                    </tr>
                  )
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {canEdit && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <Card title="Record expense">
            <form onSubmit={addExpense} className="grid grid-cols-2 gap-3">
              <input name="category" placeholder="Category" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="vendor" placeholder="Vendor" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="amount" type="number" step="0.01" placeholder="Amount" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="expense_date" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <select name="department_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                {(departments.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Record</button>
            </form>
          </Card>

          <Card title="Add budget line">
            <form onSubmit={addBudget} className="grid grid-cols-2 gap-3">
              <input name="category" placeholder="Category" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="fiscal_year" type="number" placeholder="Fiscal year" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="allocated" type="number" step="0.01" placeholder="Allocated" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <select name="department_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                {(departments.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Add</button>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
