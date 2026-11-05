import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import LiveMonitoring from './pages/LiveMonitoring'
import Alerts from './pages/Alerts'
import Students from './pages/Students'
import EventHistory from './pages/EventHistory'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import About from './pages/About'
import Login from './pages/Login'
import ForgotPassword from './pages/ForgotPassword'
import AdminLogin from './pages/AdminLogin'
import AdminForgotPassword from './pages/AdminForgotPassword'
import AdminDashboard from './pages/AdminDashboard'

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

function AdminProtectedRoute({ children }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/admin-login" replace />
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (user.role !== 'admin') return <Navigate to="/admin-login" replace />
  } catch { return <Navigate to="/admin-login" replace /> }
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/admin-login" element={<AdminLogin />} />
        <Route path="/admin-forgot-password" element={<AdminForgotPassword />} />

        {/* Admin dashboard (standalone, no sidebar layout) */}
        <Route path="/admin" element={<AdminProtectedRoute><AdminDashboard /></AdminProtectedRoute>} />

        {/* Teacher dashboard routes */}
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="live" element={<LiveMonitoring />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="students" element={<Students />} />
          <Route path="events" element={<EventHistory />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
          <Route path="about" element={<About />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
