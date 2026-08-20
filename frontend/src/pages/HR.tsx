import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { Badge, Card, EmptyState, ErrorMessage, Loading, PageHeader, ScrollTable, Stat, statusTone } from "../components/ui";
import { api } from "../api";
import { useApi } from "../useApi";

type AppUser = { id: number; full_name: string; email: string; role: { name: string }; site_id: number; active: boolean };

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
type LeaveType = {
  id: number;
  code: string;
  name: string;
  category: string;
  paid: boolean;
  accrual_days_per_month: number;
  grant_days_per_year: number | null;
  eligible_after_months: number;
  max_carryover_days: number | null;
  paid_out_year_end: boolean;
  contract_types: string;
  requires_document: boolean;
  active: boolean;
};
type LeaveBalance = {
  id: number;
  employee_id: number;
  leave_type_id: number;
  leave_type: string;
  leave_type_code: string;
  year: number;
  opened_days: number;
  accrued_days: number;
  taken_days: number;
  adjusted_days: number;
  paid_out_days: number;
  available_days: number;
};
type LeaveRequest = {
  id: number;
  request_number: string;
  employee_id: number;
  employee_name: string;
  leave_type_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  status: string;
  reason: string | null;
  rejection_reason: string | null;
  approved_at: string | null;
  created_at: string;
};
type TimeLog = {
  id: number;
  employee_id: number;
  work_date: string;
  clock_in: string;
  clock_out: string | null;
  hours_worked: number;
  standard_hours: number;
  overtime_hours: number;
  night_hours: number;
  public_holiday: boolean;
  is_rest_day: boolean;
  source: string;
  notes: string | null;
};
type AttendanceSummary = {
  site_id: number;
  start: string;
  end: string;
  employees_logged: number;
  total_hours: number;
  total_overtime_hours: number;
  total_night_hours: number;
  public_holiday_hours: number;
  label: string;
};
type Holiday = { id: number; name: string; holiday_date: string; site_id: number | null };
type PayrollPeriod = {
  id: number;
  site_id: number;
  period_start: string;
  period_end: string;
  status: string;
  processed_at: string | null;
  created_at: string;
};
type Payslip = {
  id: number;
  payslip_number: string;
  site_id: number;
  employee_id: number;
  period_id: number;
  period_start: string;
  period_end: string;
  base_salary: number;
  overtime_hours: number;
  overtime_pay: number;
  night_hours: number;
  night_differential_pay: number;
  public_holiday_hours: number;
  public_holiday_pay: number;
  leave_payout: number;
  allowances_pay: number;
  gross_pay: number;
  napsa_deduction: number;
  paye_deduction: number;
  nhima_deduction: number;
  total_deductions: number;
  net_pay: number;
  employer_napsa: number;
  employer_nhima: number;
  total_employer_cost: number;
  deductions_order: string;
  status: string;
  generated_at: string;
};
type PeriodSummary = {
  period_id: number;
  site_id: number;
  headcount: number;
  total_gross: number;
  total_napsa: number;
  total_paye: number;
  total_nhima: number;
  total_deductions: number;
  total_net: number;
  total_employer_cost: number;
};
type Allowance = { id: number; employee_id: number; allowance_type: string; amount: number; active: boolean; notes: string | null };
type HrCase = {
  id: number;
  case_number: string;
  site_id: number;
  employee_id: number;
  reporter_user_id: number;
  category: string;
  severity: string;
  status: string;
  title: string;
  description: string | null;
  assigned_user_id: number | null;
  resolution_notes: string | null;
  opened_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
};
type HrCaseNote = { id: number; case_id: number; user_id: number; note: string; is_private: boolean; created_at: string };
type CaseAnalytics = {
  site_id: number;
  total: number;
  open: number;
  resolved: number;
  closed: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  label: string;
};
type Shift = {
  id: number;
  site_id: number;
  department_id: number | null;
  name: string;
  start_time: string;
  end_time: string;
  shift_type: string;
  standard_hours: number;
  min_staff: number;
  is_night: boolean;
  description: string | null;
  active: boolean;
};
type RosterShift = {
  shift_id: number;
  shift_name: string;
  shift_type: string;
  is_night: boolean;
  min_staff: number;
  assigned: number;
  employees: number[];
  understaffed: boolean;
};
type RosterDay = {
  date: string;
  is_holiday: boolean;
  understaffed_any: boolean;
  overtime_hours: number;
  night_hours: number;
  cost_flags: { night_differential_applies: boolean; overtime_applies: boolean; holiday_pay_applies: boolean };
  shift_list: RosterShift[];
};
type RosterCost = {
  site_id: number;
  start: string;
  end: string;
  understaffed_days: number;
  total_overtime_hours: number;
  total_night_hours: number;
  public_holiday_days: number;
  label: string;
};
type StatutorySource = {
  config_key: string;
  display_name: string;
  category: string;
  source: string;
  effective_date: string;
  value: Record<string, unknown>;
  description: string;
};

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const R = {
  ADMIN: "Administrator",
  EXEC: "Executive",
  FINANCE: "Finance Officer",
  HR: "HR Officer",
  APPROVER: "Department Head",
  STAFF: "Staff",
};

