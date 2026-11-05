import { useState, useEffect } from 'react'
import { Bell, Check, CheckCheck, Send, Trash2, Plus, MessageSquare, MessageCircle } from 'lucide-react'
import { getAlerts, updateAlertStatus, createTestAlert, sendAlertSms, deleteAlert } from '../services/api'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState('')
  const [total, setTotal] = useState(0)
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [smsModalAlert, setSmsModalAlert] = useState(null)
  const [smsSending, setSmsSending] = useState(false)
  const [smsResult, setSmsResult] = useState(null)

  useEffect(() => { fetchAlerts() }, [filter])

  const fetchAlerts = async () => {
    try {
      const res = await getAlerts({ status: filter || undefined, limit: 100 })
      setAlerts(res.data.alerts || [])
      setTotal(res.data.total || 0)
    } catch (e) { console.error(e) }
  }

  const handleStatus = async (alertId, status) => {
    try {
      await updateAlertStatus(alertId, status)
      showMsg(`Alert ${alertId} marked as ${status}`)
      fetchAlerts()
    } catch (e) {
      console.error(e)
      showMsg('Failed to update alert status')
    }
  }

  const handleOpenSmsModal = (alert) => {
    setSmsModalAlert(alert)
    setSmsResult(null)
  }

  const handleDispatchSms = async () => {
    if (!smsModalAlert) return
    try {
      setSmsSending(true)
      const res = await sendAlertSms(smsModalAlert.alert_id)
      setSmsResult(res.data)
      showMsg(`SMS successfully dispatched for alert ${smsModalAlert.alert_id}!`)
      fetchAlerts()
    } catch (e) {
      console.error(e)
      setSmsResult({ error: e.response?.data?.detail || e.message })
    } finally {
      setSmsSending(false)
    }
  }

  const handleSendSms = async (alertId) => {
    try {
      setLoading(true)
      const res = await sendAlertSms(alertId)
      const count = res.data.count || 0
      showMsg(`SMS sent for alert ${alertId}: ${count} notification(s) processed`)
      fetchAlerts()
    } catch (e) {
      console.error(e)
      showMsg('SMS send failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (alertId) => {
    if (!confirm(`Delete alert ${alertId}?`)) return
    try {
      await deleteAlert(alertId)
      showMsg(`Alert ${alertId} deleted`)
      fetchAlerts()
    } catch (e) {
      console.error(e)
      showMsg('Failed to delete alert')
    }
  }

  const handleTestAlert = async () => {
    try {
      setLoading(true)
      const res = await createTestAlert({
        student_display_id: 'ST-21CS101',
        student_name: 'Rahul Sharma',
        roll_number: '21CS101',
        anomaly_score: 0.88,
        phone_confidence: 0.94,
        duration: 18.5,
        context: 'LECTURE',
        reasons: ['Phone detected in active hand region during lecture'],
      })
      const smsCount = res.data.sms_notifications?.length || 0
      showMsg(`Test alert created! ${smsCount} SMS notification(s) sent to student & parent.`)
      fetchAlerts()
    } catch (e) {
      console.error(e)
      showMsg('Failed to create test alert')
    } finally {
      setLoading(false)
    }
  }

  const showMsg = (text) => {
    setMsg(text)
    setTimeout(() => setMsg(''), 5000)
  }

  const statusColors = {
    NEW: 'bg-red-100 text-red-700',
    ACKNOWLEDGED: 'bg-yellow-100 text-yellow-700',
    RESOLVED: 'bg-green-100 text-green-700',
  }

  const formatTime = (ts) => {
    try { return new Date(ts * 1000).toLocaleString() }
    catch { return '-' }
  }

  const buildWhatsAppLink = (phone, alert) => {
    if (!phone) return '#'
    const cleanPhone = phone.replace(/\D/g, '')
    const intlPhone = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone
    const evidenceUrl = alert.evidence_url
      ? (alert.evidence_url.startsWith('http')
          ? alert.evidence_url
          : `${window.location.protocol}//${window.location.hostname}:8000${alert.evidence_url}`)
      : ''

    const text =
      `⚠️ *Classroom Monitoring System: Phone Usage Alert*\n\n` +
      `Dear Parent/Student,\n` +
      `Unauthorized mobile phone usage was detected during an academic session.\n\n` +
      `📋 *Student:* ${alert.student_name || 'Enrolled Student'}\n` +
      `🔢 *Roll Number:* ${alert.roll_number || 'N/A'}\n` +
      `🏢 *Department:* ${alert.department || 'Computer Science'}${alert.section ? ` - Sec ${alert.section}` : ''}\n` +
      `⏱ *Duration:* ${alert.duration ? alert.duration.toFixed(1) + 's' : 'N/A'}\n` +
      `🕒 *Context:* ${alert.context || 'LECTURE'}\n` +
      (evidenceUrl ? `\n📹 *Video Evidence Clip:*\n${evidenceUrl}\n` : '') +
      `\n-- Classpulse Monitoring System`

    return `https://wa.me/${intlPhone}?text=${encodeURIComponent(text)}`
  }

  return (
    <div>
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-6 gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Alerts ({total})</h1>
        <div className="flex gap-2 flex-wrap">
          {['', 'NEW', 'ACKNOWLEDGED', 'RESOLVED'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm ${filter === f ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {f || 'All'}
            </button>
          ))}
          <button onClick={handleTestAlert} disabled={loading}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-orange-100 text-orange-700 hover:bg-orange-200 disabled:opacity-50">
            <Plus size={14} />Test Alert
          </button>
        </div>
      </div>

      {msg && (
        <div className="mb-4 p-3 bg-blue-50 text-blue-700 rounded-lg text-sm flex items-center gap-2 border border-blue-200">
          <MessageSquare size={16} />{msg}
        </div>
      )}

      {alerts.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">
          <Bell size={48} className="mx-auto mb-4 opacity-30" />
          <p>No alerts found.</p>
          <p className="text-sm mt-2">Alerts appear when suspicious phone usage is detected during monitoring.</p>
          <button onClick={handleTestAlert} className="mt-4 px-4 py-2 bg-orange-100 text-orange-700 rounded-lg text-sm hover:bg-orange-200">
            Create Test Alert
          </button>
        </div>
      )}

      <div className="space-y-3">
        {alerts.map(alert => {
          const isUnknown = !alert.roll_number || alert.roll_number === 'UNKNOWN' || alert.roll_number === 'N/A' || alert.student_name === 'Unknown Person' || alert.student_name === 'Unknown' || alert.student_name === 'Enrolled Student'
          const rollNumber = isUnknown ? 'UNKNOWN' : alert.roll_number
          const studentName = isUnknown ? 'Unknown Person' : alert.student_name

          return (
            <div key={alert.alert_id || alert._id} className="bg-white rounded-xl shadow-sm p-5 border-l-4 border-l-red-500 hover:shadow-md transition">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${statusColors[alert.status] || 'bg-gray-100'}`}>
                      {alert.status}
                    </span>
                    {/* Student Name */}
                    <span className="text-base font-bold text-gray-900">
                      {studentName}
                    </span>
                    {/* Prominent Roll Number / Identity Badge */}
                    {isUnknown ? (
                      <span className="px-2.5 py-0.5 bg-gray-100 text-gray-700 rounded font-mono text-xs font-semibold border border-gray-300">
                        Unregistered / Unknown Person
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 bg-blue-100 text-blue-800 rounded font-mono text-xs font-bold border border-blue-200">
                        Roll No: {rollNumber}
                      </span>
                    )}
                    {alert.department && alert.department !== 'N/A' && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {alert.department}
                      </span>
                    )}
                    <span className="text-xs text-gray-400 font-mono">
                      Track: {alert.student_display_id || 'ST-???'} | ID: {alert.alert_id}
                    </span>
                  </div>

                  {/* Student & Parent Contacts */}
                  {(alert.student_mobile || alert.parent_mobile) && (
                    <div className="flex items-center gap-4 text-xs text-gray-600 mb-2 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
                      {alert.student_mobile && (
                        <span><strong className="text-gray-700">Student Mobile:</strong> {alert.student_mobile}</span>
                      )}
                      {alert.parent_mobile && (
                        <span><strong className="text-gray-700">Parent Mobile:</strong> {alert.parent_mobile}</span>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-2">
                    <div><span className="text-gray-400">Score: </span><span className="font-medium text-red-600">{((alert.anomaly_score || 0) * 100).toFixed(0)}%</span></div>
                    <div><span className="text-gray-400">Phone: </span><span className="font-medium">{((alert.phone_confidence || 0) * 100).toFixed(0)}%</span></div>
                    <div><span className="text-gray-400">Duration: </span><span className="font-medium">{(alert.duration || 0).toFixed(1)}s</span></div>
                    <div><span className="text-gray-400">Context: </span><span className="font-medium">{alert.context || 'N/A'}</span></div>
                  </div>

                  {alert.reasons && alert.reasons.length > 0 && (
                    <p className="text-xs text-gray-600 mb-1 font-medium">⚠️ Reason: {alert.reasons.join(' | ')}</p>
                  )}
                  {alert.evidence_url && (
                    <div className="mt-2.5 flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedVideo({ url: alert.evidence_url, alert_id: alert.alert_id, name: studentName, roll: rollNumber })}
                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-semibold hover:bg-red-200 transition cursor-pointer"
                      >
                        ▶ Watch Evidence Clip
                      </button>
                      <a href={alert.evidence_url} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-gray-400 hover:text-gray-600 hover:underline">
                        Open in tab
                      </a>
                    </div>
                  )}
                  <div className="flex items-center gap-2.5 text-xs text-gray-400 mt-2.5 flex-wrap">
                    <span>{formatTime(alert.timestamp)} | {alert.camera_id || 'CAM-01'}</span>

                    {/* Instant Free WhatsApp Quick Actions */}
                    {alert.parent_mobile && (
                      <a
                        href={buildWhatsAppLink(alert.parent_mobile, alert)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-300 rounded-lg font-semibold text-xs flex items-center gap-1.5 hover:bg-emerald-100 transition shadow-sm"
                        title="Open WhatsApp to send instant report to parent"
                      >
                        <MessageCircle size={13} className="text-emerald-600" /> WhatsApp Parent ({alert.parent_mobile})
                      </a>
                    )}
                    {alert.student_mobile && alert.student_mobile !== alert.parent_mobile && (
                      <a
                        href={buildWhatsAppLink(alert.student_mobile, alert)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-300 rounded-lg font-semibold text-xs flex items-center gap-1.5 hover:bg-emerald-100 transition shadow-sm"
                        title="Open WhatsApp to send instant report to student"
                      >
                        <MessageCircle size={13} className="text-emerald-600" /> WhatsApp Student
                      </a>
                    )}

                    {alert.sms_sent ? (
                      <button
                        type="button"
                        onClick={() => handleOpenSmsModal(alert)}
                        className="text-xs text-green-700 bg-green-50 px-2.5 py-1 rounded-lg border border-green-200 font-semibold hover:bg-green-100 flex items-center gap-1 cursor-pointer"
                      >
                        ✓ Dispatched (View Logs)
                      </button>
                    ) : isUnknown ? (
                      <span className="text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded border">
                        No Mobile Linked (Unknown Person)
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleOpenSmsModal(alert)}
                        className="text-xs text-blue-700 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200 font-semibold hover:bg-blue-100 flex items-center gap-1 cursor-pointer"
                      >
                        📲 Dispatch & Options
                      </button>
                    )}
                  </div>
                </div>

              <div className="flex gap-1 ml-4 flex-shrink-0">
                {alert.status === 'NEW' && (
                  <button onClick={() => handleStatus(alert.alert_id, 'ACKNOWLEDGED')}
                    className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg" title="Acknowledge">
                    <Check size={18} />
                  </button>
                )}
                {alert.status !== 'RESOLVED' && (
                  <button onClick={() => handleStatus(alert.alert_id, 'RESOLVED')}
                    className="p-2 text-green-600 hover:bg-green-50 rounded-lg" title="Resolve">
                    <CheckCheck size={18} />
                  </button>
                )}
                <button 
                  onClick={() => handleOpenSmsModal(alert)} 
                  disabled={loading || isUnknown || (!alert.student_mobile && !alert.parent_mobile)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer" 
                  title={isUnknown ? "SMS unavailable for unidentified person" : "Send SMS notification with evidence to student & parent"}>
                  <Send size={18} />
                </button>
                <button onClick={() => handleDelete(alert.alert_id)}
                  className="p-2 text-red-400 hover:bg-red-50 rounded-lg" title="Delete">
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          </div>
        )
      })}
      </div>

      {/* Video Evidence Modal */}
      {selectedVideo && (
        <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4 backdrop-blur-xs" onClick={() => setSelectedVideo(null)}>
          <div className="bg-gray-900 rounded-2xl max-w-2xl w-full p-4 overflow-hidden shadow-2xl border border-gray-700" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-white font-bold text-sm flex items-center gap-2">
                📹 Suspicious Activity Evidence Clip ({selectedVideo.alert_id})
              </h3>
              <button onClick={() => setSelectedVideo(null)} className="text-gray-400 hover:text-white text-lg font-bold px-2 py-1 cursor-pointer">✕</button>
            </div>
            <div className="rounded-lg overflow-hidden bg-black flex items-center justify-center aspect-video relative">
              <video
                key={selectedVideo.url}
                controls
                autoPlay
                muted
                playsInline
                preload="auto"
                className="w-full h-full object-contain"
              >
                <source src={selectedVideo.url} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>
            <div className="mt-3 text-xs text-gray-300 flex justify-between items-center">
              <span>Identified Student: <strong className="text-white">{selectedVideo.name}</strong> ({selectedVideo.roll})</span>
              <a href={selectedVideo.url} download className="text-primary-400 hover:underline">Download MP4 Clip</a>
            </div>
          </div>
        </div>
      )}

      {/* SMS Notification Details & Dispatch Modal */}
      {smsModalAlert && (
        <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4 backdrop-blur-xs" onClick={() => setSmsModalAlert(null)}>
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-gray-200 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center pb-3 border-b mb-4">
              <div>
                <h3 className="text-gray-900 font-bold text-base flex items-center gap-2">
                  📲 SMS Notification: Student & Parent Dispatch
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Sends student details, incident timestamp, and video evidence clip link to mobile phones.
                </p>
              </div>
              <button onClick={() => setSmsModalAlert(null)} className="text-gray-400 hover:text-gray-600 text-lg font-bold px-2 py-1 cursor-pointer">✕</button>
            </div>

            {/* Student & Parent Info Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-blue-50 rounded-xl border border-blue-100">
                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700">Student Recipient</span>
                <p className="font-bold text-gray-900 text-sm mt-1">{smsModalAlert.student_name} ({smsModalAlert.roll_number})</p>
                <p className="text-xs text-gray-600">📱 Mobile: <span className="font-mono font-semibold">{smsModalAlert.student_mobile || 'Not registered'}</span></p>
                <p className="text-xs text-gray-500">Dept: {smsModalAlert.department || 'N/A'}{smsModalAlert.section ? ` - Sec ${smsModalAlert.section}` : ''}</p>
              </div>
              <div className="p-3 bg-purple-50 rounded-xl border border-purple-100">
                <span className="text-[11px] font-bold uppercase tracking-wider text-purple-700">Parent Recipient</span>
                <p className="font-bold text-gray-900 text-sm mt-1">Parent of {smsModalAlert.student_name}</p>
                <p className="text-xs text-gray-600">📱 Mobile: <span className="font-mono font-semibold">{smsModalAlert.parent_mobile || 'Not registered'}</span></p>
                <p className="text-xs text-gray-500">Relation: Father / Mother / Guardian</p>
              </div>
            </div>

            {/* Video Evidence Link Info */}
            <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 mb-4 flex items-center justify-between">
              <div>
                <span className="text-xs text-gray-500 font-medium">Included Video Evidence Clip:</span>
                <p className="font-mono text-xs text-gray-800 truncate max-w-md">{smsModalAlert.evidence_url || 'Recorded MP4 video clip'}</p>
              </div>
              {smsModalAlert.evidence_url && (
                <button
                  type="button"
                  onClick={() => setSelectedVideo({ url: smsModalAlert.evidence_url, alert_id: smsModalAlert.alert_id, name: smsModalAlert.student_name, roll: smsModalAlert.roll_number })}
                  className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-semibold hover:bg-red-200 transition cursor-pointer"
                >
                  ▶ Preview Clip
                </button>
              )}
            </div>

            {/* Message Preview */}
            <div className="mb-4">
              <span className="text-xs font-bold text-gray-700 mb-2 block">Formatted SMS Message Preview:</span>
              <div className="bg-gray-900 text-green-400 font-mono text-xs p-3.5 rounded-xl border border-gray-800 space-y-2 whitespace-pre-wrap leading-relaxed shadow-inner">
                {`⚠️ Classroom Monitoring System
DISCIPLINE ALERT: MOBILE PHONE DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dear ${smsModalAlert.student_name},

Unauthorized phone usage was detected during your classroom session.

📋 Student Information:
• Name: ${smsModalAlert.student_name}
• Roll Number: ${smsModalAlert.roll_number}
• Department: ${smsModalAlert.department || 'Computer Science'}${smsModalAlert.section ? ` - Sec ${smsModalAlert.section}` : ''}

🕒 Incident Details:
• Date & Time: ${formatTime(smsModalAlert.timestamp)}
• Duration: ${smsModalAlert.duration ? smsModalAlert.duration.toFixed(1) + 's' : 'N/A'}
• Alert Reference: ${smsModalAlert.alert_id}

📹 Video Evidence Clip:
http://10.10.53.113:8000${smsModalAlert.evidence_url || '/evidence/...'}
(Tap link above to play recorded clip on your mobile phone)`}
              </div>
            </div>

            {/* Delivery Result Message */}
            {smsResult && (() => {
              const notifications = smsResult.sms_notifications || []
              const allFailed = notifications.length > 0 && notifications.every(n => n.result?.status === 'error')
              const someFailed = notifications.some(n => n.result?.status === 'error')
              const isError = smsResult.error || allFailed

              return (
                <div className={`p-3 rounded-xl mb-4 text-xs border ${
                  isError ? 'bg-red-50 text-red-800 border-red-300' : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}>
                  {smsResult.error ? (
                    <p><strong>Error:</strong> {smsResult.error}</p>
                  ) : (
                    <div>
                      <p className={`font-bold flex items-center gap-1 mb-1 ${isError ? 'text-red-900' : 'text-emerald-950'}`}>
                        {isError ? '❌ SMS Dispatch Failed' : (someFailed ? '⚠️ SMS Partially Dispatched' : '✓ SMS Dispatched Successfully')}
                      </p>
                      <div className="space-y-1.5 mt-1 text-[11px]">
                        {notifications.map((n, idx) => {
                          const status = n.result?.status || 'unknown'
                          const isErr = status === 'error'
                          return (
                            <div key={idx} className="p-1.5 bg-white/70 rounded border border-gray-200">
                              <p>
                                • Sent to <strong>{n.type}</strong> ({n.mobile}): Status ={' '}
                                <span className={`font-bold uppercase ${isErr ? 'text-red-600' : 'text-emerald-700'}`}>
                                  {status}
                                </span>
                              </p>
                              {n.result?.error && (
                                <p className="text-red-600 text-[10px] mt-0.5 font-mono">
                                  {n.result.error}
                                </p>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}

            {/* Carrier Info Note */}
            <div className="text-[11px] text-gray-600 bg-gray-50 p-2.5 rounded-lg border border-gray-200 mb-3 space-y-1">
              <div className="flex items-center justify-between font-semibold text-gray-800">
                <span>📱 Instant Free Delivery: WhatsApp (No carrier credits required)</span>
                <span className="text-emerald-700 font-mono text-[10px] bg-emerald-100 px-2 py-0.5 rounded font-bold">100% Free</span>
              </div>
              <p className="text-[10px] text-gray-500">
                Tap the WhatsApp buttons below to send the full incident report and video clip directly into WhatsApp chats.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-between items-center gap-2 pt-2 border-t flex-wrap">
              <div className="flex items-center gap-2 flex-wrap">
                {smsModalAlert.parent_mobile && (
                  <a
                    href={buildWhatsAppLink(smsModalAlert.parent_mobile, smsModalAlert)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
                  >
                    <MessageCircle size={14} /> Send WhatsApp to Parent ({smsModalAlert.parent_mobile})
                  </a>
                )}
                {smsModalAlert.student_mobile && smsModalAlert.student_mobile !== smsModalAlert.parent_mobile && (
                  <a
                    href={buildWhatsAppLink(smsModalAlert.student_mobile, smsModalAlert)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3.5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
                  >
                    <MessageCircle size={14} /> Send WhatsApp to Student
                  </a>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSmsModalAlert(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50 cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleDispatchSms}
                  disabled={smsSending || (!smsModalAlert.student_mobile && !smsModalAlert.parent_mobile)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
                >
                  <Send size={14} />
                  {smsSending ? 'Dispatching...' : '🚀 Send SMS via Brevo'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
