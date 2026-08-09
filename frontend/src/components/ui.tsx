import { ReactNode } from "react";

export type NavItem = { to: string; label: string; roles: string[] };

export const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", roles: ["Administrator", "Executive", "Finance Officer", "HR Officer", "Department Head"] },
  { to: "/hr", label: "Human Resources", roles: ["Administrator", "Executive", "HR Officer", "Department Head"] },
  { to: "/procurement", label: "Procurement", roles: ["Administrator", "Executive", "Finance Officer", "HR Officer", "Department Head", "Staff"] },
  { to: "/finance", label: "Finance", roles: ["Administrator", "Executive", "Finance Officer"] },
  { to: "/capacity", label: "Capacity Building", roles: ["Administrator", "Executive", "HR Officer"] },
  { to: "/admin", label: "Administration", roles: ["Administrator"] },
];

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-lg border border-slate-200 shadow-sm p-5 ${className}`}>
      {title && <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">{title}</h3>}
      {children}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "red" | "blue" }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-800",
    amber: "bg-amber-100 text-amber-800",
    red: "bg-red-100 text-red-800",
    blue: "bg-blue-100 text-blue-800",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function statusTone(status: string): "slate" | "green" | "amber" | "red" | "blue" {
  const s = status.toLowerCase();
  if (["approved", "received", "completed", "active"].includes(s)) return "green";
  if (["submitted", "issued", "in progress", "ordered", "planned"].includes(s)) return "amber";
  if (["rejected", "cancelled"].includes(s)) return "red";
  return "slate";
}

export function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4">{message}</div>
  );
}

export function Loading() {
  return <div className="text-sm text-slate-400 py-8 text-center">Loading…</div>;
}
