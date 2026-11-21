import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AdminShell from './layouts/AdminShell'
import DashboardPage from './pages/DashboardPage'
import DevicesPage from './pages/DevicesPage'
import LoginPage from './pages/LoginPage'

export default function App() {
  return (
    <BrowserRouter basename="/admin/ui">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AdminShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}