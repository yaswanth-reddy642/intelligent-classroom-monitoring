import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Monitor, Bell, Users, Clock, BarChart3, Settings as SettingsIcon, Info, LogOut } from 'lucide-react'
import { useState, useEffect } from 'react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/live', label: 'Live Monitoring', icon: Monitor },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/students', label: 'Students', icon: Users },
  { path: '/events', label: 'Event History', icon: Clock },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
  { path: '/about', label: 'About', icon: Info },
]

export default function Layout() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)

  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem('user') || '{}')
      setUser(u)
    } catch { setUser({}) }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="px-6 py-5 border-b border-gray-700">
          <h1 className="text-lg font-bold">🎓 Classroom Monitor</h1>
          <p className="text-xs text-gray-400 mt-1">YOLOv11 + Anonymous Tracking</p>
        </div>
        <nav className="flex-1 py-4 overflow-y-auto">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm transition-colors ${
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User info + Logout */}
        <div className="border-t border-gray-700 px-4 py-3">
          {user?.name && (
            <div className="mb-2">
              <p className="text-sm font-medium text-gray-200 truncate">{user.name}</p>
              <p className="text-xs text-gray-500 truncate">{user.email}</p>
            </div>
          )}
          <button onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition">
            <LogOut size={16} />Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
