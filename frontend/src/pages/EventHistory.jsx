import { useState, useEffect } from 'react'
import { Clock } from 'lucide-react'
import { getAlerts } from '../services/api'

export default function EventHistory() {
  const [events, setEvents] = useState([])

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await getAlerts({ limit: 200 })
        setEvents(res.data.alerts)
      } catch (e) { console.error(e) }
    }
    fetch()
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Event History</h1>

      {events.length === 0 && <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400"><Clock size={48} className="mx-auto mb-4 opacity-30" /><p>No events recorded yet.</p></div>}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Time</th>
              <th className="px-4 py-3 text-left">Student</th>
              <th className="px-4 py-3 text-left">Event</th>
              <th className="px-4 py-3 text-center">Score</th>
              <th className="px-4 py-3 text-left">Context</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {events.map(e => (
              <tr key={e.alert_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-xs text-gray-500">{new Date(e.timestamp * 1000).toLocaleString()}</td>
                <td className="px-4 py-3 font-medium">{e.student_name || e.student_display_id}</td>
                <td className="px-4 py-3 text-xs">{e.event_type?.replace(/_/g, ' ')}</td>
                <td className="px-4 py-3 text-center"><span className={`px-2 py-0.5 rounded text-xs font-medium ${e.anomaly_score >= 0.7 ? 'bg-danger-100 text-danger-700' : 'bg-warning-100 text-warning-700'}`}>{(e.anomaly_score * 100).toFixed(0)}%</span></td>
                <td className="px-4 py-3 text-xs">{e.context}</td>
                <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs font-medium ${e.status === 'NEW' ? 'bg-danger-100 text-danger-700' : e.status === 'ACKNOWLEDGED' ? 'bg-warning-100 text-warning-700' : 'bg-success-100 text-success-700'}`}>{e.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
