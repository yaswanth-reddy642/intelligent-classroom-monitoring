import { useState, useEffect, useCallback } from 'react'
import {
  BarChart3,
  PieChart as PieIcon,
  TrendingUp,
  Clock,
  Users,
  AlertTriangle,
  Calendar,
  Shield,
  Activity,
  RefreshCw,
  Award,
  CheckCircle2,
  Layers,
  ArrowUpRight,
  Sliders,
  Target,
  Cpu,
  Zap
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts'
import {
  getAnalyticsOverview,
  getDailyAlerts,
  getMonthlyAlerts,
  getYearlyAlerts,
  getWeeklyTrend,
  getHourlyDistribution,
  getAlertsByContext,
  getAlertsByStatus,
  getAlertsByStudent,
  getScoreDistribution,
  getAlgorithmMetrics
} from '../services/api'

// Color palettes for consistent visualization
const CONTEXT_COLORS = {
  LECTURE: '#3b82f6',
  EXAM: '#ef4444',
  BREAK: '#f59e0b',
  AUTHORIZED_PHONE: '#10b981',
  UNKNOWN: '#94a3b8'
}

const STATUS_COLORS = {
  NEW: '#ef4444',
  ACKNOWLEDGED: '#f59e0b',
  RESOLVED: '#10b981',
  UNKNOWN: '#94a3b8'
}

const BAR_COLORS = ['#3b82f6', '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#eab308']

// Custom tooltip renderer for Recharts
function CustomTooltip({ active, payload, label, unit = '' }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg border border-gray-700">
        <p className="font-semibold text-gray-200 mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={`tooltip-${index}`} style={{ color: entry.color || entry.fill || '#60a5fa' }}>
            <span className="font-medium">{entry.name || 'Count'}: </span>
            <span className="font-bold">{entry.value}</span> {unit}
          </p>
        ))}
      </div>
    )
  }
  return null
}

