import { useState, useEffect } from 'react'
import { Activity, Bell, Users, Smartphone, Eye, Shield, AlertTriangle } from 'lucide-react'
import { getDashboardStats, getAlertCounts, getAlerts } from '../services/api'

function StatCard({ icon: Icon, label, value, color = 'primary', sub }) {
  const bgMap = { primary: 'bg-primary-50 text-primary-600', danger: 'bg-red-50 text-red-600', warning: 'bg-yellow-50 text-yellow-600', success: 'bg-green-50 text-green-600' }
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 flex items-start gap-4">
      <div className={`p-3 rounded-lg ${bgMap[color] || bgMap.primary}`}><Icon size={24} /></div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [alertCounts, setAlertCounts] = useState(null)
  const [recentAlerts, setRecentAlerts] = useState([])
  const [user, setUser] = useState(null)

  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem('user') || '{}')) } catch {}

    const fetchData = async () => {
      try {
        const [s, a, al] = await Promise.all([
          getDashboardStats(),
          getAlertCounts(),
          getAlerts({ status: 'NEW', limit: 5 }),
        ])
        setStats(s.data)
        setAlertCounts(a.data)
        setRecentAlerts(al.data.alerts || [])
      } catch (e) { console.error('Dashboard fetch error:', e) }
    }
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (ts) => {
    try {
      const d = new Date(ts * 1000)
      const now = new Date()
      const diff = (now - d) / 1000
      if (diff < 60) return 'Just now'
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
      return d.toLocaleDateString()
    } catch { return '-' }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          {user?.name && <p className="text-sm text-gray-500 mt-1">Welcome back, {user.name}</p>}
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${stats?.pipeline_running ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
          <div className={`w-2 h-2 rounded-full ${stats?.pipeline_running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
          {stats?.pipeline_running ? `Running (${stats?.fps || 0} FPS)` : 'Pipeline Stopped'}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={Eye} label="Pipeline Status" value={stats?.pipeline_running ? 'Active' : 'Stopped'} color={stats?.pipeline_running ? 'success' : 'primary'} sub={stats?.pipeline_running ? `${stats?.fps} FPS` : 'Start from Live Monitoring'} />
        <StatCard icon={Bell} label="Total Alerts" value={alertCounts?.total || 0} color="danger" sub={`${alertCounts?.today || 0} today`} />
        <StatCard icon={Users} label="Enrolled Students" value={stats?.enrolled_students || 0} color="primary" />
        <StatCard icon={Shield} label="Context Mode" value={stats?.context || 'N/A'} color="warning" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle size={18} className="text-red-500" />New Alerts
            </h2>
            <a href="/alerts" className="text-sm text-primary-600 hover:underline">View all →</a>
          </div>

          {recentAlerts.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">No new alerts</p>
          ) : (
            <div className="space-y-3">
              {recentAlerts.map(alert => (
                <div key={alert.alert_id || alert._id} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-100">
                  <div className="w-2 h-2 mt-2 rounded-full bg-red-500 flex-shrink-0 animate-pulse" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-gray-900">{alert.student_display_id || 'Unknown'}</span>
                      <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">{((alert.anomaly_score || 0) * 100).toFixed(0)}% score</span>
                    </div>
                    <p className="text-xs text-gray-600 truncate">
                      {alert.reasons?.length > 0 ? alert.reasons[0] : 'Suspicious activity detected'}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">{formatTime(alert.timestamp)} | {alert.context}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Alert Summary + System Info */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Alert Summary</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center"><span className="text-sm text-gray-600">New</span><span className="px-2 py-1 bg-red-100 text-red-700 rounded text-sm font-medium">{alertCounts?.new || 0}</span></div>
              <div className="flex justify-between items-center"><span className="text-sm text-gray-600">Acknowledged</span><span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-sm font-medium">{alertCounts?.acknowledged || 0}</span></div>
              <div className="flex justify-between items-center"><span className="text-sm text-gray-600">Resolved</span><span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm font-medium">{alertCounts?.resolved || 0}</span></div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">System Info</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Detection Model</span><span className="font-medium">YOLOv11n (COCO)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Tracking</span><span className="font-medium">ByteTrack (Anonymous IDs)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Tracker</span><span className="font-medium">ByteTrack</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Anomaly</span><span className="font-medium">A=w1·D+w2·S+w3·T+w4·C</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