function money(n: number | null | undefined): string {
  return (n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function clock(t: string): string {
  return (t || "").slice(0, 5);
}

function lastCalendarMonthRange() {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), 0);
  const start = new Date(end.getFullYear(), end.getMonth(), end.getDate() - 27);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

function leaveTone(status: string): "slate" | "green" | "amber" | "red" | "blue" {
  if (status === "Approved") return "green";
  if (status === "Requested") return "amber";
  if (status === "Taken") return "blue";
  if (status === "Rejected" || status === "Cancelled") return "red";
  return "slate";
}

function caseTone(status: string): "slate" | "green" | "amber" | "red" | "blue" {
  if (status === "Closed" || status === "Resolved") return "green";
  if (status === "Investigating") return "amber";
  if (status === "Logged" || status === "Under Review") return "blue";
  return "slate";
}

function severityTone(sev: string): "slate" | "green" | "amber" | "red" | "blue" {
  if (sev === "LOW") return "green";
  if (sev === "MEDIUM") return "amber";
  if (sev === "HIGH" || sev === "CRITICAL") return "red";
  return "slate";
}

const CASE_CATEGORIES = ["grievance", "disciplinary", "harassment", "performance", "wellness", "attendance", "other"];
const CASE_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const ALLOWANCE_TYPES = ["Housing", "Transport", "Meal", "Duty", "Medical", "Other"];

type RoleProps = {
  isHr: boolean;
  isAdmin: boolean;
  isStaff: boolean;
  isApprover: boolean;
  isExec: boolean;
  isFinance: boolean;
};

/* ------------------------------------------------------------------ */
/* Overview tab                                                        */
/* ------------------------------------------------------------------ */

function OverviewTab({ employees, departments, training, props }: { employees: Employee[]; departments: Department[]; training: Training[]; props: RoleProps }) {
  const canAnalytics = props.isHr || props.isExec || props.isApprover;
  const analytics = useApi<CaseAnalytics>(canAnalytics ? "/hr/cases/analytics" : null);

  const trainedIds = new Set(training.map((t) => t.employee_id));
  const trainedCount = [...trainedIds].filter((id) => employees.some((e) => e.id === id)).length;
  const activeCount = employees.filter((e) => e.employment_status === "Active").length;

  const empName = (id: number) => {
    const e = employees.find((x: Employee) => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`;
  };

  const trained = training.map((t) => ({ ...t, employee_name: empName(t.employee_id) })).sort(
    (a, b) => a.employee_name.localeCompare(b.employee_name) || a.course_name.localeCompare(b.course_name)
  );

  return (
    <div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Stat label="Employees" value={employees.length} hint={`${activeCount} active`} tone="indigo" />
        <Stat label="Departments" value={departments.length} hint="on this site" tone="cyan" />
        <Stat label="Training records" value={trained.length} hint={`${trainedCount} employees trained`} tone="emerald" />
        {canAnalytics && (
          <Stat
            label="Open HR cases"
            value={analytics.data?.open ?? 0}
            hint={`${analytics.data?.total ?? 0} total, ${analytics.data?.resolved ?? 0} resolved`}
            tone="amber"
          />
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={`Employee directory (${employees.length})`}>
          {employees.length === 0 ? (
            <EmptyState title="No employees yet" />
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[460px] text-sm">
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
                  {employees.map((emp) => (
                    <tr key={emp.id} className="border-b border-slate-100">
                      <td className="py-2 font-mono text-xs">{emp.employee_number}</td>
                      <td className="font-medium">{emp.first_name} {emp.last_name}</td>
                      <td>{emp.job_title}</td>
                      <td className="text-xs text-slate-500">{departments.find((d) => d.id === emp.department_id)?.name ?? emp.department_id}</td>
                      <td><Badge tone={statusTone(emp.employment_status)}>{emp.employment_status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          )}
        </Card>

        <Card title="Training & capacity">
          {trained.length === 0 ? (
            <EmptyState title="No training records yet" />
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[420px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Employee</th>
                    <th>Course</th>
                    <th>Provider</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {trained.slice(0, 12).map((t) => (
                    <tr key={t.id} className="border-b border-slate-100">
                      <td className="py-2 font-medium">{t.employee_name}</td>
                      <td>
                        {t.course_name}
                        {t.certificate && <span className="ml-1.5 text-[10px] font-bold uppercase text-emerald-600">✓ certified</span>}
                      </td>
                      <td className="text-xs text-slate-500">{t.provider}</td>
                      <td><Badge tone={statusTone(t.status)}>{t.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          )}
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Leave tab                                                           */
/* ------------------------------------------------------------------ */

function LeaveTab({ props }: { props: RoleProps }) {
  const types = useApi<LeaveType[]>("/hr/leave/types");
  const balances = useApi<LeaveBalance[]>("/hr/leave/balances");
  const requests = useApi<LeaveRequest[]>("/hr/leave/requests");
  const employees = useApi<Employee[]>(props.isHr ? "/hr/employees" : null);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showReject, setShowReject] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const myEmployeeId = props.isStaff ? (balances.data?.[0]?.employee_id ?? null) : null;

  async function submitRequest(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/hr/leave/requests", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(fd.get("employee_id") ?? myEmployeeId),
          leave_type_id: Number(fd.get("leave_type_id")),
          start_date: String(fd.get("start_date")),
          end_date: String(fd.get("end_date")),
          reason: String(fd.get("reason") || null),
        }),
      });
      setMessage("Leave request submitted.");
      setShowForm(false);
      balances.refresh();
      requests.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function act(url: string, method = "POST", body?: unknown) {
    setError(null);
    setMessage(null);
    try {
      await api(url, { method, body: body === undefined ? undefined : JSON.stringify(body) });
      requests.refresh();
      balances.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function runAccrual(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      const r = await api<{ posted_entries: number; already_present: number }>("/hr/leave/accrue", {
        method: "POST",
        body: JSON.stringify({ year: Number(fd.get("year")), month: Number(fd.get("month")) }),
      });
      setMessage(`Accrual complete: ${r.posted_entries} posted, ${r.already_present} already present.`);
      balances.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function runYearEnd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      const r = await api<{ paid_out_rows: number; carried_forward_rows: number }>("/hr/leave/year-end", {
        method: "POST",
        body: JSON.stringify({ year: Number(fd.get("year")) }),
      });
      setMessage(`Year-end close: ${r.paid_out_rows} paid out, ${r.carried_forward_rows} carried forward.`);
      balances.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  return (
    <div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <Card
            title={`Leave requests (${requests.data?.length ?? 0})`}
            actions={
              !props.isStaff && (
                <button onClick={() => setShowForm((v) => !v)} className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700">
                  {showForm ? "Close" : "New request"}
                </button>
              )
            }
          >
            {requests.loading ? (
              <Loading />
            ) : (requests.data?.length ?? 0) === 0 ? (
              <EmptyState title="No leave requests" />
            ) : (
              <ScrollTable>
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Number</th>
                      <th>Employee</th>
                      <th>Type</th>
                      <th>Dates</th>
                      <th>Days</th>
                      <th>Status</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(requests.data ?? []).map((req) => (
                      <tr key={req.id} className="border-b border-slate-100 align-top">
                        <td className="py-2 font-mono text-xs">{req.request_number}</td>
                        <td className="py-2">{req.employee_name}</td>
                        <td className="py-2">{req.leave_type}</td>
                        <td className="py-2 text-xs whitespace-nowrap">{fmtDate(req.start_date)} → {fmtDate(req.end_date)}</td>
                        <td className="py-2 tabular-nums">{req.days_requested}</td>
                        <td className="py-2">
                          <Badge tone={leaveTone(req.status)} dot>{req.status}</Badge>
                          {req.rejection_reason && <div className="mt-1 text-[11px] text-rose-600">{req.rejection_reason}</div>}
                        </td>
                        <td className="py-2">
                          <div className="flex flex-wrap justify-end gap-1">
                            {props.isStaff && req.status === "Requested" && (
                              <button onClick={() => act(`/hr/leave/requests/${req.id}/cancel`)} className="rounded-md bg-slate-100 px-2 py-1 text-xs hover:bg-slate-200">Cancel</button>
                            )}
                            {!props.isStaff && req.status === "Requested" && (
                              <>
                                <button onClick={() => act(`/hr/leave/requests/${req.id}/approve`)} className="rounded-md bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700">Approve</button>
                                <button onClick={() => setShowReject(req.id)} className="rounded-md bg-rose-100 px-2 py-1 text-xs text-rose-700 hover:bg-rose-200">Reject</button>
                              </>
                            )}
                            {!props.isStaff && req.status === "Approved" && props.isHr && (
                              <button onClick={() => act(`/hr/leave/requests/${req.id}/mark-taken`)} className="rounded-md bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700">Mark taken</button>
                            )}
                            {showReject === req.id && (
                              <div className="flex gap-1 items-center">
                                <input
                                  value={rejectReason}
                                  onChange={(e) => setRejectReason(e.target.value)}
                                  placeholder="Reason"
                                  className="rounded border border-slate-300 px-2 py-1 text-xs w-36"
                                />
                                <button
                                  onClick={() => { act(`/hr/leave/requests/${req.id}/reject`, "POST", { reason: rejectReason }); setShowReject(null); setRejectReason(""); }}
                                  className="rounded-md bg-rose-600 px-2 py-1 text-xs text-white"
                                >
                                  Confirm
                                </button>
                                <button onClick={() => setShowReject(null)} className="rounded-md bg-slate-100 px-2 py-1 text-xs">✕</button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            )}
          </Card>

          {(showForm || props.isStaff) && (
            <div className="mt-6">
              <Card title="Request leave">
                <form onSubmit={submitRequest} className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {!props.isStaff && (
                    <select name="employee_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                      <option value="">Employee…</option>
                      {(employees.data ?? []).map((e) => (
                        <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                      ))}
                    </select>
                  )}
                  <select name="leave_type_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                    <option value="">Leave type…</option>
                    {(types.data ?? []).map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                  <input name="start_date" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="end_date" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <div className="flex gap-2">
                    <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">Submit</button>
                    {!props.isStaff && <button type="button" onClick={() => setShowForm(false)} className="rounded-md bg-slate-200 px-3 py-1.5 text-sm">Close</button>}
                  </div>
                  <div className="col-span-2 md:col-span-5">
                    <input name="reason" placeholder="Reason (optional)" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  </div>
                </form>
              </Card>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <Card title="Leave balances">
            {balances.loading ? (
              <Loading />
            ) : (balances.data?.length ?? 0) === 0 ? (
              <EmptyState title="No balances yet" hint="Run the monthly accrual to populate balances." />
            ) : (
              <ScrollTable>
                <table className="w-full min-w-[280px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Type</th>
                      <th className="text-right">Available</th>
                      <th className="text-right">Taken</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(balances.data ?? []).map((b) => (
                      <tr key={b.id} className="border-b border-slate-100">
                        <td className="py-2">{b.leave_type} <span className="text-[10px] text-slate-400">({b.year})</span></td>
                        <td className="py-2 text-right font-semibold tabular-nums">{b.available_days.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                        <td className="py-2 text-right text-xs text-slate-500 tabular-nums">{b.taken_days.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            )}
          </Card>

          {props.isHr && (
            <>
              <Card title="Monthly accrual">
                <form onSubmit={runAccrual} className="flex gap-2">
                  <input name="year" type="number" defaultValue={currentYear} className="w-20 rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="month" type="number" defaultValue={currentMonth} min={1} max={12} className="w-16 rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Accrue</button>
                </form>
              </Card>
              <Card title="Year-end close">
                <form onSubmit={runYearEnd} className="flex gap-2">
                  <input name="year" type="number" defaultValue={currentYear} className="w-20 rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <button className="rounded-md bg-amber-600 px-3 py-1.5 text-sm text-white">Close year</button>
                </form>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Attendance tab                                                      */
/* ------------------------------------------------------------------ */

function AttendanceTab({ props }: { props: RoleProps }) {
  const [from, setFrom] = useState(lastCalendarMonthRange().start);
  const [to, setTo] = useState(lastCalendarMonthRange().end);
  const params = `start=${from}&end=${to}`;

  const logs = useApi<TimeLog[]>(`/hr/attendance/logs?${params}`);
  const summary = useApi<AttendanceSummary>(props.isStaff ? null : `/hr/attendance/summary?${params}`);
  const weekly = useApi<{
    weekly_standard_hours: number;
    weeks: Array<{ week_start: string; employee_id: number; employee_name: string; hours_worked: number; overtime_hours: number; threshold_exceeded: boolean }>;
  }>(props.isStaff ? null : `/hr/attendance/weekly-overview?${params}`);
  const holidays = useApi<Holiday[]>("/hr/attendance/holidays");
  const employees = useApi<Employee[]>(props.isHr ? "/hr/employees" : null);
  const shifts = useApi<Shift[]>(props.isHr ? "/hr/roster/shifts" : null);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function addLog(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      const shiftId = fd.get("shift_id");
      await api("/hr/attendance/logs", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(fd.get("employee_id")),
          work_date: String(fd.get("work_date")),
          clock_in: String(fd.get("clock_in")),
          clock_out: String(fd.get("clock_out")),
          shift_id: shiftId ? Number(shiftId) : null,
          notes: String(fd.get("notes") || null),
        }),
      });
      setMessage("Time log added.");
      (e.target as HTMLFormElement).reset();
      logs.refresh();
      summary.refresh();
      weekly.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addHoliday(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const fd = new FormData(e.target as HTMLFormElement);
    const q = new URLSearchParams({ name: String(fd.get("name")), holiday_date: String(fd.get("holiday_date")) });
    try {
      await api(`/hr/attendance/holidays?${q}`, { method: "POST" });
      setMessage("Public holiday added.");
      holidays.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const empName = (id: number) => {
    const e = employees.data?.find((x) => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`;
  };

  return (
    <div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <Card className="mb-6" title="Period">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-500">
            From
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs text-slate-500">
            To
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </label>
        </div>
      </Card>

      {!props.isStaff && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Stat label="Employees logged" value={summary.data?.employees_logged ?? 0} tone="indigo" />
          <Stat label="Total hours" value={summary.data ? money(summary.data.total_hours) : 0} tone="emerald" />
          <Stat label="Overtime hours" value={summary.data ? money(summary.data.total_overtime_hours) : 0} tone="amber" />
          <Stat label="Night hours" value={summary.data ? money(summary.data.total_night_hours) : 0} tone="cyan" />
        </div>
      )}

      {props.isStaff ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card title="My time logs" className="lg:col-span-2">
            {logs.loading ? (
              <Loading />
            ) : (logs.data?.length ?? 0) === 0 ? (
              <EmptyState title="No time logs in range" />
            ) : (
              <ScrollTable>
                <table className="w-full min-w-[560px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Date</th>
                      <th>Clock in</th>
                      <th>Clock out</th>
                      <th>Hours</th>
                      <th>Night</th>
                      <th>Flags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(logs.data ?? []).map((t) => (
                      <tr key={t.id} className="border-b border-slate-100">
                        <td className="py-2">{fmtDate(t.work_date)}</td>
                        <td className="py-2 font-mono text-xs">{clock(t.clock_in)}</td>
                        <td className="py-2 font-mono text-xs">{t.clock_out ? clock(t.clock_out) : "—"}</td>
                        <td className="py-2 tabular-nums">{t.hours_worked}</td>
                        <td className="py-2 tabular-nums">{t.night_hours}</td>
                        <td className="py-2">
                          {t.overtime_hours > 0 && <Badge tone="amber">OT {t.overtime_hours}h</Badge>}
                          {t.public_holiday && <span className="ml-1"><Badge tone="blue">Holiday</Badge></span>}
                          {t.is_rest_day && <span className="ml-1"><Badge tone="slate">Rest day</Badge></span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            )}
          </Card>
          <Card title="Public holidays">
            {(holidays.data ?? []).map((h) => (
              <div key={h.id} className="flex justify-between py-2 border-b border-slate-100 text-sm">
                <span>{h.name}</span>
                <span className="text-slate-500">{fmtDate(h.holiday_date)}</span>
              </div>
            ))}
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title={`Time logs (${logs.data?.length ?? 0})`}>
            {logs.loading ? (
              <Loading />
            ) : (logs.data?.length ?? 0) === 0 ? (
              <EmptyState title="No time logs in range" />
            ) : (
              <ScrollTable>
                <table className="w-full min-w-[600px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Date</th>
                      <th>Employee</th>
                      <th>Clock in</th>
                      <th>Clock out</th>
                      <th>Hours</th>
                      <th>OT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(logs.data ?? []).slice(0, 40).map((t) => (
                      <tr key={t.id} className="border-b border-slate-100">
                        <td className="py-2">{fmtDate(t.work_date)}</td>
                        <td className="py-2">{empName(t.employee_id)}</td>
                        <td className="py-2 font-mono text-xs">{clock(t.clock_in)}</td>
                        <td className="py-2 font-mono text-xs">{t.clock_out ? clock(t.clock_out) : "—"}</td>
                        <td className="py-2 tabular-nums">{t.hours_worked}</td>
                        <td className="py-2 tabular-nums">{t.overtime_hours}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            )}
          </Card>

          <div className="space-y-6">
            <Card title="Weekly overview (48h threshold)">
              {weekly.data?.weeks?.length ? (
                <ScrollTable>
                  <table className="w-full min-w-[380px] text-sm">
                    <thead>
                      <tr className="text-left text-xs text-slate-500 border-b">
                        <th className="py-2">Week</th>
                        <th>Employee</th>
                        <th className="text-right">Hours</th>
                        <th className="text-right">OT</th>
                      </tr>
                    </thead>
                    <tbody>
                      {weekly.data.weeks.map((w, i) => (
                        <tr key={`${w.week_start}-${w.employee_id}-${i}`} className="border-b border-slate-100">
                          <td className="py-2 text-xs">{fmtDate(w.week_start)}</td>
                          <td className="py-2">{w.employee_name}</td>
                          <td className="py-2 text-right tabular-nums">{w.hours_worked}</td>
                          <td className="py-2 text-right">
                            {w.overtime_hours > 0 ? <Badge tone="amber">{w.overtime_hours}h</Badge> : <span className="text-xs text-slate-400">—</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollTable>
              ) : (
                <EmptyState title="No weekly rows in range" />
              )}
            </Card>

            <Card title="Public holidays">
              {(holidays.data ?? []).map((h) => (
                <div key={h.id} className="flex justify-between py-2 border-b border-slate-100 text-sm">
                  <span>{h.name}</span>
                  <span className="text-slate-500">{fmtDate(h.holiday_date)}</span>
                </div>
              ))}
              {props.isHr && (
                <form onSubmit={addHoliday} className="grid grid-cols-3 gap-2 mt-4">
                  <input name="name" placeholder="Holiday name" required className="col-span-2 rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <input name="holiday_date" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
                  <button className="col-span-3 rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Add holiday</button>
                </form>
              )}
            </Card>
          </div>
        </div>
      )}

      {props.isHr && (
        <div className="mt-6">
          <Card title="Record time log">
            <form onSubmit={addLog} className="grid grid-cols-2 md:grid-cols-6 gap-3">
              <select name="employee_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Employee…</option>
                {(employees.data ?? []).map((e) => (
                  <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                ))}
              </select>
              <select name="shift_id" className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Shift (auto)</option>
                {(shifts.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>{s.name} {clock(s.start_time)}–{clock(s.end_time)}</option>
                ))}
              </select>
              <input name="work_date" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="clock_in" type="datetime-local" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <input name="clock_out" type="datetime-local" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">Save log</button>
              <div className="col-span-2 md:col-span-6">
                <input name="notes" placeholder="Notes (optional)" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Payslip detail card                                                 */
/* ------------------------------------------------------------------ */

function PayslipCard({ slip }: { slip: Payslip }) {
  return (
    <Card title={`Payslip ${slip.payslip_number}`}>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Period</span>{fmtDate(slip.period_start)} → {fmtDate(slip.period_end)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Base salary</span>{money(slip.base_salary)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Allowances</span>{money(slip.allowances_pay)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">OT ({slip.overtime_hours}h)</span>{money(slip.overtime_pay)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Night ({slip.night_hours}h)</span>{money(slip.night_differential_pay)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Public holiday</span>{money(slip.public_holiday_pay)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Gross</span>{money(slip.gross_pay)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Leave payout</span>{money(slip.leave_payout)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">NAPSA</span>{money(slip.napsa_deduction)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">PAYE</span>{money(slip.paye_deduction)}</div>
        <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">NHIMA</span>{money(slip.nhima_deduction)}</div>
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 block">Net pay</span><b>{money(slip.net_pay)}</b></div>
      </div>
      <p className="mt-4 text-xs text-slate-400">Deductions order: {slip.deductions_order} · Employer cost {money(slip.total_employer_cost)}</p>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Payroll tab                                                         */
/* ------------------------------------------------------------------ */

function PayrollTab({ props }: { props: RoleProps }) {
  const periods = useApi<PayrollPeriod[]>("/hr/payroll/periods");
  const allowances = useApi<Allowance[]>("/hr/payroll/allowances");
  const employees = useApi<Employee[]>(props.isHr ? "/hr/employees" : null);

  const [selected, setSelected] = useState<number | null>(null);
  const [summary, setSummary] = useState<PeriodSummary | null>(null);
  const [slips, setSlips] = useState<Payslip[] | null>(null);
  const [mySlip, setMySlip] = useState<Payslip | null>(null);
  const [preview, setPreview] = useState<Record<string, number | string> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function selectPeriod(id: number) {
    setSelected(id);
    setSummary(null);
    setSlips(null);
    setMySlip(null);
    setPreview(null);
    setError(null);
    try {
      if (props.isStaff) {
        const slip = await api<Payslip>(`/hr/payroll/payslips/my?period_id=${id}`);
        setMySlip(slip);
      } else {
        const [s, p] = await Promise.all([
          api<PeriodSummary>(`/hr/payroll/periods/${id}/summary`),
          api<Payslip[]>(`/hr/payroll/periods/${id}/payslips`),
        ]);
        setSummary(s);
        setSlips(p);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function createPeriod(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/hr/payroll/periods", {
        method: "POST",
        body: JSON.stringify({ period_start: String(fd.get("period_start")), period_end: String(fd.get("period_end")) }),
      });
      setMessage("Payroll period created.");
      periods.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function generate(periodId: number) {
    setError(null);
    setMessage(null);
    try {
      const created = await api<Payslip[]>(`/hr/payroll/periods/${periodId}/generate`, { method: "POST" });
      setMessage(`${created.length} payslips generated.`);
      if (selected === periodId) await selectPeriod(periodId);
      periods.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addAllowance(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/hr/payroll/allowances", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(fd.get("employee_id")),
          allowance_type: String(fd.get("allowance_type")),
          amount: Number(fd.get("amount")),
          active: true,
          notes: String(fd.get("notes") || null),
        }),
      });
      setMessage("Allowance added.");
      allowances.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function runPreview(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (!selected) return;
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      const p = await api<Record<string, number | string>>(`/hr/payroll/preview/${Number(fd.get("employee_id"))}?period_id=${selected}`);
      setPreview(p);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const empName = (id: number) => {
    const e = employees.data?.find((x) => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`;
  };

  const slipTone = (status: string): "green" | "amber" => (status === "Processed" ? "green" : "amber");

  return (
    <div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      {props.isHr && (
        <Card className="mb-6" title="Create payroll period">
          <form onSubmit={createPeriod} className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <input name="period_start" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input name="period_end" type="date" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Create period</button>
          </form>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title={`Payroll periods (${periods.data?.length ?? 0})`}>
          {periods.loading ? (
            <Loading />
          ) : (periods.data?.length ?? 0) === 0 ? (
            <EmptyState title="No periods yet" hint="Create a period to start the payroll run." />
          ) : (
            <div className="space-y-2">
              {(periods.data ?? []).map((p) => (
                <div key={p.id} className={`rounded-xl border p-3 transition-colors ${selected === p.id ? "border-brand-500 bg-brand-50" : "border-slate-200"}`}>
                  <button onClick={() => selectPeriod(p.id)} className="w-full text-left">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold">{fmtDate(p.period_start)} → {fmtDate(p.period_end)}</span>
                      <Badge tone={slipTone(p.status)}>{p.status}</Badge>
                    </div>
                  </button>
                  {props.isHr && p.status === "Draft" && (
                    <button onClick={() => generate(p.id)} className="mt-2 rounded-md bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700">
                      Generate payslips
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        <div className="lg:col-span-2 space-y-6">
          {selected === null && (
            <Card title="Select a period">
              <p className="text-sm text-slate-500">Choose a payroll period to view its summary and payslips.</p>
            </Card>
          )}

          {selected !== null && props.isStaff && mySlip && <PayslipCard slip={mySlip} />}

          {selected !== null && !props.isStaff && summary && (
            <Card title="Period summary">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                <Stat label="Headcount" value={summary.headcount} tone="indigo" />
                <Stat label="Gross" value={money(summary.total_gross)} tone="emerald" />
                <Stat label="Deductions" value={money(summary.total_deductions)} tone="amber" />
                <Stat label="Net pay" value={money(summary.total_net)} tone="cyan" />
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">NAPSA</span>{money(summary.total_napsa)}</div>
                <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">PAYE</span>{money(summary.total_paye)}</div>
                <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">NHIMA</span>{money(summary.total_nhima)}</div>
                <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2 col-span-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Employer cost</span>{money(summary.total_employer_cost)}</div>
              </div>
            </Card>
          )}

          {selected !== null && !props.isStaff && slips && (
            <Card title={`Payslips (${slips.length})`}>
              <ScrollTable>
                <table className="w-full min-w-[680px] text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b">
                      <th className="py-2">Number</th>
                      <th>Employee</th>
                      <th className="text-right">Gross</th>
                      <th className="text-right">Deductions</th>
                      <th className="text-right">Net</th>
                      <th className="text-right">Employer cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {slips.map((s) => (
                      <tr key={s.id} className="border-b border-slate-100">
                        <td className="py-2 font-mono text-xs">{s.payslip_number}</td>
                        <td className="py-2">{empName(s.employee_id)}</td>
                        <td className="py-2 text-right tabular-nums">{money(s.gross_pay)}</td>
                        <td className="py-2 text-right tabular-nums text-amber-700">{money(s.total_deductions)}</td>
                        <td className="py-2 text-right font-semibold tabular-nums">{money(s.net_pay)}</td>
                        <td className="py-2 text-right text-xs text-slate-500 tabular-nums">{money(s.total_employer_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollTable>
            </Card>
          )}

          {selected !== null && props.isHr && (
            <Card title="Payroll preview (dry run)">
              <form onSubmit={runPreview} className="flex flex-wrap gap-2 items-end">
                <label className="text-xs text-slate-500 flex-1 min-w-[160px]">
                  Employee
                  <select name="employee_id" required className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                    <option value="">Choose…</option>
                    {(employees.data ?? []).map((e) => (
                      <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                    ))}
                  </select>
                </label>
                <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white">Preview</button>
              </form>
              {preview && (
                <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                  <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Base</span>{money(preview.base_salary as number)}</div>
                  <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Allowances</span>{money(preview.allowances_pay as number)}</div>
                  <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">OT ({preview.overtime_hours as number}h)</span>{money(preview.overtime_pay as number)}</div>
                  <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Night ({preview.night_hours as number}h)</span>{money(preview.night_differential_pay as number)}</div>
                  <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Gross</span>{money(preview.gross_pay as number)}</div>
                  <div className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">Deductions</span>{money(preview.total_deductions as number)}</div>
                  <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2"><span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 block">Net</span><b>{money(preview.net_pay as number)}</b></div>
                </div>
              )}
            </Card>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Employee allowances">
          {allowances.loading ? (
            <Loading />
          ) : (allowances.data?.length ?? 0) === 0 ? (
            <EmptyState title="No allowances recorded" />
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[360px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Employee</th>
                    <th>Type</th>
                    <th className="text-right">Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(allowances.data ?? []).map((a) => (
                    <tr key={a.id} className="border-b border-slate-100">
                      <td className="py-2">{empName(a.employee_id)}</td>
                      <td className="py-2">{a.allowance_type}</td>
                      <td className="py-2 text-right tabular-nums">{money(a.amount)}</td>
                      <td className="py-2"><Badge tone={a.active ? "green" : "slate"}>{a.active ? "Active" : "Inactive"}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          )}
        </Card>

        {props.isHr && (
          <Card title="Add allowance">
            <form onSubmit={addAllowance} className="grid grid-cols-2 gap-3">
              <select name="employee_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Employee…</option>
                {(employees.data ?? []).map((e) => (
                  <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                ))}
              </select>
              <select name="allowance_type" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Type…</option>
                {ALLOWANCE_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <input name="amount" type="number" step="0.01" min="0" placeholder="Amount" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">Add</button>
              <div className="col-span-2">
                <input name="notes" placeholder="Notes (optional)" className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* HR cases tab                                                        */
/* ------------------------------------------------------------------ */

function CasesTab({ props }: { props: RoleProps }) {
  const cases = useApi<HrCase[]>("/hr/cases");
  const analytics = useApi<CaseAnalytics>(props.isStaff ? null : "/hr/cases/analytics");
  const employees = useApi<Employee[]>(props.isHr ? "/hr/employees" : null);
  const assignees = useApi<AppUser[]>(props.isHr ? "/hr/cases/assignees" : null);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [openForm, setOpenForm] = useState(false);
  const [notes, setNotes] = useState<Record<number, HrCaseNote[]>>({});
  const [noteText, setNoteText] = useState("");
  const [privateNote, setPrivateNote] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [assignFor, setAssignFor] = useState<Record<number, string>>({});
  const [resolutionText, setResolutionText] = useState<Record<number, string>>({});

  async function createCase(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api("/hr/cases", {
        method: "POST",
        body: JSON.stringify({
          employee_id: props.isStaff ? 0 : Number(fd.get("employee_id")),
          category: String(fd.get("category")),
          severity: String(fd.get("severity")),
          title: String(fd.get("title")),
          description: String(fd.get("description") || null),
        }),
      });
      setMessage("Case opened.");
      setOpenForm(false);
      cases.refresh();
      analytics.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadNotes(caseId: number) {
    setExpanded(caseId === expanded ? null : caseId);
    setNoteText("");
    setPrivateNote(false);
    try {
      const rows = await api<HrCaseNote[]>(`/hr/cases/${caseId}/notes`);
      setNotes((prev) => ({ ...prev, [caseId]: rows }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addNote(caseId: number) {
    setError(null);
    try {
      await api(`/hr/cases/${caseId}/notes`, {
        method: "POST",
        body: JSON.stringify({ note: noteText, is_private: privateNote }),
      });
      setNoteText("");
      setPrivateNote(false);
      const rows = await api<HrCaseNote[]>(`/hr/cases/${caseId}/notes`);
      setNotes((prev) => ({ ...prev, [caseId]: rows }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function transition(caseId: number, status: string) {
    setError(null);
    setMessage(null);
    try {
      await api(`/hr/cases/${caseId}/status`, {
        method: "POST",
        body: JSON.stringify({ status, resolution_notes: resolutionText[caseId] || null }),
      });
      setMessage(`Case moved to ${status}.`);
      setResolutionText((r) => ({ ...r, [caseId]: "" }));
      cases.refresh();
      analytics.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function assignCase(caseId: number, assigneeId: number) {
    if (!assigneeId) return;
    setError(null);
    setMessage(null);
    try {
      await api(`/hr/cases/${caseId}/assign`, {
        method: "POST",
        body: JSON.stringify({ assignee_user_id: assigneeId }),
      });
      setMessage("Case assigned.");
      setAssignFor((a) => ({ ...a, [caseId]: "" }));
      cases.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const empName = (id: number) => {
    const e = employees.data?.find((x) => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`;
  };

  const assigneeName = (id: number | null) => {
    if (!id) return null;
    const u = assignees.data?.find((x) => x.id === id);
    return u ? (u.full_name ?? `user #${id}`) : `user #${id}`;
  };

  const nextStatus = (current: string): string | null => {
    const map: Record<string, string> = {
      Logged: "Under Review",
      "Under Review": "Investigating",
      Investigating: "Resolved",
      Resolved: "Closed",
    };
    return map[current] ?? null;
  };

  return (
    <div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      {!props.isStaff && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Stat label="Total cases" value={analytics.data?.total ?? 0} tone="indigo" />
          <Stat label="Open" value={analytics.data?.open ?? 0} tone="amber" />
          <Stat label="Resolved" value={analytics.data?.resolved ?? 0} tone="emerald" />
          <Stat label="Closed" value={analytics.data?.closed ?? 0} tone="cyan" />
        </div>
      )}

      <Card
        title={`Cases (${cases.data?.length ?? 0})`}
        actions={
          !props.isExec && (
            <button onClick={() => setOpenForm((v) => !v)} className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700">
              {openForm ? "Close" : "Open case"}
            </button>
          )
        }
      >
        {cases.loading ? (
          <Loading />
        ) : (cases.data?.length ?? 0) === 0 ? (
          <EmptyState title="No cases" />
        ) : (
          <div className="space-y-3">
            {(cases.data ?? []).map((c) => (
              <div key={c.id} className="rounded-xl border border-slate-200 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-slate-400">{c.case_number}</span>
                  <span className="text-sm font-semibold">{c.title}</span>
                  <Badge tone={severityTone(c.severity)}>{c.severity}</Badge>
                  <Badge tone="slate">{c.category}</Badge>
                  <Badge tone={caseTone(c.status)} dot>{c.status}</Badge>
                  {c.assigned_user_id && <Badge tone="blue">Assigned: {assigneeName(c.assigned_user_id)}</Badge>}
                  <div className="ml-auto flex flex-wrap gap-1">
                    {props.isHr && (
                      <>
                        <select
                          value={assignFor[c.id] ?? ""}
                          onChange={(e) => setAssignFor((s) => ({ ...s, [c.id]: e.target.value }))}
                          className="rounded border border-slate-300 px-1.5 py-0.5 text-xs"
                        >
                          <option value="">Assign to…</option>
                          {(assignees.data ?? []).map((u) => (
                            <option key={u.id} value={u.id}>{u.full_name}</option>
                          ))}
                        </select>
                        <button onClick={() => assignCase(c.id, Number(assignFor[c.id]))} disabled={!assignFor[c.id]} className="rounded-md bg-indigo-600 px-2 py-1 text-xs text-white hover:bg-indigo-700 disabled:opacity-40">Assign</button>
                      </>
                    )}
                    {props.isHr && nextStatus(c.status) && (
                      <div className="flex items-center gap-1">
                        {nextStatus(c.status) === "Resolved" && (
                          <input
                            value={resolutionText[c.id] ?? ""}
                            onChange={(e) => setResolutionText((r) => ({ ...r, [c.id]: e.target.value }))}
                            placeholder="Resolution notes…"
                            className="rounded border border-slate-300 px-2 py-1 text-xs w-32"
                          />
                        )}
                        <button onClick={() => transition(c.id, nextStatus(c.status)!)} className="rounded-md bg-brand-600 px-2 py-1 text-xs text-white hover:bg-brand-700">
                          Move to {nextStatus(c.status)}
                        </button>
                      </div>
                    )}
                    <button onClick={() => loadNotes(c.id)} className="rounded-md bg-slate-100 px-2 py-1 text-xs hover:bg-slate-200">
                      {expanded === c.id ? "Hide notes" : "Notes"}
                    </button>
                  </div>
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  {empName(c.employee_id)} · opened {fmtDate(c.opened_at)}
                  {c.resolution_notes && <span className="text-slate-400"> · {c.resolution_notes}</span>}
                </div>
                {c.description && <p className="mt-1 text-sm text-slate-600">{c.description}</p>}

                {expanded === c.id && (
                  <div className="mt-3 border-t border-slate-100 pt-3">
                    {(notes[c.id] ?? []).map((n) => (
                      <div key={n.id} className="flex items-start gap-2 py-1.5 text-sm">
                        <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${n.is_private ? "bg-amber-400" : "bg-indigo-400"}`} />
                        <div className="min-w-0">
                          <span className="text-slate-700">{n.note}</span>
                          {n.is_private && <span className="ml-1.5 text-[10px] font-bold uppercase text-amber-600">private</span>}
                          <span className="block text-[11px] text-slate-400">{fmtDate(n.created_at)}</span>
                        </div>
                      </div>
                    ))}
                    <div className="mt-2 flex flex-wrap gap-2">
                      <input
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="Add a note…"
                        className="flex-1 min-w-[200px] rounded border border-slate-300 px-2 py-1.5 text-sm"
                      />
                      <label className="flex items-center gap-1 text-xs text-slate-500">
                        <input type="checkbox" checked={privateNote} onChange={(e) => setPrivateNote(e.target.checked)} /> Private
                      </label>
                      <button onClick={() => addNote(c.id)} disabled={!noteText.trim()} className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white disabled:opacity-40">
                        Add
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {openForm && (
        <div className="mt-6">
          <Card title="Open a case">
            <form onSubmit={createCase} className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {!props.isStaff && (
                <select name="employee_id" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                  <option value="">Employee…</option>
                  {(employees.data ?? []).map((e) => (
                    <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                  ))}
                </select>
              )}
              <select name="category" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                <option value="">Category…</option>
                {CASE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <select name="severity" required className="rounded border border-slate-300 px-2 py-1.5 text-sm">
                {CASE_SEVERITIES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <input name="title" placeholder="Title" required className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
              <div className="col-span-2 md:col-span-4">
                <textarea name="description" placeholder="Description (optional)" rows={3} className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </div>
              <div className="col-span-2 md:col-span-4 flex gap-2">
                <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">Open case</button>
                <button type="button" onClick={() => setOpenForm(false)} className="rounded-md bg-slate-200 px-3 py-1.5 text-sm">Cancel</button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Roster tab                                                          */
/* ------------------------------------------------------------------ */

type AssignmentRow = {
  id: number;
  employee_id: number;
  employee_number: string;
  employee_name: string;
  shift_id: number;
  shift_name: string;
  work_date: string;
  status: string;
  note: string | null;
};
type ConflictEmployee = { id: number; employee_number: string; full_name: string; job_title: string; department_id: number };
type RosterConflict = {
  date: string;
  shift_id: number;
  shift_name: string;
  shift_type: string;
  is_night: boolean;
  min_staff: number;
  assigned: number;
  shortage: number;
  eligible_employees: ConflictEmployee[];
};

function RosterTab({ props }: { props: RoleProps }) {
  const canEdit = props.isHr;
  const [from, setFrom] = useState(lastCalendarMonthRange().start);
  const [to, setTo] = useState(lastCalendarMonthRange().end);
  const params = `start=${from}&end=${to}`;

  const shifts = useApi<Shift[]>("/hr/roster/shifts");
  const roster = useApi<{ site_id: number; start: string; end: string; days: RosterDay[] }>(`/hr/roster?${params}`);
  const cost = useApi<RosterCost>(`/hr/roster/cost?${params}`);
  const assignments = useApi<AssignmentRow[]>(`/hr/roster/assignments?${params}`);
  const conflicts = useApi<RosterConflict[]>(`/hr/roster/conflicts?${params}`);
  const employees = useApi<Employee[]>(canEdit ? "/hr/employees" : null);
  const departments = useApi<Department[]>(canEdit ? "/hr/departments" : null);

  const [error, setError] = useState<string | null>(null);
  const derivedError = shifts.error || roster.error || cost.error || assignments.error || conflicts.error || error;
  const [message, setMessage] = useState<string | null>(null);
  const [editShiftId, setEditShiftId] = useState<number | null>(null);
  const [newShiftOpen, setNewShiftOpen] = useState(false);
  const [editAssignId, setEditAssignId] = useState<number | null>(null);
  const [swapFor, setSwapFor] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);

  async function run(url: string, method: string, body?: unknown) {
    setError(null);
    setMessage(null);
    try {
      await api(url, { method, body: body === undefined ? undefined : JSON.stringify(body) });
      shifts.refresh();
      roster.refresh();
      cost.refresh();
      assignments.refresh();
      conflicts.refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveShift(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData(e.target as HTMLFormElement);
    const payload = {
      name: String(fd.get("name")),
      start_time: String(fd.get("start_time")),
      end_time: String(fd.get("end_time")),
      shift_type: String(fd.get("shift_type")),
      standard_hours: Number(fd.get("standard_hours")),
      min_staff: Number(fd.get("min_staff")),
      department_id: fd.get("department_id") ? Number(fd.get("department_id")) : null,
    };
    try {
      if (editShiftId) {
        await api(`/hr/roster/shifts/${editShiftId}`, { method: "PUT", body: JSON.stringify(payload) });
        setMessage("Shift updated.");
        setEditShiftId(null);
      } else {
        await api("/hr/roster/shifts", { method: "POST", body: JSON.stringify(payload) });
        setMessage("Shift created.");
        setNewShiftOpen(false);
      }
      shifts.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function deactivateShift(id: number, name: string) {
    if (!window.confirm(`Deactivate shift "${name}"? It will leave the pickers but keep its history.`)) return;
    await run(`/hr/roster/shifts/${id}`, "DELETE");
  }

  async function saveAssignment(e: FormEvent) {
    e.preventDefault();
    if (editAssignId === null) return;
    setBusy(true);
    const fd = new FormData(e.target as HTMLFormElement);
    try {
      await api(`/hr/roster/assignments/${editAssignId}`, {
        method: "PUT",
        body: JSON.stringify({
          employee_id: Number(fd.get("employee_id")),
          shift_id: Number(fd.get("shift_id")),
          work_date: String(fd.get("work_date")),
        }),
      });
      setMessage("Assignment updated.");
      setEditAssignId(null);
      assignments.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function unassign(id: number, label: string) {
    if (!window.confirm(`Remove ${label} from this assignment?`)) return;
    await run(`/hr/roster/assignments/${id}`, "DELETE");
  }

  async function doSwap(assignment: AssignmentRow, otherEmployeeId: number) {
    if (!otherEmployeeId) return;
    if (!window.confirm(`Swap ${assignment.employee_name} with ${employeeLabel(otherEmployeeId)} on ${assignment.work_date}?`)) return;
    await run(`/hr/roster/assignments/${assignment.id}/swap?other_employee_id=${otherEmployeeId}`, "PUT");
    setSwapFor((s) => ({ ...s, [assignment.id]: "" }));
  }

  async function fillConflict(conflict: RosterConflict, employeeId: number) {
    if (!employeeId) return;
    await run("/hr/roster/assignments", "POST", {
      employee_id: employeeId,
      shift_id: conflict.shift_id,
      work_date: conflict.date,
    });
  }

  function employeeLabel(id: number): string {
    const e = employees.data?.find((x) => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`;
  }

  return (
    <div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <Card className="mb-6" title="Period">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-500">
            From
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs text-slate-500">
            To
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </label>
        </div>
      </Card>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Stat label="Understaffed days" value={cost.data?.understaffed_days ?? 0} tone="rose" />
        {derivedError && <div className="col-span-4"><ErrorMessage message={derivedError} /></div>}
        <Stat label="Overtime hours" value={cost.data ? money(cost.data.total_overtime_hours) : 0} tone="amber" />
        <Stat label="Night hours" value={cost.data ? money(cost.data.total_night_hours) : 0} tone="cyan" />
        <Stat label="Open conflicts" value={conflicts.data?.length ?? 0} tone="indigo" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card
          title="Shifts"
          actions={
            canEdit && (
              <button onClick={() => { setNewShiftOpen((v) => !v); setEditShiftId(null); }} className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700">
                {newShiftOpen ? "Close" : "New shift"}
              </button>
            )
          }
        >
          {newShiftOpen && canEdit && (
            <form onSubmit={saveShift} className="mb-4 grid grid-cols-2 gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <input name="name" placeholder="Name" required className="rounded border border-slate-300 px-2 py-1 text-sm" />
              <input name="shift_type" defaultValue="day" placeholder="Type" className="rounded border border-slate-300 px-2 py-1 text-sm" />
              <label className="text-xs text-slate-500">Start
                <input name="start_time" type="time" defaultValue="08:00" required className="mt-0.5 block w-full rounded border border-slate-300 px-2 py-1 text-sm" />
              </label>
              <label className="text-xs text-slate-500">End
                <input name="end_time" type="time" defaultValue="16:00" required className="mt-0.5 block w-full rounded border border-slate-300 px-2 py-1 text-sm" />
              </label>
              <input name="min_staff" type="number" defaultValue={1} min={1} required placeholder="Min staff" className="rounded border border-slate-300 px-2 py-1 text-sm" />
              <input name="standard_hours" type="number" step="0.5" defaultValue={8} required placeholder="Std hours" className="rounded border border-slate-300 px-2 py-1 text-sm" />
              <select name="department_id" className="rounded border border-slate-300 px-2 py-1 text-sm col-span-2">
                <option value="">All departments</option>
                {(departments.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <button disabled={busy} className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white disabled:opacity-50 col-span-2">Create shift</button>
            </form>
          )}
          {shifts.loading ? (
            <Loading />
          ) : (
            <div className="space-y-2">
              {(shifts.data ?? []).map((s) =>
                editShiftId === s.id ? (
                  <form key={s.id} onSubmit={saveShift} className="rounded-xl border border-slate-200 bg-slate-50 p-3 grid grid-cols-2 gap-2">
                    <input name="name" defaultValue={s.name} required placeholder="Name" className="rounded border border-slate-300 px-2 py-1 text-sm" />
                    <input name="shift_type" defaultValue={s.shift_type} className="rounded border border-slate-300 px-2 py-1 text-sm" />
                    <label className="text-xs text-slate-500">Start
                      <input name="start_time" type="time" defaultValue={clock(s.start_time)} required className="mt-0.5 block w-full rounded border border-slate-300 px-2 py-1 text-sm" />
                    </label>
                    <label className="text-xs text-slate-500">End
                      <input name="end_time" type="time" defaultValue={clock(s.end_time)} required className="mt-0.5 block w-full rounded border border-slate-300 px-2 py-1 text-sm" />
                    </label>
                    <input name="min_staff" type="number" defaultValue={s.min_staff} min={1} required className="rounded border border-slate-300 px-2 py-1 text-sm" />
                    <input name="standard_hours" type="number" step="0.5" defaultValue={s.standard_hours} required className="rounded border border-slate-300 px-2 py-1 text-sm" />
                    <select name="department_id" defaultValue={s.department_id ?? ""} className="rounded border border-slate-300 px-2 py-1 text-sm col-span-2">
                      <option value="">All departments</option>
                      {(departments.data ?? []).map((d) => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                    <button disabled={busy} className="rounded-md bg-emerald-600 px-3 py-1 text-xs text-white disabled:opacity-50">Save</button>
                    <button type="button" onClick={() => setEditShiftId(null)} className="rounded-md bg-slate-200 px-3 py-1 text-xs">Cancel</button>
                  </form>
                ) : (
                  <div key={s.id} className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-semibold">{s.name} {s.is_night && <Badge tone="blue">Night</Badge>}</div>
                        <div className="text-[11px] text-slate-500">{clock(s.start_time)}–{clock(s.end_time)} · min {s.min_staff} staff</div>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-slate-500 tabular-nums mr-1">{s.standard_hours}h</span>
                        {canEdit && (
                          <>
                            <button onClick={() => { setEditShiftId(s.id); setNewShiftOpen(false); }} className="text-xs text-indigo-600 hover:underline">Edit</button>
                            <button onClick={() => deactivateShift(s.id, s.name)} className="text-xs text-rose-600 hover:underline">Deactivate</button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </Card>

        <Card title="Daily coverage" className="lg:col-span-2">
          {roster.loading ? (
            <Loading />
          ) : (roster.data?.days?.length ?? 0) === 0 ? (
            <EmptyState title="No roster data in range" />
          ) : (
            <ScrollTable>
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b">
                    <th className="py-2">Date</th>
                    <th>Shift coverage</th>
                    <th className="text-right">OT</th>
                    <th className="text-right">Night</th>
                    <th>Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {(roster.data?.days ?? []).map((d) => (
                    <tr key={d.date} className="border-b border-slate-100 align-top">
                      <td className="py-2 whitespace-nowrap">
                        {fmtDate(d.date)}
                        {d.is_holiday && <span className="ml-1"><Badge tone="blue">Holiday</Badge></span>}
                      </td>
                      <td className="py-2">
                        {d.shift_list.map((s) => (
                          <div key={s.shift_id} className="flex items-center gap-1.5">
                            <span className="text-xs">{s.shift_name}</span>
                            <Badge tone={s.understaffed ? "red" : "green"}>{s.assigned}/{s.min_staff}</Badge>
                          </div>
                        ))}
                      </td>
                      <td className="py-2 text-right tabular-nums">{d.overtime_hours || "—"}</td>
                      <td className="py-2 text-right tabular-nums">{d.night_hours || "—"}</td>
                      <td className="py-2">
                        {d.understaffed_any && <Badge tone="red">Understaffed</Badge>}
                        {d.cost_flags.night_differential_applies && <span className="ml-1"><Badge tone="blue">Night</Badge></span>}
                        {d.cost_flags.overtime_applies && <span className="ml-1"><Badge tone="amber">OT</Badge></span>}
                        {d.cost_flags.holiday_pay_applies && <span className="ml-1"><Badge tone="blue">Holiday pay</Badge></span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollTable>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <Card title={`Assignments (${assignments.data?.length ?? 0})`}>
          {assignments.loading ? (
            <Loading />
          ) : (assignments.data?.length ?? 0) === 0 ? (
            <EmptyState title="No assignments in range" />
          ) : (
            <div className="space-y-2">
              {(assignments.data ?? []).map((a) =>
                editAssignId === a.id ? (
                  <form key={a.id} onSubmit={saveAssignment} className="rounded-xl border border-slate-200 bg-slate-50 p-3 grid grid-cols-2 gap-2">
                    <select name="employee_id" defaultValue={a.employee_id} required className="rounded border border-slate-300 px-2 py-1 text-sm col-span-2">
                      {(employees.data ?? []).map((e) => (
                        <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                      ))}
                    </select>
                    <select name="shift_id" defaultValue={a.shift_id} required className="rounded border border-slate-300 px-2 py-1 text-sm col-span-2">
                      {(shifts.data ?? []).map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                    <input name="work_date" type="date" defaultValue={a.work_date} required className="rounded border border-slate-300 px-2 py-1 text-sm" />
                    <button disabled={busy} className="rounded-md bg-emerald-600 px-3 py-1 text-xs text-white disabled:opacity-50">Save</button>
                    <button type="button" onClick={() => setEditAssignId(null)} className="rounded-md bg-slate-200 px-3 py-1 text-xs">Cancel</button>
                  </form>
                ) : (
                  <div key={a.id} className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold">{a.employee_name}</span>
                      <span className="text-[11px] text-slate-400">{a.employee_number}</span>
                      <Badge tone={a.status === "Assigned" ? "green" : "slate"}>{a.status}</Badge>
                      <span className="text-xs text-slate-500 ml-auto">{fmtDate(a.work_date)} · {a.shift_name}</span>
                    </div>
                    {canEdit && (
                      <div className="mt-1.5 flex flex-wrap items-center gap-2">
                        <button onClick={() => setEditAssignId(a.id)} className="text-xs text-indigo-600 hover:underline">Reassign</button>
                        <button onClick={() => unassign(a.id, a.employee_name)} className="text-xs text-rose-600 hover:underline">Unassign</button>
                        <select value={swapFor[a.id] ?? ""} onChange={(e) => setSwapFor((s) => ({ ...s, [a.id]: e.target.value }))} className="ml-auto rounded border border-slate-300 px-1.5 py-0.5 text-xs">
                          <option value="">Swap with…</option>
                          {(employees.data ?? [])
                            .filter((e) => e.id !== a.employee_id && e.employment_status === "Active")
                            .map((e) => (
                              <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                            ))}
                        </select>
                        <button onClick={() => doSwap(a, Number(swapFor[a.id]))} disabled={!swapFor[a.id]} className="rounded-md bg-indigo-600 px-2 py-0.5 text-xs text-white disabled:opacity-40">Swap</button>
                      </div>
                    )}
                  </div>
                )
              )}
            </div>
          )}
        </Card>

        <Card title="Coverage conflicts">
          {conflicts.loading ? (
            <Loading />
          ) : (conflicts.data?.length ?? 0) === 0 ? (
            <EmptyState title="No conflicts in range" hint="Every active shift meets its minimum staff." />
          ) : (
            <div className="space-y-2">
              {(conflicts.data ?? []).slice(0, 40).map((c) => (
                <div key={`${c.date}-${c.shift_id}`} className="rounded-xl bg-white/60 border border-slate-200 px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold">{fmtDate(c.date)}</span>
                    <span className="text-xs text-slate-500">{c.shift_name}</span>
                    <Badge tone="red">short {c.shortage}</Badge>
                    <span className="text-[11px] text-slate-400 ml-auto">{c.assigned}/{c.min_staff} staffed</span>
                  </div>
                  {canEdit && c.eligible_employees.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      {(c.eligible_employees).slice(0, 4).map((emp) => (
                        <button
                          key={emp.id}
                          onClick={() => fillConflict(c, emp.id)}
                          className="rounded-md bg-brand-600 px-2 py-0.5 text-xs text-white hover:bg-brand-700"
                        >
                          Assign {emp.full_name}
                        </button>
                      ))}
                      {c.eligible_employees.length > 4 && (
                        <span className="text-[11px] text-slate-400">+{c.eligible_employees.length - 4} more</span>
                      )}
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

/* ------------------------------------------------------------------ */
/* Statutory tab                                                       */
/* ------------------------------------------------------------------ */

function StatutoryTab({ props }: { props: RoleProps }) {
  const sources = useApi<StatutorySource[]>("/hr/statutory-config/sources");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editKey, setEditKey] = useState<string>("overtime");
  const [valueText, setValueText] = useState("");
  const [source, setSource] = useState("Administrative update");
  const [effectiveDate, setEffectiveDate] = useState("");

  function pickKey(key: string) {
    setEditKey(key);
    const row = (sources.data ?? []).find((s) => s.config_key === key);
    setValueText(JSON.stringify(row?.value ?? {}, null, 2));
  }

  async function saveConfig(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const parsed = JSON.parse(valueText);
      await api(`/hr/statutory-config/${editKey}`, {
        method: "PUT",
        body: JSON.stringify({ value: parsed, source, effective_date: effectiveDate || null }),
      });
      setMessage("Statutory config updated (a new version is now effective).");
      sources.refresh();
    } catch (err) {
      setError(err instanceof SyntaxError ? `Invalid JSON: ${err.message}` : (err as Error).message);
    }
  }

  return (
    <div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 mb-4">{message}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Statutory rates (effective)">
          {sources.loading ? (
            <Loading />
          ) : (sources.data?.length ?? 0) === 0 ? (
            <EmptyState title="No config seeded yet" />
          ) : (
            <div className="space-y-3">
              {(sources.data ?? []).map((s) => (
                <div key={s.config_key} className="rounded-xl bg-white/60 border border-slate-200 p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-bold text-slate-700">{s.display_name}</span>
                      <span className="ml-2 font-mono text-[11px] text-slate-400">{s.config_key}</span>
                    </div>
                    {props.isAdmin && (
                      <button onClick={() => pickKey(s.config_key)} className="rounded-md bg-slate-100 px-2 py-1 text-xs hover:bg-slate-200">
                        Edit
                      </button>
                    )}
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">Source: {s.source} · effective {fmtDate(s.effective_date)}</div>
                  <pre className="mt-2 max-h-36 overflow-auto rounded-lg bg-slate-50 border border-slate-100 p-2 text-[11px] text-slate-600">
                    {JSON.stringify(s.value, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </Card>

        {props.isAdmin && (
          <Card title="Update a statutory rate (new version)">
            <form onSubmit={saveConfig} className="grid grid-cols-2 gap-3">
              <label className="text-xs text-slate-500">
                Config key
                <select value={editKey} onChange={(e) => pickKey(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                  {(sources.data ?? []).map((s) => (
                    <option key={s.config_key} value={s.config_key}>{s.display_name}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-slate-500">
                Effective date
                <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </label>
              <label className="text-xs text-slate-500 col-span-2">
                Source reference
                <input value={source} onChange={(e) => setSource(e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
              </label>
              <label className="text-xs text-slate-500 col-span-2">
                Value (JSON)
                <textarea value={valueText} onChange={(e) => setValueText(e.target.value)} rows={12} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 font-mono text-xs" />
              </label>
              <div className="col-span-2">
                <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">Save new version</button>
              </div>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}

/* ==== HR ==== */

export default function HR() {
  const { user } = useAuth();
  const role = user?.role.name ?? "";
  const isHr = role === R.ADMIN || role === R.HR;
  const isAdmin = role === R.ADMIN;
  const isStaff = role === R.STAFF;
  const isApprover = role === R.APPROVER;
  const isExec = role === R.EXEC;
  const isFinance = role === R.FINANCE;

  const props: RoleProps = { isHr, isAdmin, isStaff, isApprover, isExec, isFinance };

  const tabs: Array<{ id: string; label: string; show: boolean }> = [
    { id: "overview", label: "Overview", show: true },
    { id: "leave", label: "Leave", show: isHr || isApprover || isStaff },
    { id: "attendance", label: "Attendance", show: isHr || isApprover || isStaff || isExec || isFinance },
    { id: "payroll", label: "Payroll", show: isHr || isStaff || isExec || isFinance },
    { id: "cases", label: "HR Cases", show: isHr || isApprover || isStaff || isExec },
    { id: "roster", label: "Roster", show: isHr || isApprover || isExec },
    { id: "statutory", label: "Statutory", show: isHr },
  ];
  const visible = tabs.filter((t) => t.show);
  const [tab, setTab] = useState(visible[0]?.id ?? "overview");
  const active = visible.some((t) => t.id === tab) ? tab : visible[0]?.id ?? "overview";

  const employees = useApi<Employee[]>("/hr/employees");
  const departments = useApi<Department[]>("/hr/departments");
  const training = useApi<Training[]>("/hr/training");

  return (
    <div>
      <PageHeader
        title="Human Resources"
        subtitle="Employees, leave, time & attendance, payroll, HR cases, shift roster and statutory configuration."
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {visible.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
              active === t.id ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-900/30" : "bg-white/60 border border-slate-200 text-slate-600 hover:border-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {active === "overview" && <OverviewTab employees={employees.data ?? []} departments={departments.data ?? []} training={training.data ?? []} props={props} />}
      {active === "leave" && <LeaveTab props={props} />}
      {active === "attendance" && <AttendanceTab props={props} />}
      {active === "payroll" && <PayrollTab props={props} />}
      {active === "cases" && <CasesTab props={props} />}
      {active === "roster" && <RosterTab props={props} />}
      {active === "statutory" && <StatutoryTab props={props} />}
    </div>
  );
}




