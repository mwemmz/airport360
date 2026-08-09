import { Navigate, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./auth";
import { NAV } from "./components/ui";

export default function Layout() {
  const { user, logout } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  const items = NAV.filter((n) => n.roles.includes(user.role.name));

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-slate-900 text-slate-200 flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="text-lg font-bold text-white">Airport360</div>
          <div className="text-xs text-slate-400 mt-0.5">
            Site {user.site_id} · {user.role.name}
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
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
        <div className="px-5 py-4 border-t border-slate-800">
          <div className="text-sm text-slate-300">{user.full_name}</div>
          <div className="text-xs text-slate-500">{user.email}</div>
          <button
            onClick={logout}
            className="mt-3 text-xs text-slate-400 hover:text-white underline"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
