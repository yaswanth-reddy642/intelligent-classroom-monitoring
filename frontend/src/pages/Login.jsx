import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { LogIn, Eye, EyeOff, Shield, CheckCircle } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({
    email: location.state?.email || '',
    password: '',
  })
  const [successMsg, setSuccessMsg] = useState(location.state?.message || '')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Login failed')
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-primary-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">🎓 Classroom Monitor</h1>
          <p className="text-gray-400 mt-2">YOLOv11 Intelligent Monitoring System</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <LogIn size={20} className="text-primary-600" />Teacher Login
          </h2>

          {successMsg && (
            <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm border border-green-200 flex items-center gap-2">
              <CheckCircle size={18} className="shrink-0 text-green-600" />
              <span>{successMsg}</span>
            </div>
          )}

          {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Registered Email or Mobile Number</label>
              <input type="text" required value={form.email}
                onChange={e => { setForm({ ...form, email: e.target.value }); setSuccessMsg('') }}
                placeholder="teacher@college.edu or 6363661265"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <input type={showPw ? 'text' : 'password'} required value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none pr-10" />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center space-y-3">
            <Link to="/forgot-password" className="text-sm text-primary-600 hover:underline block">Forgot Password?</Link>
            <div className="border-t pt-3">
              <Link to="/admin-login" className="text-sm text-gray-500 hover:text-primary-600 flex items-center justify-center gap-1">
                <Shield size={14} /> Admin Login
              </Link>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="font-semibold">Quick Login Credentials (Password: <span className="font-mono font-bold">teacher123</span>):</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setForm({ email: 'teacher@college.edu', password: 'teacher123' })}
                className="flex-1 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs font-medium cursor-pointer text-center"
              >
                Auto-fill: teacher@college.edu
              </button>
              <button
                type="button"
                onClick={() => setForm({ email: 'loshma@gmail.com', password: 'teacher123' })}
                className="flex-1 py-1.5 bg-emerald-600 text-white rounded hover:bg-emerald-700 text-xs font-medium cursor-pointer text-center"
              >
                Auto-fill: loshma@gmail.com
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
