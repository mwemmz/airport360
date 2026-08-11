import { ReactNode } from "react";
import {
  AlertTriangle,
  Banknote,
  Bell,
  BookOpen,
  Briefcase,
  Building2,
  Cctv,
  ClipboardList,
  Cloud,
  HeartHandshake,
  LayoutDashboard,
  Luggage,
  MessageSquareWarning,
  Package,
  Plane,
  Radar,
  ShoppingCart,
  Sparkles,
  UserRound,
  Users,
  Wrench,
} from "lucide-react";

const OPS = ["Administrator", "Executive", "Operations Manager"];

export type NavItem = { to: string; label: string; roles: string[] };

export const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", roles: ["Administrator", "Executive", "Finance Officer", "HR Officer", "Department Head"] },
  { to: "/ops", label: "Command Center", roles: OPS },
  { to: "/flights", label: "Flights", roles: [...OPS, "Staff"] },
  { to: "/queues", label: "Queues & Predictions", roles: OPS },
  { to: "/vision", label: "Computer Vision", roles: OPS },
  { to: "/baggage", label: "Baggage", roles: OPS },
  { to: "/incidents", label: "Incidents", roles: OPS },
  { to: "/maintenance", label: "Maintenance", roles: [...OPS, "Staff"] },
  { to: "/cargo", label: "Cargo", roles: [...OPS, "Staff"] },
  { to: "/alerts", label: "Alerts", roles: OPS },
  { to: "/assistant", label: "AI Assistant", roles: OPS },
  { to: "/complaints", label: "Complaints", roles: OPS },
  { to: "/bookings", label: "Booking Marketplace", roles: [...OPS, "Passenger"] },
  { to: "/passenger", label: "Passenger Portal", roles: ["Passenger"] },
  { to: "/hr", label: "Human Resources", roles: ["Administrator", "Executive", "HR Officer", "Department Head", "Staff"] },
  { to: "/procurement", label: "Procurement", roles: ["Administrator", "Executive", "Finance Officer", "HR Officer", "Department Head", "Staff"] },
  { to: "/finance", label: "Finance", roles: ["Administrator", "Executive", "Finance Officer"] },
  { to: "/capacity", label: "Capacity Building", roles: ["Administrator", "Executive", "HR Officer"] },
  { to: "/admin", label: "Administration", roles: ["Administrator"] },
];

export function navIcon(to: string) {
  switch (to) {
    case "/": return LayoutDashboard;
    case "/ops": return Radar;
    case "/flights": return Plane;
    case "/queues": return ClipboardList;
    case "/vision": return Cctv;
    case "/baggage": return Luggage;
    case "/incidents": return AlertTriangle;
    case "/maintenance": return Wrench;
    case "/cargo": return Package;
    case "/alerts": return Bell;
    case "/assistant": return Sparkles;
    case "/complaints": return MessageSquareWarning;
    case "/bookings": return HeartHandshake;
    case "/passenger": return UserRound;
    case "/hr": return Users;
    case "/procurement": return ShoppingCart;
    case "/finance": return Banknote;
    case "/capacity": return BookOpen;
    case "/admin": return Briefcase;
    default: return Building2;
  }
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 animate-fade-in">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1.5 max-w-3xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

export function Card({ title, children, className = "", actions }: { title?: string; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <div className={`glass-card card-glow p-5 md:p-6 ${className}`}>
      {(title || actions) && (
        <div className="flex items-center justify-between mb-4">
          {title && (
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-blue-500" />
              <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">{title}</h3>
            </div>
          )}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export type StatTone = "indigo" | "emerald" | "amber" | "rose" | "cyan";

const STAT_STYLES: Record<StatTone, { chip: string; ring: string }> = {
  indigo: { chip: "bg-indigo-50 text-indigo-600", ring: "from-indigo-500 to-blue-500" },
  emerald: { chip: "bg-emerald-50 text-emerald-600", ring: "from-emerald-500 to-teal-500" },
  amber: { chip: "bg-amber-50 text-amber-600", ring: "from-amber-500 to-orange-500" },
  rose: { chip: "bg-rose-50 text-rose-600", ring: "from-rose-500 to-pink-500" },
  cyan: { chip: "bg-cyan-50 text-cyan-600", ring: "from-cyan-500 to-sky-500" },
};

export function Stat({
  label,
  value,
  hint,
  icon,
  tone = "indigo",
  className = "",
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
  tone?: StatTone;
  className?: string;
}) {
  const s = STAT_STYLES[tone];
  return (
    <div className={`glass-card card-glow p-4 md:p-5 group ${className ?? ""}`}>
      <div className={`absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r ${s.ring} opacity-70 rounded-t-2xl`} />
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{label}</div>
          <div className="mt-1.5 text-xl md:text-2xl font-extrabold text-slate-900 tabular-nums">{value}</div>
          {hint && <div className="mt-1 text-[11px] text-slate-400 truncate">{hint}</div>}
        </div>
        {icon && (
          <div className={`shrink-0 w-9 h-9 rounded-xl ${s.chip} flex items-center justify-center transition-transform duration-300 group-hover:scale-110`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

export function Badge({
  children,
  tone = "slate",
  dot = false,
}: {
  children: ReactNode;
  tone?: "slate" | "green" | "amber" | "red" | "blue";
  dot?: boolean;
}) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600 ring-slate-200",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    amber: "bg-amber-50 text-amber-700 ring-amber-200",
    red: "bg-rose-50 text-rose-700 ring-rose-200",
    blue: "bg-blue-50 text-blue-700 ring-blue-200",
  };
  const dots: Record<string, string> = {
    slate: "bg-slate-400",
    green: "bg-emerald-500",
    amber: "bg-amber-500",
    red: "bg-rose-500",
    blue: "bg-blue-500",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${tones[tone]}`}>
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dots[tone]}`} />}
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
    <div className="animate-fade-in rounded-xl bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-700 mb-4 flex items-start gap-2.5">
      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function Spinner({ size = "md", label }: { size?: "sm" | "md" | "lg"; label?: string }) {
  const dims = { sm: "w-4 h-4", md: "w-6 h-6", lg: "w-10 h-10" }[size];
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className={`${dims} rounded-full border-[3px] border-indigo-100 border-t-indigo-500 animate-spin`} />
      {label && <div className="text-sm text-slate-500 animate-pulse">{label}</div>}
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <Spinner size="md" label={label} />;
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`glass-card p-5 ${className}`}>
      <div className="skeleton h-3 w-24 mb-4" />
      <div className="skeleton h-8 w-full mb-2" />
      <div className="skeleton h-3 w-3/4" />
    </div>
  );
}

export function EmptyState({ title = "Nothing here yet", hint }: { title?: string; hint?: string }) {
  return (
    <div className="text-center py-10">
      <Cloud className="w-10 h-10 text-slate-300 mx-auto mb-3" />
      <div className="text-sm font-semibold text-slate-500">{title}</div>
      {hint && <div className="text-xs text-slate-400 mt-1">{hint}</div>}
    </div>
  );
}

/** Mobile-first table wrapper: horizontal scroll on small screens, never breaks layout. */
export function ScrollTable({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 ${className}`}>{children}</div>;
}
