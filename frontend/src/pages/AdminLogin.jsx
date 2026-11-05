import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Shield, Eye, EyeOff } from 'lucide-react'

export default function AdminLogin() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/auth/admin-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Login failed')
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      navigate('/admin')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-red-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">🔐 Admin Panel</h1>
          <p className="text-gray-400 mt-2">Classroom Monitoring Administration</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <Shield size={20} className="text-red-600" />Admin Login
          </h2>

          {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Admin Email</label>
              <input type="email" required value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                placeholder="admin@classroom.edu"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <input type={showPw ? 'text' : 'password'} required value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none pr-10" />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 transition">
              {loading ? 'Signing in...' : 'Admin Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center space-y-2">
            <Link to="/admin-forgot-password" className="text-sm text-red-600 hover:underline block">Forgot Admin Password?</Link>
            <Link to="/login" className="text-sm text-gray-500 hover:text-primary-600">← Back to Teacher Login</Link>
          </div>

          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center justify-between">
            <div>
              <p className="font-semibold">Admin Credentials:</p>
              <p>Email: <span className="font-mono font-bold">admin@classroom.edu</span></p>
              <p>Password: <span className="font-mono font-bold">admin123</span></p>
            </div>
            <button
              type="button"
              onClick={() => setForm({ email: 'admin@classroom.edu', password: 'admin123' })}
              className="px-2.5 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-xs font-medium cursor-pointer"
            >
              Auto-fill
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
