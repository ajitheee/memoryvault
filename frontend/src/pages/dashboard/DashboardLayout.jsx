import { NavLink, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, Database, Inbox, PlusCircle, Package,
  Plug, LogOut, User as UserIcon,
} from "lucide-react";

const NAV = [
  { to: "/app", end: true, label: "Overview", icon: LayoutDashboard, testid: "nav-overview" },
  { to: "/app/facts", label: "Fact Browser", icon: Database, testid: "nav-facts" },
  { to: "/app/pending", label: "Pending Queue", icon: Inbox, testid: "nav-pending" },
  { to: "/app/ingest", label: "Ingest", icon: PlusCircle, testid: "nav-ingest" },
  { to: "/app/context", label: "Context Pack", icon: Package, testid: "nav-context" },
  { to: "/app/connect", label: "MCP Connect", icon: Plug, testid: "nav-connect" },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const doLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#F5F5F5] flex">
      {/* Sidebar */}
      <aside className="w-60 border-r border-[#262626] flex flex-col fixed h-screen bg-[#0A0A0A]">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-[#262626]">
          <div className="w-5 h-5 border border-white flex items-center justify-center">
            <div className="w-2 h-2 bg-white" />
          </div>
          <span className="font-heading font-extrabold tracking-tight">MEMORYVAULT</span>
        </div>

        <nav className="flex-1 py-4">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              data-testid={item.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm border-l-2 transition-colors ${
                  isActive
                    ? "border-white bg-[#141414] text-white"
                    : "border-transparent text-neutral-400 hover:text-white hover:bg-[#111]"
                }`
              }
            >
              <item.icon className="w-4 h-4" strokeWidth={1.5} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-[#262626] p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 border border-[#262626] flex items-center justify-center">
              <UserIcon className="w-4 h-4 text-neutral-400" />
            </div>
            <div className="min-w-0">
              <p className="text-sm truncate">{user?.name}</p>
              <p className="font-mono text-[10px] text-neutral-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            data-testid="logout-btn"
            onClick={doLogout}
            className="w-full flex items-center gap-2 justify-center border border-[#262626] py-2 text-sm text-neutral-400 hover:text-white hover:border-white/50 transition-colors"
          >
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 ml-60 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
