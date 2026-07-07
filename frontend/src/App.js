import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import DashboardLayout from "@/pages/dashboard/DashboardLayout";
import Overview from "@/pages/dashboard/Overview";
import Facts from "@/pages/dashboard/Facts";
import Pending from "@/pages/dashboard/Pending";
import Ingest from "@/pages/dashboard/Ingest";
import ContextPack from "@/pages/dashboard/ContextPack";
import Connect from "@/pages/dashboard/Connect";

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <div className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-600 animate-pulse">Loading vault…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function GuestOnly({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return null;
  if (user) return <Navigate to="/app" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<GuestOnly><Auth mode="login" /></GuestOnly>} />
            <Route path="/signup" element={<GuestOnly><Auth mode="signup" /></GuestOnly>} />
            <Route path="/app" element={<Protected><DashboardLayout /></Protected>}>
              <Route index element={<Overview />} />
              <Route path="facts" element={<Facts />} />
              <Route path="pending" element={<Pending />} />
              <Route path="ingest" element={<Ingest />} />
              <Route path="context" element={<ContextPack />} />
              <Route path="connect" element={<Connect />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Toaster theme="dark" position="bottom-right" toastOptions={{ style: { background: "#141414", border: "1px solid #262626", color: "#F5F5F5", borderRadius: 0 } }} />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
