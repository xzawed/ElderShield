import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AdminShell from './layouts/AdminShell'
import AuditPage from './pages/AuditPage'
import DashboardPage from './pages/DashboardPage'
import DeviceDetailPage from './pages/DeviceDetailPage'
import DevicesPage from './pages/DevicesPage'
import DnsLogsPage from './pages/DnsLogsPage'
import IncidentPage from './pages/IncidentPage'
import LoginPage from './pages/LoginPage'

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
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
