import { useState, useEffect } from 'react'
import {
  getContext,
  setContext,
  startDetection,
  stopDetection,
  getDetectionStatus,
  getModelInfo,
} from '../services/api'

export default function Settings() {
  const [ctx, setCtx] = useState('LECTURE')
  const [running, setRunning] = useState(false)
  const [source, setSource] = useState('webcam')
  const [modelInfo, setModelInfo] = useState(null)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    const fetch = async () => {
      try {
        const [ctxRes, statusRes] = await Promise.all([
          getContext(),
          getDetectionStatus(),
        ])
        setCtx(ctxRes.data.mode)
        setRunning(statusRes.data.running)
        try {
          const mi = await getModelInfo()
          setModelInfo(mi.data)
        } catch (e) {}
      } catch (e) {
        console.error(e)
      }
    }
    fetch()
  }, [])

  const handleContext = async (mode) => {
    try {
      await setContext(mode)
      setCtx(mode)
      setMsg(`Context changed to ${mode}`)
      setTimeout(() => setMsg(''), 3000)
    } catch (e) {
      console.error(e)
    }
  }

  const handleToggle = async () => {
    try {
      if (running) {
        await stopDetection()
        setRunning(false)
        setMsg('Pipeline stopped')
      } else {
        await startDetection(source)
        setRunning(true)
        setMsg('Pipeline started')
      }
      setTimeout(() => setMsg(''), 3000)
    } catch (e) {
      setMsg('Failed: ' + (e.response?.data?.detail || e.message))
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-xs text-gray-500 mt-1">
            Configure classroom context, video pipeline, and AI models.
          </p>
        </div>
      </div>

      {msg && (
        <div className="p-3 bg-primary-50 text-primary-700 rounded-lg text-sm border border-primary-200">
          {msg}
        </div>
      )}

      {/* 1. Pipeline Control */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h2 className="text-lg font-semibold mb-4 text-gray-900">1. Pipeline Control</h2>
        <div className="flex items-center gap-4 mb-4">
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="webcam, video.mp4, or rtsp://..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <button
            onClick={handleToggle}
            className={`px-6 py-2 rounded-lg text-white font-medium cursor-pointer ${
              running ? 'bg-danger-600 hover:bg-danger-700' : 'bg-success-600 hover:bg-success-700'
            }`}
          >
            {running ? 'Stop' : 'Start'}
          </button>
        </div>
        <p className="text-xs text-gray-500">Enter 'webcam', an uploaded video file path, or an RTSP stream URL.</p>
      </div>

      {/* 2. Classroom Context */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h2 className="text-lg font-semibold mb-4 text-gray-900">2. Classroom Context</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {['LECTURE', 'EXAM', 'AUTHORIZED_PHONE_ACTIVITY', 'BREAK'].map((mode) => (
            <button
              key={mode}
              onClick={() => handleContext(mode)}
              className={`p-3 rounded-lg text-sm font-medium transition cursor-pointer ${
                ctx === mode ? 'bg-primary-600 text-white shadow-md' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {mode.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Context affects anomaly scoring multiplier. EXAM = strictest, BREAK = most relaxed.
        </p>
      </div>

      {/* 3. Model Information */}
      {modelInfo && (
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">3. Model Information</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Model Path</span>
              <span className="font-medium">{modelInfo.model_path}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Device</span>
              <span className="font-medium">{modelInfo.device}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Confidence</span>
              <span className="font-medium">{modelInfo.confidence_threshold}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">IoU</span>
              <span className="font-medium">{modelInfo.iou_threshold}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Image Size</span>
              <span className="font-medium">{modelInfo.image_size}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Loaded</span>
              <span className="font-medium">{modelInfo.model_loaded ? '✅ Yes' : '❌ No'}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
