import { useState, useEffect, useRef, useCallback } from 'react'
import { Play, Square, Monitor, WifiOff, Maximize2, Minimize2, Smartphone, Users, Gauge, Clapperboard } from 'lucide-react'
import { startDetection, stopDetection, getDetectionStatus, uploadVideo } from '../services/api'

export default function LiveMonitoring() {
  const [connected, setConnected] = useState(false)
  const [running, setRunning] = useState(false)
  const [stats, setStats] = useState({ student_count: 0, phone_count: 0, fps: 0, context: 'N/A', frame_id: 0 })
  const [tracks, setTracks] = useState([])
  const [frame, setFrame] = useState(null)
  const wsRef = useRef(null)
  const videoContainerRef = useRef(null)

  const [sourceType, setSourceType] = useState('sample')
  const [rtspUrl, setRtspUrl] = useState('sample://classroom')
  const [uploadedPath, setUploadedPath] = useState('')
  const [uploading, setUploading] = useState(false)

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    checkStatus()
    // Listen for fullscreen changes (Esc key, browser controls)
    const onFSChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onFSChange)
    return () => {
      if (wsRef.current) wsRef.current.close()
      document.removeEventListener('fullscreenchange', onFSChange)
    }
  }, [])

  const checkStatus = async () => {
    try {
      const res = await getDetectionStatus()
      setRunning(res.data.running)
      if (res.data.running) connectWS()
    } catch (e) { console.error(e) }
  }

  const connectWS = () => {
    if (wsRef.current) wsRef.current.close()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/live`)
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'frame' && data.frame) {
          setFrame(data.frame)
          setStats(data.stats || {})
          setTracks(data.tracks || [])
        } else if (data.type === 'status') {
          if (data.running === false && running) {
            setRunning(false)
          }
        }
      } catch (err) {
        console.error('WS parse error:', err)
      }
    }
    wsRef.current = ws
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setUploadedPath('')
    try {
      const res = await uploadVideo(file)
      const path = res.data.path || res.data.filename || ''
      if (!path) throw new Error('No file path returned from server')
      setUploadedPath(path)
    } catch (err) {
      console.error('File upload failed:', err)
      const detail = err.response?.data?.detail || err.message || 'Unknown error'
      alert(`Upload failed: ${detail}`)
    } finally {
      setUploading(false)
    }
  }

  const handleStart = async () => {
    let sourceParam = 'webcam'
    if (sourceType === 'sample') {
      sourceParam = 'classroom_sample'
    } else if (sourceType === 'rtsp') {
      if (!rtspUrl) return alert('Enter RTSP / Stream URL')
      sourceParam = rtspUrl.trim()
    } else if (sourceType === 'video') {
      if (!uploadedPath) return alert('Please upload a video file first')
      sourceParam = uploadedPath
    }
    try {
      // Stop first if running (handles re-start cleanly)
      if (running) {
        await stopDetection()
        setRunning(false)
        if (wsRef.current) wsRef.current.close()
        await new Promise(r => setTimeout(r, 400))
      }
      const res = await startDetection(sourceParam)
      if (res.data.status === 'started' || res.data.status === 'already_running') {
        setRunning(true)
        setTimeout(connectWS, 600)
      }
    } catch (e) {
      console.error('Start failed:', e)
      const detail = e.response?.data?.detail || e.message || 'Unknown error'
      alert(`Failed to start: ${detail}`)
    }
  }

  const handleStop = async () => {
    try {
      await stopDetection()
      setRunning(false)
      if (wsRef.current) wsRef.current.close()
    } catch (e) { console.error(e) }
  }

  // ─── Fullscreen toggle ───
  const toggleFullscreen = useCallback(() => {
    if (!videoContainerRef.current) return
    if (!document.fullscreenElement) {
      videoContainerRef.current.requestFullscreen().catch(err =>
        console.error('Fullscreen request failed:', err)
      )
    } else {
      document.exitFullscreen()
    }
  }, [])

  // Keyboard shortcut: F for fullscreen, Escape handled natively
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'f' || e.key === 'F') {
        // Don't trigger if user is typing in an input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return
        toggleFullscreen()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [toggleFullscreen])

  // FPS color coding
  const fpsColor = stats.fps >= 15 ? 'text-green-500' : stats.fps >= 8 ? 'text-yellow-500' : 'text-red-500'

  return (
    <div>
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-4 gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Live Monitoring</h1>

        <div className="flex flex-col md:flex-row items-center gap-3 bg-white p-2 rounded-lg shadow-sm w-full md:w-auto border">
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            disabled={running}
            className="border-gray-300 rounded-md shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm p-2 bg-gray-50 outline-none font-medium text-gray-800"
          >
            <option value="sample">🎓 Classroom Camera (Sample Feed)</option>
            <option value="video">📁 Upload Video File (Auto-looping)</option>
            <option value="rtsp">🌐 RTSP / Network Stream URL</option>
            <option value="webcam">📷 Local Webcam</option>
          </select>

          {sourceType === 'sample' && (
            <div className="flex items-center gap-2 px-2 text-xs text-gray-600">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span>Full HD Classroom test stream with students & phone usage</span>
            </div>
          )}

          {sourceType === 'rtsp' && (
            <div className="flex flex-col gap-1.5">
              <input
                type="text"
                placeholder="rtsp://192.168.1.100:554/stream"
                value={rtspUrl}
                onChange={(e) => setRtspUrl(e.target.value)}
                disabled={running}
                className="border border-gray-300 rounded-md p-2 text-xs w-80 outline-none font-mono"
              />
              <div className="flex gap-1.5 flex-wrap items-center">
                <span className="text-[11px] text-gray-400 font-medium">Presets:</span>
                {[
                  { label: '🎓 Classroom Stream', url: 'sample://classroom' },
                  { label: '📱 Phone IP Webcam', url: 'http://192.168.1.100:8080/video' },
                  { label: '🎥 Local RTSP', url: 'rtsp://localhost:8554/live' },
                ].map(s => (
                  <button key={s.label} type="button"
                    onClick={() => setRtspUrl(s.url)}
                    disabled={running}
                    className="text-[11px] px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 disabled:opacity-40 font-medium transition"
                  >{s.label}</button>
                ))}
              </div>
            </div>
          )}

          {sourceType === 'video' && (
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
              <input
                type="file"
                accept=".mp4,.avi,.mkv,.mov,.webm"
                onChange={handleFileUpload}
                disabled={running || uploading}
                className="text-xs file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 cursor-pointer w-56"
              />
              {uploading && <span className="text-xs text-blue-500 animate-pulse font-medium">Uploading...</span>}
              {!uploading && uploadedPath && (
                <span className="text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded border border-green-200 font-semibold">
                  ✓ Ready (Auto-loop)
                </span>
              )}
            </div>
          )}

          {!running ? (
            <button
              onClick={handleStart}
              disabled={uploading}
              className="flex items-center justify-center gap-2 px-5 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 min-w-[110px] font-medium transition"
            >
              <Play size={16} />Start
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="flex items-center justify-center gap-2 px-5 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 min-w-[110px] font-medium transition"
            >
              <Square size={16} />Stop
            </button>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="bg-white rounded-lg shadow-sm p-3 flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg"><Users size={18} className="text-blue-600" /></div>
          <div><p className="text-xs text-gray-400">Students</p><p className="text-xl font-bold text-blue-600">{stats.student_count || 0}</p></div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-3 flex items-center gap-3">
          <div className="p-2 bg-red-50 rounded-lg"><Smartphone size={18} className="text-red-600" /></div>
          <div><p className="text-xs text-gray-400">Phones</p><p className="text-xl font-bold text-red-600">{stats.phone_count || 0}</p></div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-3 flex items-center gap-3">
          <div className="p-2 bg-gray-50 rounded-lg"><Gauge size={18} className="text-gray-600" /></div>
          <div><p className="text-xs text-gray-400">FPS</p><p className={`text-xl font-bold ${fpsColor}`}>{stats.fps || 0}</p></div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-3 flex items-center gap-3">
          <div className="p-2 bg-yellow-50 rounded-lg"><Clapperboard size={18} className="text-yellow-600" /></div>
          <div><p className="text-xs text-gray-400">Context</p><p className="text-lg font-bold text-yellow-600">{stats.context || 'N/A'}</p></div>
        </div>
      </div>

      {/* Video + Tracks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* ─── Video Feed with Fullscreen ─── */}
        <div
          ref={videoContainerRef}
          className={`lg:col-span-2 bg-black rounded-xl overflow-hidden relative group ${isFullscreen ? 'fullscreen-container' : ''}`}
          style={{ minHeight: isFullscreen ? '100vh' : '500px' }}
          onDoubleClick={toggleFullscreen}
        >
          {/* Overlay: Connection status */}
          {running && !connected && (
            <div className="absolute top-4 left-4 bg-red-600 text-white px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 z-20 shadow-lg animate-pulse">
              <WifiOff size={16} /> Reconnecting...
            </div>
          )}

          {/* Overlay: Stats HUD (visible in fullscreen) */}
          {isFullscreen && frame && connected && (
            <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-20 pointer-events-none">
              <div className="flex gap-3">
                <span className="bg-black/60 text-white px-3 py-1.5 rounded-lg text-sm backdrop-blur-sm flex items-center gap-1.5">
                  <Users size={14} /> {stats.student_count || 0} Students
                </span>
                <span className="bg-black/60 text-red-400 px-3 py-1.5 rounded-lg text-sm backdrop-blur-sm flex items-center gap-1.5">
                  <Smartphone size={14} /> {stats.phone_count || 0} Phones
                </span>
              </div>
              <div className="flex gap-3">
                <span className={`bg-black/60 px-3 py-1.5 rounded-lg text-sm backdrop-blur-sm ${fpsColor}`}>
                  {stats.fps || 0} FPS
                </span>
                <span className="bg-black/60 text-yellow-400 px-3 py-1.5 rounded-lg text-sm backdrop-blur-sm">
                  {stats.context || 'N/A'}
                </span>
              </div>
            </div>
          )}

          {/* Fullscreen / Minimize button */}
          <button
            onClick={toggleFullscreen}
            className="absolute top-3 right-3 z-20 p-2 bg-black/50 hover:bg-black/80 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 backdrop-blur-sm"
            title={isFullscreen ? 'Exit Fullscreen (Esc)' : 'Fullscreen (F)'}
          >
            {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
          </button>

          {/* Frame number */}
          {frame && connected && (
            <div className="absolute bottom-3 left-3 z-20 bg-black/50 text-white/70 px-2 py-1 rounded text-xs backdrop-blur-sm">
              Frame #{stats.frame_id || 0}
            </div>
          )}

          {/* Exit hint in fullscreen */}
          {isFullscreen && (
            <div className="absolute bottom-3 right-3 z-20 bg-black/40 text-white/50 px-2 py-1 rounded text-xs backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity">
              Press Esc or double-click to exit • F to toggle
            </div>
          )}

          {/* Active Phone Alert Banner */}
          {running && connected && (stats.phone_count || 0) > 0 && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-red-600/95 text-white px-4 py-1.5 rounded-full text-xs font-bold flex items-center gap-2 shadow-xl backdrop-blur-sm animate-pulse border border-red-400 pointer-events-none">
              <Smartphone size={16} />
              <span>UNAUTHORIZED PHONE DETECTED ({stats.phone_count})</span>
            </div>
          )}

          {/* Video Frame */}
          {frame && connected ? (
            <img
              src={`data:image/jpeg;base64,${frame}`}
              alt="Live Feed"
              className="w-full h-full object-contain"
              draggable={false}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <Monitor size={56} className="mx-auto mb-3 opacity-30" />
                <p className="text-lg">{running ? (connected ? 'Waiting for frames...' : 'Connecting...') : 'Pipeline stopped'}</p>
                <p className="text-sm text-gray-600 mt-1">
                  {running ? '' : 'Select a source and click Start to begin monitoring'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ─── Tracks Panel ─── */}
        <div className={`bg-white rounded-xl shadow-sm p-4 overflow-y-auto ${isFullscreen ? 'hidden' : 'max-h-[560px]'}`}>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center justify-between">
            <span>Active Tracks ({tracks.length})</span>
            {running && connected && (
              <span className="flex items-center gap-1 text-xs text-green-500">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" /> Live
              </span>
            )}
          </h3>
          {tracks.length === 0 && <p className="text-sm text-gray-400">No active tracks</p>}
          <div className="space-y-2">
            {tracks.map((t, i) => {
              const isPhone = t.class_name === 'mobile_phone'
              const isDanger = t.state === 'potential_phone_use'
              const isWarn = t.state === 'suspicious'
              const bgClass = isPhone
                ? 'bg-red-50 border-red-300'
                : isDanger ? 'bg-red-50 border-red-400'
                : isWarn ? 'bg-yellow-50 border-yellow-300'
                : 'bg-green-50 border-green-200'
              const conf = typeof t.confidence === 'number' ? (t.confidence * 100).toFixed(0) : '?'
              const dur = typeof t.duration === 'number' ? t.duration.toFixed(1) : '-'
              const isUnknown = !isPhone && (!t.roll_number || t.roll_number === 'UNKNOWN' || t.roll_number === 'N/A' || t.student_name === 'Unknown Person' || t.student_name === 'Unknown' || !t.is_identified)
              const stuName = isPhone ? t.display_id : (isUnknown ? 'Unknown Person' : (t.student_name || 'Student'))
              const rollNo = isUnknown ? null : t.roll_number
              const dept = t.department && t.department !== 'N/A' ? t.department : null
              const sec = t.section && t.section !== 'N/A' ? t.section : null
              const matchConf = typeof t.match_confidence === 'number' && t.match_confidence > 0 ? t.match_confidence.toFixed(1) : null
              const identityStatus = !isPhone ? (t.identity_status || (isUnknown ? 'Unverified' : 'Verified')) : null
              const phoneStatus = isPhone ? 'Device' : (isDanger ? 'Phone in Use' : isWarn ? 'Suspicious' : 'Normal')

              return (
                <div key={i} className={`p-3 rounded-lg border text-sm transition-all shadow-sm ${bgClass}`}>
                  {/* Row 1: Name + Status Badges */}
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex flex-col">
                      <span className="font-semibold text-gray-900 flex items-center gap-1.5">
                        {isPhone ? <Smartphone size={14} className="text-red-500" /> : <Users size={14} className={isUnknown ? "text-gray-400" : "text-blue-600"} />}
                        <span className="truncate max-w-[130px]">{stuName}</span>
                      </span>
                      {!isPhone && (
                        <span className="text-[11px] text-gray-500 font-mono mt-0.5">
                          ID: <span className="font-semibold text-gray-700">{t.display_id}</span>
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {!isPhone && (
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          identityStatus === 'Verified'
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                            : 'bg-gray-100 text-gray-600 border-gray-300'
                        }`}>
                          {identityStatus}
                        </span>
                      )}
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        isDanger ? 'bg-red-100 text-red-700 border border-red-300 animate-pulse' :
                        isWarn ? 'bg-yellow-100 text-yellow-800 border border-yellow-300' :
                        isPhone ? 'bg-red-100 text-red-600 border border-red-200' :
                        'bg-green-100 text-green-700 border border-green-300'
                      }`}>
                        {phoneStatus}
                      </span>
                    </div>
                  </div>

                  {/* Row 2: Roll Number & Department/Section if verified */}
                  {!isPhone && !isUnknown && (
                    <div className="mt-2 pt-2 border-t border-gray-200/60 flex flex-wrap items-center gap-1.5 text-xs">
                      {rollNo && (
                        <span className="font-mono bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-bold border border-blue-200 text-[11px]">
                          Roll: {rollNo}
                        </span>
                      )}
                      {dept && (
                        <span className="bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded text-[11px] font-medium border border-purple-200">
                          {dept}{sec ? ` - Sec ${sec}` : ''}
                        </span>
                      )}
                      {matchConf && (
                        <span className="bg-teal-50 text-teal-700 px-1.5 py-0.5 rounded text-[11px] font-medium border border-teal-200">
                          Match: {matchConf}%
                        </span>
                      )}
                    </div>
                  )}

                  {/* Row 3: Meta & Timing */}
                  <div className="flex justify-between items-center text-[11px] text-gray-500 mt-2 pt-1 border-t border-gray-200/40">
                    <span>Det: {conf}% • {dur}s</span>
                    {!isPhone && t.parent_mobile && (
                      <span className="text-[10px] text-gray-500 font-mono">Parent: {t.parent_mobile}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Fullscreen CSS */}
      <style>{`
        .fullscreen-container {
          display: flex;
          align-items: center;
          justify-content: center;
          background: #000;
          cursor: none;
        }
        .fullscreen-container:hover {
          cursor: default;
        }
        .fullscreen-container img {
          max-width: 100%;
          max-height: 100vh;
          object-fit: contain;
        }
      `}</style>
    </div>
  )
}
