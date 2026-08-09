import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { NAV } from "./components/ui";

export default function Layout() {
  const { user, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  if (!user) return <Navigate to="/login" replace />;

  const items = NAV.filter((n) => n.roles.includes(user.role.name));

  const nav = (
    <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) =>
            `block rounded-md px-3 py-2 text-sm ${
              isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-800"
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  const brand = (
    <div className="px-5 py-5 border-b border-slate-800 shrink-0">
      <div className="text-lg font-bold text-white">Airport360</div>
      <div className="text-xs text-slate-400 mt-0.5">
        Site {user.site_id} · {user.role.name}
      </div>
    </div>
  );

  const footer = (
    <div className="px-5 py-4 border-t border-slate-800 shrink-0">
      <div className="text-sm text-slate-300">{user.full_name}</div>
      <div className="text-xs text-slate-500 break-all">{user.email}</div>
      <button onClick={logout} className="mt-3 text-xs text-slate-400 hover:text-white underline">
        Sign out
      </button>
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Desktop sidebar (md+) */}
      <aside className="hidden md:flex w-60 bg-slate-900 text-slate-200 flex-col shrink-0 sticky top-0 h-screen">
        {brand}
        {nav}
        {footer}
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="md:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/50" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-slate-900 text-slate-200 flex flex-col shadow-xl">
            <button
              onClick={() => setDrawerOpen(false)}
              aria-label="Close menu"
              className="absolute right-3 top-3 text-slate-400 hover:text-white text-xl"
            >
              ×
            </button>
            {brand}
            {nav}
            {footer}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="md:hidden sticky top-0 z-30 bg-slate-900 text-white flex items-center justify-between px-4 py-3 shadow">
          <button
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            className="text-slate-300 hover:text-white"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
            </svg>
          </button>
          <div className="font-bold">Airport360</div>
          <div className="text-xs text-slate-400">{user.role.name}</div>
        </header>

        <main className="flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
