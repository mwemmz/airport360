import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { NAV, navIcon } from "./components/ui";
import { LogOut, Plane, Menu, X } from "lucide-react";

export default function Layout() {
  const { user, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showBar, setShowBar] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setDrawerOpen(false);
    setShowBar(true);
    const t = setTimeout(() => setShowBar(false), 500);
    return () => clearTimeout(t);
  }, [location.pathname]);

  if (!user) return <Navigate to="/login" replace />;

  const items = NAV.filter((n) => n.roles.includes(user.role.name));

  const nav = (
    <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
      {items.map((item) => {
        const Icon = navIcon(item.to);
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-900/40"
                  : "text-slate-400 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Icon className={`w-5 h-5 shrink-0 transition-transform duration-200 group-hover:scale-110`} />
            <span>{item.label}</span>
            {item.to === location.pathname && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white/80" />}
          </NavLink>
        );
      })}
    </nav>
  );

  const brand = (
    <div className="px-5 py-6 shrink-0 relative overflow-hidden">
      <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full bg-indigo-500/20 blur-2xl" />
      <div className="relative flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-900/40">
          <Plane className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-lg font-extrabold tracking-tight text-white leading-none">Airport360</div>
          <div className="text-[11px] text-slate-400 mt-1">ZACL Digital Platform</div>
        </div>
      </div>
      <div className="relative mt-4 inline-flex items-center gap-1.5 rounded-full bg-white/5 border border-white/10 px-2.5 py-1 text-[11px] text-slate-300">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
        Site {user.site_id} · {user.role.name}
      </div>
    </div>
  );

  const footer = (
    <div className="px-4 py-4 border-t border-white/10 shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center text-sm font-bold text-white shrink-0">
          {user.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-200 truncate">{user.full_name}</div>
          <div className="text-[11px] text-slate-500 truncate">{user.email}</div>
        </div>
      </div>
      <button
        onClick={logout}
        className="mt-3 w-full flex items-center justify-center gap-2 rounded-xl bg-white/5 border border-white/10 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition-colors py-2"
      >
        <LogOut className="w-3.5 h-3.5" /> Sign out
      </button>
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {showBar && <div className="progress-bar animate-fade-in" />}

      {/* Desktop sidebar (md+) */}
      <aside className="hidden md:flex w-64 bg-slate-950 text-slate-200 flex-col shrink-0 sticky top-0 h-screen">
        <div className="absolute inset-0 bg-grid pointer-events-none" />
        {brand}
        {nav}
        {footer}
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="md:hidden fixed inset-0 z-40 animate-fade-in">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-slate-950 text-slate-200 flex flex-col shadow-2xl animate-fade-in-up">
            <button
              onClick={() => setDrawerOpen(false)}
              aria-label="Close menu"
              className="absolute right-3 top-3 z-10 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            {brand}
            {nav}
            {footer}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="md:hidden sticky top-0 z-30 bg-slate-950/90 backdrop-blur-lg text-white flex items-center justify-between px-4 py-3 shadow-lg border-b border-white/10">
          <button
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            className="text-slate-300 hover:text-white p-1.5 -ml-1.5"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2 font-extrabold tracking-tight">
            <Plane className="w-4 h-4 text-indigo-400" /> Airport360
          </div>
          <div className="text-[11px] text-slate-400 font-medium">{user.role.name}</div>
        </header>

        <main className="flex-1 p-4 md:p-8 max-w-[1400px] w-full mx-auto relative">
          {/* Decorative background blobs */}
          <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
            <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-indigo-400/25 blur-3xl animate-blob" />
            <div className="absolute top-1/3 -right-32 w-[28rem] h-[28rem] rounded-full bg-cyan-400/20 blur-3xl animate-blob" style={{ animationDelay: "2.5s" }} />
            <div className="absolute bottom-0 left-1/3 w-80 h-80 rounded-full bg-emerald-400/15 blur-3xl animate-blob" style={{ animationDelay: "5s" }} />
          </div>
          <div key={location.pathname} className="relative z-10 animate-fade-in-up">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
