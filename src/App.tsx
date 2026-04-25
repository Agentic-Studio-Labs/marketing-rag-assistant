import { useEffect, useRef, useState } from "react";
import { HashRouter, Routes, Route, Navigate, NavLink } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthProvider";
import { api } from "./api/client";
import Dashboard from "./views/Dashboard";
import Library from "./views/Library";
import Generated from "./views/Generated";
import ContentDetail from "./views/ContentDetail";
import Settings from "./views/Settings";
import Login from "./views/Login";

const SIDEBAR_WIDTH_KEY = "cih.sidebarWidth";
const SIDEBAR_MIN = 180;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 256;

function readStoredSidebarWidth(): number {
  if (typeof window === "undefined") return SIDEBAR_DEFAULT;
  const raw = window.localStorage.getItem(SIDEBAR_WIDTH_KEY);
  const parsed = raw ? parseInt(raw, 10) : NaN;
  if (!Number.isFinite(parsed)) return SIDEBAR_DEFAULT;
  return Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, parsed));
}

function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <AuthenticatedShell />
      </HashRouter>
    </AuthProvider>
  );
}

function AuthenticatedShell() {
  const { authRequired, loading, user, logout } = useAuth();
  const backend = api.backendInfo();
  const [sidebarWidth, setSidebarWidth] = useState<number>(
    readStoredSidebarWidth,
  );
  const draggingRef = useRef(false);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!draggingRef.current) return;
      const next = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, e.clientX));
      setSidebarWidth(next);
    }
    function onUp() {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth));
  }, [sidebarWidth]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-sm text-muted-foreground">
        Loading session...
      </div>
    );
  }

  if (authRequired && !user) {
    return <Login />;
  }

  return (
    <div className="flex h-screen">
      <nav
        style={{ width: sidebarWidth }}
        className="shrink-0 bg-muted/30 p-4 pt-10 flex flex-col gap-1"
      >
        <div className="mb-6 px-3">
          <p className="text-sm font-semibold">Content Intelligence Hub</p>
          <p className="text-xs text-muted-foreground mt-1">
            {backend.mode === "cloud"
              ? "Cloud control plane"
              : "Local sidecar mode"}
          </p>
          {user && (
            <>
              <p className="text-xs text-muted-foreground mt-3">Signed in as</p>
              <p className="text-sm font-medium truncate">{user.email}</p>
              <button
                onClick={() => void logout()}
                className="mt-3 text-xs text-primary hover:underline"
              >
                Sign out
              </button>
            </>
          )}
        </div>
        <SidebarLink to="/library">Library</SidebarLink>
        <SidebarLink to="/generated">Generated</SidebarLink>
        <SidebarLink to="/dashboard">Search</SidebarLink>
        <SidebarLink to="/settings">Settings</SidebarLink>
      </nav>
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize sidebar"
        title="Drag to resize · double-click to reset"
        onMouseDown={(e) => {
          e.preventDefault();
          draggingRef.current = true;
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
        }}
        onDoubleClick={() => setSidebarWidth(SIDEBAR_DEFAULT)}
        style={{ backgroundColor: "rgba(120,120,128,0.35)" }}
        className="group relative w-1.5 shrink-0 cursor-col-resize hover:!bg-blue-500/70 active:!bg-blue-500 transition-colors"
      >
        {/* widened invisible hit area so the divider is easy to grab */}
        <span aria-hidden className="absolute inset-y-0 -left-2 -right-2" />
      </div>
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/library" element={<Library />} />
          <Route path="/generated" element={<Generated />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/content/:id" element={<ContentDetail />} />
          <Route path="*" element={<Navigate to="/library" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function SidebarLink({
  to,
  children,
}: {
  to: string;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default App;
