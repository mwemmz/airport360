import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { Badge, Card, ErrorMessage, Loading, PageHeader, statusTone } from "../components/ui";
import { api } from "../api";
import { useApi } from "../useApi";

type Employee = {
  id: number;
  employee_number: string;
  first_name: string;
  last_name: string;
  email: string;
  site_id: number;
  department_id: number;
  job_title: string;
  employment_status: string;
};
type Department = { id: number; site_id: number; name: string; code: string };
type Training = {
  id: number;
  employee_id: number;
  course_name: string;
  provider: string;
  status: string;
  completed_date: string | null;
  certificate: boolean;
};

export default function HR() {
  const { user } = useAuth();
  const canEdit = user?.role.name === "Administrator" || user?.role.name === "HR Officer";

  const employees = useApi<Employee[]>("/hr/employees");
  const departments = useApi<Department[]>("/hr/departments");
  const training = useApi<Training[]>("/hr/training");

  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function addEmployee(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      const deptId = String(fd.get("department_id"));
      const params = new URLSearchParams({
        employee_number: String(fd.get("employee_number")),
        first_name: String(fd.get("first_name")),
        last_name: String(fd.get("last_name")),
        email: String(fd.get("email")),
        department_id: deptId,
        job_title: String(fd.get("job_title")),
        hire_date: String(fd.get("hire_date")),
      });
      await api(`/hr/employees?${params}`, { method: "POST" });
      setMessage("Employee created.");
      setShowForm(false);
      employees.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addTraining(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/hr/training", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(fd.get("employee_id")),
          course_name: String(fd.get("course_name")),
          provider: String(fd.get("provider")),
          status: String(fd.get("status")),
          completed_date: String(fd.get("completed_date")) || null,
          certificate: fd.get("certificate") === "on",
        }),
      });
      setMessage("Training record added.");
      training.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <PageHeader title="Human Resources" subtitle="Employee records, departments, and training/capacity records." />
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title={`Employees (${employees.data?.length ?? 0})`} className="lg:col-span-2">
          {employees.loading ? (
            <Loading />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b">
                  <th className="py-2">Number</th>
                  <th>Name</th>
                  <th>Title</th>
                  <th>Department</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(employees.data ?? []).map((emp) => (
                  <tr key={emp.id} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{emp.employee_number}</td>
                    <td>{emp.first_name} {emp.last_name}</td>
                    <td>{emp.job_title}</td>
                    <td>{departments.data?.find((d) => d.id === emp.department_id)?.name ?? emp.department_id}</td>
                    <td><Badge tone={statusTone(emp.employment_status)}>{emp.employment_status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {canEdit && (
            <div className="mt-4">
              {!showForm ? (
                <button onClick={() => setShowForm(true)} className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700">Add employee</button>
              ) : (
                <form onSubmit={addEmployee} className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-4">
                  <input name="employee_number" placeholder="Employee number" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="first_name" placeholder="First name" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="last_name" placeholder="Last name" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="email" type="email" placeholder="Email" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="job_title" placeholder="Job title" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="hire_date" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <select name="department_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                    {(departments.data ?? []).map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">Save</button>
                    <button type="button" onClick={() => setShowForm(false)} className="rounded-md bg-slate-200 px-3 py-1.5 text-sm">Cancel</button>
                  </div>
                </form>
              )}
            </div>
          )}
        </Card>

        <Card title="Training records">
          {training.loading ? (
            <Loading />
          ) : (
            <ul className="space-y-3 text-sm">
              {(training.data ?? []).map((t) => (
                <li key={t.id} className="border-b border-slate-100 pb-2">
                  <div className="font-medium">{t.course_name}</div>
                  <div className="text-xs text-slate-500">{t.provider} · {t.completed_date ?? "in progress"}</div>
                  <div className="mt-1"><Badge tone={statusTone(t.status)}>{t.status}</Badge></div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {canEdit && (
        <div className="mt-6">
          <Card title="Add training record">
            <form onSubmit={addTraining} className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <select name="employee_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                {(employees.data ?? []).map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>
                ))}
              </select>
              <input name="course_name" placeholder="Course name" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="provider" placeholder="Provider" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <select name="status" className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option>Completed</option>
                <option>In Progress</option>
              </select>
              <div className="flex items-center gap-3">
                <input name="completed_date" type="date" className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                <label className="text-xs flex items-center gap-1"><input name="certificate" type="checkbox" /> Certificate</label>
                <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Add</button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
