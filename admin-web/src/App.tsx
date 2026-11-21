import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AdminShell from './layouts/AdminShell'
import AllowlistPage from './pages/AllowlistPage'
import AuditPage from './pages/AuditPage'
import CallRulesPage from './pages/CallRulesPage'
import DashboardPage from './pages/DashboardPage'
import DeviceDetailPage from './pages/DeviceDetailPage'
import DevicesPage from './pages/DevicesPage'
import DnsDenylistPage from './pages/DnsDenylistPage'
import DnsLogsPage from './pages/DnsLogsPage'
import IncidentPage from './pages/IncidentPage'
import LoginPage from './pages/LoginPage'
import RestrictionsPage from './pages/RestrictionsPage'

export default function App() {
  return (
    <BrowserRouter basename="/admin/ui">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AdminShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:deviceUuid" element={<DeviceDetailPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/dns-logs" element={<DnsLogsPage />} />
          <Route path="/restrictions" element={<RestrictionsPage />} />
          <Route path="/call-rules" element={<CallRulesPage />} />
          <Route path="/dns-denylist" element={<DnsDenylistPage />} />
          <Route path="/allowlist" element={<AllowlistPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
