export default function About() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">About</h1>

      <div className="bg-white rounded-xl shadow-sm p-8">
        <h2 className="text-xl font-bold text-primary-700 mb-2">Intelligent Classroom Monitoring and Anomaly Detection</h2>
        <p className="text-sm text-gray-500 mb-6">Using YOLOv11 — B.Tech Major Project</p>

        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-green-800 mb-1">🔒 Privacy Notice</h3>
          <p className="text-sm text-green-700">
            This system performs automated classroom video analysis for research and monitoring purposes.
            It does <strong>not</strong> perform facial identity recognition. All students are tracked
            using anonymous identifiers (ST-001, ST-002, etc.).
          </p>
        </div>

        <div className="space-y-6 text-sm text-gray-700">
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Project Objective</h3>
            <p>Build a complete, modular, production-style intelligent classroom monitoring system that analyzes classroom video in real time using YOLOv11-based object detection, multi-object tracking, student-phone association, temporal behavior analysis, context-aware anomaly detection, and real-time teacher alerts.</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Technology Stack</h3>
            <div className="grid grid-cols-2 gap-3">
              <div><span className="text-gray-400">Detection: </span>YOLOv11 (Ultralytics)</div>
              <div><span className="text-gray-400">Tracking: </span>ByteTrack (supervision)</div>
              <div><span className="text-gray-400">Identity: </span>Anonymous IDs (ST-XXX)</div>
              <div><span className="text-gray-400">Backend: </span>FastAPI + MongoDB</div>
              <div><span className="text-gray-400">Frontend: </span>React + Vite + Tailwind CSS</div>
              <div><span className="text-gray-400">Anomaly: </span>Weighted multi-factor scoring</div>
            </div>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Research Extensions</h3>
            <div className="grid grid-cols-2 gap-3">
              <div><span className="text-gray-400">VAD Baseline: </span>CNN-LSTM</div>
              <div><span className="text-gray-400">Proposed: </span>Temporal Transformer</div>
              <div><span className="text-gray-400">Localization: </span>Temporal segments</div>
              <div><span className="text-gray-400">Explainability: </span>VLM (optional)</div>
            </div>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Anomaly Scoring Formula</h3>
            <div className="bg-gray-50 rounded-lg p-4 font-mono">
              <p className="text-primary-700 font-bold">A = w₁·D + w₂·S + w₃·T + w₄·C</p>
              <p className="text-xs text-gray-500 mt-2">Where D=phone detection confidence, S=student-phone association, T=temporal persistence, C=context multiplier</p>
            </div>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Key Features</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>Real-time YOLOv11 object detection (students + phones)</li>
              <li>ByteTrack multi-object tracking with anonymous persistent IDs</li>
              <li>Spatial student-phone association engine</li>
              <li>Sliding-window temporal behavior analysis</li>
              <li>Context-aware anomaly detection (LECTURE/EXAM/BREAK)</li>
              <li>Cooldown-based alert system with evidence capture</li>
              <li>CNN-LSTM and Temporal Transformer for learned anomaly detection</li>
              <li>WebSocket live video streaming to dashboard</li>
              <li>No facial identity recognition — privacy by design</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
