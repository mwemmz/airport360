import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import CommandCenter from "./pages/CommandCenter";
import Flights from "./pages/Flights";
import Queues from "./pages/Queues";
import Baggage from "./pages/Baggage";
import Incidents from "./pages/Incidents";
import Maintenance from "./pages/Maintenance";
import Cargo from "./pages/Cargo";
import Alerts from "./pages/Alerts";
import AIAssistant from "./pages/AIAssistant";
import Complaints from "./pages/Complaints";
import Bookings from "./pages/Bookings";
import PassengerPortal from "./pages/PassengerPortal";
import HR from "./pages/HR";
import Procurement from "./pages/Procurement";
import Finance from "./pages/Finance";
import CapacityBuilding from "./pages/CapacityBuilding";
import Admin from "./pages/Admin";

const OPS = ["Administrator", "Executive", "Operations Manager"];

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
              path="/ops"
              element={
                <RequireRole roles={OPS}>
                  <CommandCenter />
                </RequireRole>
              }
            />
            <Route
              path="/flights"
              element={
                <RequireRole roles={[...OPS, "Staff"]}>
                  <Flights />
                </RequireRole>
              }
            />
            <Route
              path="/queues"
              element={
                <RequireRole roles={OPS}>
                  <Queues />
                </RequireRole>
              }
            />
            <Route
              path="/baggage"
              element={
                <RequireRole roles={OPS}>
                  <Baggage />
                </RequireRole>
              }
            />
            <Route
              path="/incidents"
              element={
                <RequireRole roles={OPS}>
                  <Incidents />
                </RequireRole>
              }
            />
            <Route
              path="/maintenance"
              element={
                <RequireRole roles={[...OPS, "Staff"]}>
                  <Maintenance />
                </RequireRole>
              }
            />
            <Route
              path="/cargo"
              element={
                <RequireRole roles={[...OPS, "Staff"]}>
                  <Cargo />
                </RequireRole>
              }
            />
            <Route
              path="/alerts"
              element={
                <RequireRole roles={OPS}>
                  <Alerts />
                </RequireRole>
              }
            />
            <Route
              path="/assistant"
              element={
                <RequireRole roles={OPS}>
                  <AIAssistant />
                </RequireRole>
              }
            />
            <Route
              path="/complaints"
              element={
                <RequireRole roles={OPS}>
                  <Complaints />
                </RequireRole>
              }
            />
            <Route
              path="/bookings"
              element={
                <RequireRole roles={[...OPS, "Passenger"]}>
                  <Bookings />
                </RequireRole>
              }
            />
            <Route
              path="/passenger"
              element={
                <RequireRole roles={["Passenger"]}>
                  <PassengerPortal />
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
