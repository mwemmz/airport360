import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import HR from "./pages/HR";
import Procurement from "./pages/Procurement";
import Finance from "./pages/Finance";
import CapacityBuilding from "./pages/CapacityBuilding";
import Admin from "./pages/Admin";

function RequireRole({ roles, children }: { roles: string[]; children: JSX.Element }) {
  const { user } = useAuth();
  if (!user) return null;
  if (!roles.includes(user.role.name)) {
    return <div className="text-center py-20 text-slate-500">You do not have access to this module.</div>;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Layout />}>
            <Route
              path="/"
              element={
                <RequireRole roles={["Administrator", "Executive", "Finance Officer", "HR Officer", "Department Head"]}>
                  <Dashboard />
                </RequireRole>
              }
            />
            <Route
              path="/hr"
              element={
                <RequireRole roles={["Administrator", "Executive", "HR Officer", "Department Head"]}>
                  <HR />
                </RequireRole>
              }
            />
            <Route
              path="/procurement"
              element={
                <RequireRole roles={["Administrator", "Executive", "Finance Officer", "HR Officer", "Department Head", "Staff"]}>
                  <Procurement />
                </RequireRole>
              }
            />
            <Route
              path="/finance"
              element={
                <RequireRole roles={["Administrator", "Executive", "Finance Officer"]}>
                  <Finance />
                </RequireRole>
              }
            />
            <Route
              path="/capacity"
              element={
                <RequireRole roles={["Administrator", "Executive", "HR Officer"]}>
                  <CapacityBuilding />
                </RequireRole>
              }
            />
            <Route
              path="/admin"
              element={
                <RequireRole roles={["Administrator"]}>
                  <Admin />
                </RequireRole>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
