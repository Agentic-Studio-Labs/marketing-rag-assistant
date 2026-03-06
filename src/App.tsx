import { HashRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom'

function App() {
  return (
    <HashRouter>
      <div className="flex h-screen">
        <nav className="w-56 border-r border-border bg-muted/30 p-4 pt-12 flex flex-col gap-1">
          <SidebarLink to="/dashboard">Dashboard</SidebarLink>
          <SidebarLink to="/library">Library</SidebarLink>
          <SidebarLink to="/generated">Generated</SidebarLink>
          <SidebarLink to="/settings">Settings</SidebarLink>
        </nav>
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/dashboard" element={<Placeholder name="Dashboard" />} />
            <Route path="/library" element={<Placeholder name="Library" />} />
            <Route path="/generated" element={<Placeholder name="Generated" />} />
            <Route path="/settings" element={<Placeholder name="Settings" />} />
            <Route path="/content/:id" element={<Placeholder name="Content Detail" />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  )
}

function SidebarLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-accent text-accent-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

function Placeholder({ name }: { name: string }) {
  return (
    <div className="flex items-center justify-center h-full text-muted-foreground">
      <p className="text-lg">{name} -- coming soon</p>
    </div>
  )
}

export default App
