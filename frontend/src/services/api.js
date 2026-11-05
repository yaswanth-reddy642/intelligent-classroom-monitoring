import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Detection
export const startDetection = (source) => api.post('/detection/start', { source })
export const stopDetection = () => api.post('/detection/stop')
export const getDetectionStatus = () => api.get('/detection/status')
export const getCurrentDetections = () => api.get('/detection/current')
export const getAnnotatedFrame = () => api.get('/detection/frame')
export const uploadVideo = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/detection/upload-video', fd, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000 })
}

// Alerts
export const getAlerts = (params) => api.get('/alerts', { params })
export const getAlertCounts = () => api.get('/alerts/count')
export const updateAlertStatus = (id, status) => api.patch(`/alerts/${id}/status`, { status })
export const createTestAlert = (data) => api.post('/alerts/test', data)
export const sendAlertSms = (alertId) => api.post(`/alerts/${alertId}/send-sms`)
export const deleteAlert = (alertId) => api.delete(`/alerts/${alertId}`)

// Students
export const getStudents = () => api.get('/students')
export const createStudent = (data) => api.post('/students', data)
export const updateStudent = (rollNumber, data) => api.put(`/students/${rollNumber}`, data)
export const deleteStudent = (rollNumber) => api.delete(`/students/${rollNumber}`)
export const getPrivacyNotice = () => api.get('/students/privacy')
export const uploadStudentsCsv = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/students/upload-csv', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}
export const getSampleCsvUrl = () => '/api/students/sample-csv'

// Statistics
export const getDashboardStats = () => api.get('/stats/dashboard')
export const getLiveStats = () => api.get('/stats/live')

// Settings
export const getContext = () => api.get('/settings/context')
export const setContext = (mode) => api.post('/settings/context', { mode })
export const getModelInfo = () => api.get('/settings/model-info')
export const getSmsSettings = () => api.get('/settings/sms')
export const saveSmsSettings = (data) => api.post('/settings/sms', data, { timeout: 20000 })
export const testSmsDelivery = (data) => api.post('/settings/sms/test', data, { timeout: 25000 })

// Health
export const healthCheck = () => api.get('/health')

// Admin
export const adminLogin = (data) => api.post('/auth/admin-login', data)
export const adminForgotPassword = (data) => api.post('/auth/admin-forgot-password', data)
export const adminResetPassword = (data) => api.post('/auth/admin-reset-password', data)
export const adminGetStats = () => api.get('/auth/admin/stats')
export const adminRegisterTeacher = (data) => api.post('/auth/admin/register-teacher', data)
export const adminGetTeachers = () => api.get('/auth/admin/teachers')
export const adminDeleteTeacher = (id) => api.delete(`/auth/admin/teachers/${id}`)

// Analytics
export const getAnalyticsOverview = () => api.get('/analytics/overview')
export const getDailyAlerts = (days = 30) => api.get(`/analytics/daily?days=${days}`)
export const getMonthlyAlerts = (months = 12) => api.get(`/analytics/monthly?months=${months}`)
export const getYearlyAlerts = (years = 5) => api.get(`/analytics/yearly?years=${years}`)
export const getWeeklyTrend = (weeks = 12) => api.get(`/analytics/weekly-trend?weeks=${weeks}`)
export const getHourlyDistribution = (days = 7) => api.get(`/analytics/hourly?days=${days}`)
export const getAlertsByContext = () => api.get('/analytics/by-context')
export const getAlertsByStatus = () => api.get('/analytics/by-status')
export const getAlertsByStudent = (limit = 10) => api.get(`/analytics/by-student?limit=${limit}`)
export const getScoreDistribution = () => api.get('/analytics/score-distribution')
export const getAlgorithmMetrics = () => api.get('/analytics/algorithm-metrics')

export default api