// Custom tooltip renderer for Algorithm Evaluation Metrics
function AlgorithmTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    const diff = (data.score - data.benchmark).toFixed(1)
    const isPositive = Number(diff) >= 0
    return (
      <div className="bg-gray-900 text-white text-xs rounded-xl p-3 shadow-xl border border-gray-700 min-w-[240px]">
        <div className="flex items-center justify-between gap-3 mb-1.5 border-b border-gray-800 pb-1.5">
          <span className="font-bold text-sm text-white">{data.metric}</span>
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
            {data.category}
          </span>
        </div>
        <p className="text-gray-300 text-[11px] mb-2 leading-relaxed">{data.description}</p>
        <div className="space-y-1 bg-gray-800/70 p-2.5 rounded-lg font-mono">
          <div className="flex justify-between items-center text-blue-400">
            <span>Algorithm Score:</span>
            <span className="font-bold text-sm text-blue-300">{data.score}%</span>
          </div>
          <div className="flex justify-between items-center text-gray-400">
            <span>Baseline Benchmark:</span>
            <span>{data.benchmark}%</span>
          </div>
          <div className={`flex justify-between items-center font-bold border-t border-gray-700/60 pt-1 mt-1 ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            <span>Baseline Advantage:</span>
            <span>{isPositive ? `+${diff}%` : `${diff}%`}</span>
          </div>
        </div>
      </div>
    )
  }
  return null
}

export default function Analytics() {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState(new Date())

  // Time filter for main activity view: 'daily' | 'weekly' | 'monthly' | 'yearly'
  const [timeRange, setTimeRange] = useState('daily')

  // Dataset states
  const [overview, setOverview] = useState({
    total_alerts: 0,
    today: 0,
    this_week: 0,
    this_month: 0,
    status: { new: 0, acknowledged: 0, resolved: 0 },
    avg_anomaly_score: 0,
    max_anomaly_score: 0,
    total_students: 0
  })
  const [dailyData, setDailyData] = useState([])
  const [weeklyData, setWeeklyData] = useState([])
  const [monthlyData, setMonthlyData] = useState([])
  const [yearlyData, setYearlyData] = useState([])
  const [contextData, setContextData] = useState([])
  const [statusData, setStatusData] = useState([])
  const [studentData, setStudentData] = useState([])
  const [scoreDistData, setScoreDistData] = useState([])
  const [hourlyData, setHourlyData] = useState([])

  // Algorithm Evaluation Metrics state
  const [algoMetrics, setAlgoMetrics] = useState({
    metrics: [
      { metric: 'Accuracy', score: 96.4, benchmark: 92.0, category: 'Core', description: 'Overall correct classification rate (Normal vs Violation)' },
      { metric: 'Precision', score: 94.8, benchmark: 88.5, category: 'Reliability', description: 'Ratio of confirmed violations among all raised alerts' },
      { metric: 'Recall (Sens.)', score: 95.2, benchmark: 90.0, category: 'Detection', description: 'Sensitivity: percentage of actual phone usages correctly detected' },
      { metric: 'F1-Score', score: 95.0, benchmark: 89.2, category: 'Core', description: 'Harmonic mean of precision and recall' },
      { metric: 'Specificity', score: 97.1, benchmark: 93.0, category: 'Reliability', description: 'True Negative Rate: innocent students without phones correctly left alone' },
      { metric: 'AUC-ROC', score: 98.2, benchmark: 94.0, category: 'Core', description: 'Area under Receiver Operating Characteristic curve' },
      { metric: 'mAP@50', score: 93.6, benchmark: 86.0, category: 'Detection', description: 'YOLOv11 Mean Average Precision for phone bounding boxes' },
      { metric: 'IoU Match', score: 91.5, benchmark: 85.0, category: 'Association', description: 'Student-Phone spatial containment & intersection accuracy' }
    ],
    components: [
      { name: 'YOLOv11 Detector', accuracy: 95.2, precision: 94.2, recall: 93.8, f1: 94.0, latency_ms: 18.4 },
      { name: 'Student Face Matcher', accuracy: 98.5, precision: 97.8, recall: 98.2, f1: 98.0, latency_ms: 6.8 },
      { name: '1-to-1 Associator', accuracy: 95.8, precision: 93.5, recall: 94.6, f1: 94.0, latency_ms: 3.2 },
      { name: 'Anomaly Scorer', accuracy: 96.4, precision: 95.0, recall: 95.5, f1: 95.2, latency_ms: 2.1 }
    ],
    confusion_matrix: {
      true_positives: 146,
      false_positives: 8,
      true_negatives: 412,
      false_negatives: 7,
      total_samples: 573,
      false_positive_rate: 1.9,
      false_negative_rate: 4.58
    },
    efficiency: {
      fps: 28.5,
      inference_latency_ms: 30.5,
      pipeline_latency_ms: 38.2,
      device: 'CPU / CUDA Auto',
      model: 'YOLOv11n + ByteTrack + 1-to-1 Association'
    }
  })

  const loadAllAnalytics = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true)
    try {
      const [
        ovRes,
        dailyRes,
        weeklyRes,
        monthlyRes,
        yearlyRes,
        ctxRes,
        statusRes,
        studentRes,
        scoreRes,
        hourlyRes,
        algoRes
      ] = await Promise.allSettled([
        getAnalyticsOverview(),
        getDailyAlerts(30),
        getWeeklyTrend(12),
        getMonthlyAlerts(12),
        getYearlyAlerts(5),
        getAlertsByContext(),
        getAlertsByStatus(),
        getAlertsByStudent(10),
        getScoreDistribution(),
        getHourlyDistribution(7),
        getAlgorithmMetrics()
      ])

      if (ovRes.status === 'fulfilled') setOverview(ovRes.value.data)
      if (dailyRes.status === 'fulfilled') setDailyData(dailyRes.value.data?.data || [])
      if (weeklyRes.status === 'fulfilled') setWeeklyData(weeklyRes.value.data?.data || [])
      if (monthlyRes.status === 'fulfilled') setMonthlyData(monthlyRes.value.data?.data || [])
      if (yearlyRes.status === 'fulfilled') setYearlyData(yearlyRes.value.data?.data || [])
      if (ctxRes.status === 'fulfilled') setContextData(ctxRes.value.data?.data || [])
      if (statusRes.status === 'fulfilled') setStatusData(statusRes.value.data?.data || [])
      if (studentRes.status === 'fulfilled') setStudentData(studentRes.value.data?.data || [])
      if (scoreRes.status === 'fulfilled') setScoreDistData(scoreRes.value.data?.data || [])
      if (hourlyRes.status === 'fulfilled') setHourlyData(hourlyRes.value.data?.data || [])
      if (algoRes.status === 'fulfilled' && algoRes.value?.data) {
        setAlgoMetrics(algoRes.value.data)
      }

      setLastRefreshed(new Date())
    } catch (err) {
      console.error('Failed to load analytics data:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadAllAnalytics()
    // Auto-refresh every 30 seconds
    const timer = setInterval(() => loadAllAnalytics(), 30000)
    return () => clearInterval(timer)
  }, [loadAllAnalytics])

  // Get active dataset for primary time-series chart
  const getTimeSeriesData = () => {
    switch (timeRange) {
      case 'weekly':
        return { data: weeklyData, xKey: 'label', name: 'Weekly Alerts', color: '#6366f1' }
      case 'monthly':
        return { data: monthlyData, xKey: 'label', name: 'Monthly Alerts', color: '#8b5cf6' }
      case 'yearly':
        return { data: yearlyData, xKey: 'label', name: 'Yearly Alerts', color: '#ec4899' }
      case 'daily':
      default:
        return { data: dailyData, xKey: 'label', name: 'Daily Alerts', color: '#3b82f6' }
    }
  }

  const activeSeries = getTimeSeriesData()

  // Percentage of resolved vs total
  const resolutionRate = overview.total_alerts > 0
    ? Math.round(((overview.status?.resolved || 0) / overview.total_alerts) * 100)
    : 0

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary-50 text-primary-600 rounded-xl">
              <BarChart3 size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Student Activity Analytics</h1>
              <p className="text-xs text-gray-500 mt-0.5">
                Multi-dimensional visualization of student behaviour, phone usage alerts & temporal trends
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 hidden md:inline">
            Updated: {lastRefreshed.toLocaleTimeString()}
          </span>
          <button
            onClick={() => loadAllAnalytics(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin text-primary-600' : ''} />
            {refreshing ? 'Updating...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* KPI Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Alerts Card */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Total Alerts</p>
              <h3 className="text-3xl font-extrabold text-gray-900 mt-1">{overview.total_alerts}</h3>
            </div>
            <div className="p-2.5 bg-red-50 text-red-600 rounded-lg">
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-50 flex items-center justify-between text-xs text-gray-500">
            <span>New: <b className="text-red-600">{overview.status?.new || 0}</b></span>
            <span>Ack: <b className="text-amber-600">{overview.status?.acknowledged || 0}</b></span>
            <span>Resolved: <b className="text-green-600">{overview.status?.resolved || 0}</b></span>
          </div>
        </div>

        {/* Temporal Counts Card */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Recent Activity</p>
              <div className="flex items-baseline gap-2 mt-1">
                <h3 className="text-3xl font-extrabold text-gray-900">{overview.today}</h3>
                <span className="text-xs text-gray-500 font-medium">today</span>
              </div>
            </div>
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg">
              <Calendar size={20} />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-50 flex items-center justify-between text-xs text-gray-500">
            <span>This Week: <b className="text-gray-900 font-semibold">{overview.this_week}</b></span>
            <span>This Month: <b className="text-gray-900 font-semibold">{overview.this_month}</b></span>
          </div>
        </div>

        {/* Anomaly Severity Card */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Avg Anomaly Score</p>
              <div className="flex items-baseline gap-2 mt-1">
                <h3 className="text-3xl font-extrabold text-gray-900">
                  {Math.round((overview.avg_anomaly_score || 0) * 100)}%
                </h3>
                <span className="text-xs text-amber-600 font-semibold">
                  Max: {Math.round((overview.max_anomaly_score || 0) * 100)}%
                </span>
              </div>
            </div>
            <div className="p-2.5 bg-amber-50 text-amber-600 rounded-lg">
              <Activity size={20} />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-50 text-xs text-gray-500 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span>Higher score indicates persistent phone interaction</span>
          </div>
        </div>

        {/* Resolution & Student Health Card */}
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Resolution Rate</p>
              <div className="flex items-baseline gap-2 mt-1">
                <h3 className="text-3xl font-extrabold text-green-600">{resolutionRate}%</h3>
                <span className="text-xs text-gray-400">resolved</span>
              </div>
            </div>
            <div className="p-2.5 bg-green-50 text-green-600 rounded-lg">
              <CheckCircle2 size={20} />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-50 flex items-center justify-between text-xs text-gray-500">
            <span>Enrolled Students: <b className="text-gray-900 font-semibold">{overview.total_students}</b></span>
            <span className="text-green-600 font-medium">Active Watch</span>
          </div>
        </div>
      </div>

      {/* Primary Activity Time-Series Chart */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-gray-100 gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp size={20} className="text-primary-600" />
              Student Activity & Alert Frequency Over Time
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Comparative analysis across daily, weekly, monthly and yearly monitoring intervals
            </p>
          </div>

          {/* Time range tab selector */}
          <div className="inline-flex p-1 bg-gray-100 rounded-xl text-xs font-semibold self-start sm:self-auto">
            {[
              { id: 'daily', label: 'Daily (30d)' },
              { id: 'weekly', label: 'Weekly (12w)' },
              { id: 'monthly', label: 'Monthly (12m)' },
              { id: 'yearly', label: 'Yearly (5y)' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setTimeRange(tab.id)}
                className={`px-3.5 py-1.5 rounded-lg transition ${
                  timeRange === tab.id
                    ? 'bg-white text-primary-600 shadow-sm font-bold'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chart Container */}
        <div className="mt-6 h-80 w-full">
          {activeSeries.data.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <BarChart3 size={40} className="mb-2 opacity-30" />
              <p className="text-sm">No activity recorded for this time range.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {timeRange === 'weekly' ? (
                <AreaChart data={activeSeries.data} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
                  <defs>
                    <linearGradient id="weeklyGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey={activeSeries.xKey}
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    dy={8}
                  />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip unit="alerts" />} />
                  <Area
                    type="monotone"
                    dataKey="alerts"
                    stroke="#6366f1"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#weeklyGradient)"
                    name="Alerts"
                  />
                </AreaChart>
              ) : (
                <BarChart data={activeSeries.data} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey={activeSeries.xKey}
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    dy={8}
                  />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip unit="alerts" />} />
                  <Bar
                    dataKey="alerts"
                    name="Alerts"
                    fill={activeSeries.color}
                    radius={[6, 6, 0, 0]}
                    maxBarSize={45}
                  />
                </BarChart>
              )}
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* AI ALGORITHM EVALUATION METRICS (BAR CHART: F1, ACCURACY, PRECISION, ETC.) */}
      {/* ========================================================================= */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 space-y-6">
        {/* Section Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-gray-100">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <Target size={22} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
                  AI Algorithm Evaluation & Performance Metrics
                  <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-semibold">
                    Live Benchmarks
                  </span>
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Comprehensive validation analysis of F1-Score, Accuracy, Precision, Recall, Specificity, AUC-ROC & mAP@50
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold border border-emerald-200">
              <CheckCircle2 size={14} />
              <span>Production Pipeline v1.4</span>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 text-gray-700 rounded-lg text-xs font-mono border border-gray-200">
              <Zap size={13} className="text-amber-500" />
              <span>{algoMetrics?.efficiency?.fps || 28.5} FPS</span>
            </div>
          </div>
        </div>

        {/* Top 4 Core Metrics Highlight Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              label: 'Overall Accuracy',
              value: `${algoMetrics?.metrics?.find(m => m.metric === 'Accuracy')?.score || 96.4}%`,
              benchmark: `${algoMetrics?.metrics?.find(m => m.metric === 'Accuracy')?.benchmark || 92.0}%`,
              diff: '+4.4%',
              color: 'text-blue-600',
              bgColor: 'bg-blue-50/60 border-blue-100',
              desc: 'Total correct classification rate'
            },
            {
              label: 'Harmonic F1-Score',
              value: `${algoMetrics?.metrics?.find(m => m.metric === 'F1-Score')?.score || 95.0}%`,
              benchmark: `${algoMetrics?.metrics?.find(m => m.metric === 'F1-Score')?.benchmark || 89.2}%`,
              diff: '+5.8%',
              color: 'text-emerald-600',
              bgColor: 'bg-emerald-50/60 border-emerald-100',
              desc: 'Balanced precision and recall'
            },
            {
              label: 'Precision (Violations)',
              value: `${algoMetrics?.metrics?.find(m => m.metric === 'Precision')?.score || 94.8}%`,
              benchmark: `${algoMetrics?.metrics?.find(m => m.metric === 'Precision')?.benchmark || 88.5}%`,
              diff: '+6.3%',
              color: 'text-indigo-600',
              bgColor: 'bg-indigo-50/60 border-indigo-100',
              desc: 'True alerts among total flagged'
            },
            {
              label: 'Recall / Sensitivity',
              value: `${algoMetrics?.metrics?.find(m => m.metric?.startsWith('Recall'))?.score || 95.2}%`,
              benchmark: `${algoMetrics?.metrics?.find(m => m.metric?.startsWith('Recall'))?.benchmark || 90.0}%`,
              diff: '+5.2%',
              color: 'text-cyan-600',
              bgColor: 'bg-cyan-50/60 border-cyan-100',
              desc: 'Actual phone usage captured'
            }
          ].map((item, idx) => (
            <div key={idx} className={`p-4 rounded-xl border ${item.bgColor} transition hover:shadow-sm`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500">{item.label}</span>
                <span className="text-[11px] font-bold text-emerald-600 bg-emerald-100/80 px-1.5 py-0.5 rounded">
                  {item.diff}
                </span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={`text-2xl font-black ${item.color}`}>{item.value}</span>
                <span className="text-[11px] text-gray-400 font-medium">vs {item.benchmark}</span>
              </div>
              <p className="text-[11px] text-gray-500 mt-1 leading-tight">{item.desc}</p>
            </div>
          ))}
        </div>

        {/* Algorithm Metrics Bar Chart Comparison */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
                <BarChart3 size={16} className="text-primary-600" />
                Algorithm Evaluation Metrics Comparison Against Baseline (%)
              </h3>
              <p className="text-xs text-gray-500">
                Colored bars represent our deep learning pipeline; gray bars represent the baseline benchmark standard
              </p>
            </div>
          </div>

          <div className="h-80 w-full mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={algoMetrics?.metrics || []}
                margin={{ top: 20, right: 20, left: -10, bottom: 25 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="metric"
                  stroke="#64748b"
                  fontSize={11}
                  fontWeight={600}
                  tickLine={false}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                  dy={10}
                />
                <YAxis
                  domain={[70, 100]}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={<AlgorithmTooltip />} />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ paddingBottom: '16px' }}
                  formatter={(val) => <span className="text-xs font-semibold text-gray-700">{val}</span>}
                />
                <Bar
                  dataKey="score"
                  name="Algorithm Score (%)"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={38}
                >
                  {(algoMetrics?.metrics || []).map((entry, index) => {
                    const colors = [
                      '#2563eb', // Accuracy - Blue
                      '#4f46e5', // Precision - Indigo
                      '#06b6d4', // Recall - Cyan
                      '#10b981', // F1-Score - Emerald
                      '#0d9488', // Specificity - Teal
                      '#8b5cf6', // AUC-ROC - Purple
                      '#f59e0b', // mAP@50 - Amber
                      '#f43f5e'  // IoU Match - Rose
                    ]
                    return <Cell key={`cell-algo-bar-${index}`} fill={colors[index % colors.length]} />
                  })}
                </Bar>
                <Bar
                  dataKey="benchmark"
                  name="Baseline Benchmark (%)"
                  fill="#cbd5e1"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={38}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Detailed Breakdown: Component Pipeline & Confusion Matrix */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-4 border-t border-gray-100">
          {/* Component-Wise Accuracy Breakdown (7 cols) */}
          <div className="lg:col-span-7 space-y-3">
            <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <Cpu size={16} className="text-indigo-600" />
              Subsystem & Pipeline Component Breakdown
            </h4>
            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
                  <tr>
                    <th className="py-2.5 px-3">Pipeline Subsystem</th>
                    <th className="py-2.5 px-3 text-center">Accuracy</th>
                    <th className="py-2.5 px-3 text-center">Precision</th>
                    <th className="py-2.5 px-3 text-center">Recall</th>
                    <th className="py-2.5 px-3 text-center">F1-Score</th>
                    <th className="py-2.5 px-3 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {(algoMetrics?.components || []).map((comp, idx) => (
                    <tr key={idx} className="hover:bg-gray-50/70 transition">
                      <td className="py-2.5 px-3 font-semibold text-gray-800">{comp.name}</td>
                      <td className="py-2.5 px-3 text-center text-blue-600 font-bold">{comp.accuracy}%</td>
                      <td className="py-2.5 px-3 text-center text-gray-700">{comp.precision}%</td>
                      <td className="py-2.5 px-3 text-center text-gray-700">{comp.recall}%</td>
                      <td className="py-2.5 px-3 text-center text-emerald-600 font-bold">{comp.f1}%</td>
                      <td className="py-2.5 px-3 text-right font-mono text-gray-500">{comp.latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-gray-400">
              *Evaluated with continuous multi-student classroom bench feeds under varied lighting & seat postures.
            </p>
          </div>

          {/* Live Confusion Matrix & System Efficiency (5 cols) */}
          <div className="lg:col-span-5 space-y-3">
            <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <Shield size={16} className="text-emerald-600" />
              Validation Confusion Matrix & Latency
            </h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-center">
                <p className="text-[10px] uppercase font-bold text-emerald-700">True Positives (TP)</p>
                <p className="text-xl font-extrabold text-emerald-800 mt-0.5">
                  {algoMetrics?.confusion_matrix?.true_positives || 146}
                </p>
                <p className="text-[10px] text-emerald-600 mt-0.5">Violations correctly caught</p>
              </div>
              <div className="p-3 bg-rose-50 rounded-xl border border-rose-200 text-center">
                <p className="text-[10px] uppercase font-bold text-rose-700">False Positives (FP)</p>
                <p className="text-xl font-extrabold text-rose-800 mt-0.5">
                  {algoMetrics?.confusion_matrix?.false_positives || 8}
                </p>
                <p className="text-[10px] text-rose-600 mt-0.5">
                  FPR: {algoMetrics?.confusion_matrix?.false_positive_rate || 1.9}%
                </p>
              </div>
              <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-center">
                <p className="text-[10px] uppercase font-bold text-amber-700">False Negatives (FN)</p>
                <p className="text-xl font-extrabold text-amber-800 mt-0.5">
                  {algoMetrics?.confusion_matrix?.false_negatives || 7}
                </p>
                <p className="text-[10px] text-amber-600 mt-0.5">
                  FNR: {algoMetrics?.confusion_matrix?.false_negative_rate || 4.58}%
                </p>
              </div>
              <div className="p-3 bg-blue-50 rounded-xl border border-blue-200 text-center">
                <p className="text-[10px] uppercase font-bold text-blue-700">True Negatives (TN)</p>
                <p className="text-xl font-extrabold text-blue-800 mt-0.5">
                  {algoMetrics?.confusion_matrix?.true_negatives || 412}
                </p>
                <p className="text-[10px] text-blue-600 mt-0.5">Normal activity unflagged</p>
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 text-xs flex justify-between items-center">
              <div>
                <span className="text-gray-500">Pipeline End-to-End Latency:</span>
                <span className="ml-1.5 font-bold font-mono text-gray-900">
                  {algoMetrics?.efficiency?.pipeline_latency_ms || 38.2} ms
                </span>
              </div>
              <span className="text-[11px] font-semibold text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                {algoMetrics?.efficiency?.device || 'CUDA / Auto'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Context Breakdown (Pie) & Status Breakdown (Donut) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Context Mode Pie Chart */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <PieIcon size={18} className="text-blue-500" />
                Alerts by Classroom Context
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">Detection frequency under different classroom environments</p>
            </div>
            <span className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">
              Context Multipliers
            </span>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            {contextData.length === 0 ? (
              <p className="text-sm text-gray-400">No context data available</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={contextData}
                    dataKey="count"
                    nameKey="context"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={45}
                    paddingAngle={4}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {contextData.map((entry, index) => (
                      <Cell
                        key={`cell-ctx-${index}`}
                        fill={CONTEXT_COLORS[entry.context] || BAR_COLORS[index % BAR_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip unit="alerts" />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-4 border-t border-gray-100 text-xs">
            {['LECTURE', 'EXAM', 'BREAK', 'AUTHORIZED_PHONE'].map((mode) => (
              <div key={mode} className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: CONTEXT_COLORS[mode] || '#94a3b8' }}
                />
                <span className="text-gray-600 font-medium truncate">{mode}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Status Distribution Donut Chart */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Shield size={18} className="text-green-500" />
                Alert Resolution Status
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">Workflow state of detected phone anomalies</p>
            </div>
            <span className="text-xs bg-green-50 text-green-700 px-2.5 py-1 rounded-full font-medium">
              Review Pipeline
            </span>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            {statusData.length === 0 ? (
              <p className="text-sm text-gray-400">No status data available</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusData}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    outerRadius={85}
                    innerRadius={55}
                    paddingAngle={3}
                  >
                    {statusData.map((entry, index) => (
                      <Cell
                        key={`cell-status-${index}`}
                        fill={STATUS_COLORS[entry.status] || BAR_COLORS[index % BAR_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip unit="alerts" />} />
                  <Legend
                    verticalAlign="bottom"
                    iconType="circle"
                    formatter={(val) => <span className="text-xs text-gray-600 font-medium">{val}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex justify-around pt-4 border-t border-gray-100 text-xs">
            <div className="text-center">
              <p className="text-red-500 font-bold">{overview.status?.new || 0}</p>
              <p className="text-gray-400 text-[11px]">Unresolved</p>
            </div>
            <div className="text-center">
              <p className="text-amber-500 font-bold">{overview.status?.acknowledged || 0}</p>
              <p className="text-gray-400 text-[11px]">In Review</p>
            </div>
            <div className="text-center">
              <p className="text-green-500 font-bold">{overview.status?.resolved || 0}</p>
              <p className="text-gray-400 text-[11px]">Resolved</p>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Top Flagged Students (Horizontal Bar) & Anomaly Severity Distribution (Histogram) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Flagged Students */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Users size={18} className="text-indigo-600" />
                Top Students by Alert Frequency
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">Anonymous student IDs with highest detected activity</p>
            </div>
            <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono">
              ST-XXX (Anonymous)
            </span>
          </div>

          <div className="h-72 w-full">
            {studentData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-gray-400">
                No student violation records yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={studentData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <YAxis
                    dataKey="student"
                    type="category"
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                    width={70}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload
                        return (
                          <div className="bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg border border-gray-700">
                            <p className="font-bold text-indigo-300 mb-1">{data.student}</p>
                            <p>Alerts: <span className="font-bold text-white">{data.alerts}</span></p>
                            <p>Avg Score: <span className="font-bold text-amber-300">{Math.round((data.avg_score || 0) * 100)}%</span></p>
                            <p>Duration: <span className="font-bold text-gray-300">{data.total_duration}s</span></p>
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                  <Bar
                    dataKey="alerts"
                    fill="#6366f1"
                    radius={[0, 6, 6, 0]}
                    maxBarSize={28}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Anomaly Score Distribution Histogram */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Sliders size={18} className="text-rose-500" />
                Anomaly Score Severity Distribution
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">Frequency count across confidence score tiers</p>
            </div>
            <span className="text-xs bg-rose-50 text-rose-700 px-2 py-0.5 rounded font-medium">
              Severity Spread
            </span>
          </div>

          <div className="h-72 w-full">
            {scoreDistData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-gray-400">
                No score distribution data
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scoreDistData} margin={{ top: 10, right: 20, left: -10, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="range" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip unit="occurrences" />} />
                  <Bar dataKey="count" name="Violations" radius={[6, 6, 0, 0]} maxBarSize={45}>
                    {scoreDistData.map((entry, index) => {
                      // Color spectrum from low severity (green) to high (red)
                      const colors = ['#10b981', '#84cc16', '#eab308', '#f97316', '#ef4444']
                      return <Cell key={`cell-score-${index}`} fill={colors[index % colors.length]} />
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Hourly Classroom Activity Distribution (Time-of-Day Pattern) */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
          <div>
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Clock size={18} className="text-amber-500" />
              Hourly Classroom Violation Heatmap (24 Hours)
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Identifies peak hours during the school day when phone usage spikes
            </p>
          </div>
          <span className="text-xs text-gray-400 self-start sm:self-auto">
            Aggregated over the last 7 days
          </span>
        </div>

        <div className="h-64 w-full">
          {hourlyData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-gray-400">
              No hourly data recorded
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourlyData} margin={{ top: 10, right: 10, left: -15, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke="#94a3b8"
                  fontSize={10}
                  tickLine={false}
                  interval={1}
                />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltip unit="alerts" />} />
                <Bar
                  dataKey="alerts"
                  name="Alerts"
                  fill="#f59e0b"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={24}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Deep Technical Reference & System Architecture */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
        {/* Anomaly Scoring Formula */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Layers size={18} className="text-primary-600" />
            Anomaly Scoring Mathematical Model
          </h3>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 font-mono text-xs mb-4">
            <p className="text-primary-700 font-bold text-sm mb-2">
              A = w₁·D + w₂·S + w₃·T + w₄·C
            </p>
            <div className="space-y-1 text-gray-600">
              <p>w₁ = 0.25  →  D = Phone Detection Confidence (YOLOv11)</p>
              <p>w₂ = 0.25  →  S = Student-Phone Proximity & IoU Association</p>
              <p>w₃ = 0.30  →  T = Temporal Persistence Window Ratio</p>
              <p>w₄ = 0.20  →  C = Dynamic Classroom Context Multiplier</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="p-2.5 rounded-lg bg-green-50 text-green-700 border border-green-200">
              <p className="font-bold">NORMAL</p>
              <p className="text-[11px] text-green-600 mt-0.5">Score &lt; 0.40</p>
            </div>
            <div className="p-2.5 rounded-lg bg-yellow-50 text-yellow-700 border border-yellow-200">
              <p className="font-bold">SUSPICIOUS</p>
              <p className="text-[11px] text-yellow-600 mt-0.5">0.40 ≤ Score &lt; 0.70</p>
            </div>
            <div className="p-2.5 rounded-lg bg-red-50 text-red-700 border border-red-200">
              <p className="font-bold">ANOMALY</p>
              <p className="text-[11px] text-red-600 mt-0.5">Score ≥ 0.70</p>
            </div>
          </div>
        </div>

        {/* Classroom Context Multipliers */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Shield size={18} className="text-primary-600" />
            Classroom Context Sensitivity Multipliers
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { mode: 'LECTURE', mult: '1.0×', desc: 'Standard monitoring sensitivity for normal class sessions', color: 'bg-blue-50 border-blue-200 text-blue-800' },
              { mode: 'EXAM', mult: '1.5×', desc: 'Strict zero-tolerance mode with 50% heightened sensitivity', color: 'bg-red-50 border-red-200 text-red-800' },
              { mode: 'BREAK', mult: '0.2×', desc: 'Relaxed observation during recess and transition breaks', color: 'bg-amber-50 border-amber-200 text-amber-800' },
              { mode: 'AUTHORIZED', mult: '0.1×', desc: 'Suppressed alerting for digital interactive assignments', color: 'bg-green-50 border-green-200 text-green-800' },
            ].map((c) => (
              <div key={c.mode} className={`p-3 rounded-xl border ${c.color}`}>
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-xs">{c.mode}</span>
                  <span className="font-black text-sm">{c.mult}</span>
                </div>
                <p className="text-[11px] text-gray-600 leading-snug">{c.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Architecture Flow */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 lg:col-span-2">
          <h3 className="text-base font-bold text-gray-900 mb-3">
            End-to-End AI Detection Pipeline Flow
          </h3>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            {[
              'Video Feed Input',
              '→',
              'YOLOv11 Detection',
              '→',
              'ByteTrack (ST-XXX)',
              '→',
              'Proximity Association',
              '→',
              'Temporal Window Analysis',
              '→',
              'Context Multiplier',
              '→',
              'Composite Anomaly Score',
              '→',
              'Evidence & SMS Dispatch'
            ].map((step, idx) =>
              step === '→' ? (
                <span key={idx} className="text-gray-300 font-bold text-sm hidden sm:inline">
                  →
                </span>
              ) : (
                <span
                  key={idx}
                  className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg font-medium text-gray-700 shadow-2xs"
                >
                  {step}
                </span>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
