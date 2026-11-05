import { useState } from 'react'
import { Link } from 'react-router-dom'
import { KeyRound, CheckCircle } from 'lucide-react'
import { API_BASE } from '../services/api'

export default function AdminForgotPassword() {
  const [step, setStep] = useState(1)
  const [email, setEmail] = useState('')
  const [resetCode, setResetCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [codeHint, setCodeHint] = useState('')

  const handleRequestCode = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/admin-forgot-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed')
      if (data.reset_code) setCodeHint(data.reset_code)
      setStep(2)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  const handleReset = async (e) => {
    e.preventDefault()
    setError('')
    if (newPassword.length < 6) { setError('Password must be at least 6 characters'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/admin-reset-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, reset_code: resetCode, new_password: newPassword }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Reset failed')
      setStep(3)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-red-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <KeyRound size={20} className="text-red-600" />
            {step === 1 && 'Admin Forgot Password'}
            {step === 2 && 'Enter Reset Code'}
            {step === 3 && 'Password Reset!'}
          </h2>
          {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">{error}</div>}

          {step === 1 && (
            <form onSubmit={handleRequestCode} className="space-y-4">
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="admin@classroom.edu"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg outline-none" />
              <button type="submit" disabled={loading}
                className="w-full py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50">
                {loading ? 'Sending...' : 'Send Reset Code'}
              </button>
            </form>
          )}
          {step === 2 && (
            <form onSubmit={handleReset} className="space-y-4">
              <input type="text" required value={resetCode} onChange={e => setResetCode(e.target.value)}
                placeholder="123456" maxLength={6}
                className="w-full px-4 py-2.5 border rounded-lg text-center text-xl tracking-widest font-mono outline-none" />
              <input type="password" required value={newPassword} onChange={e => setNewPassword(e.target.value)}
                placeholder="New password (min 6 chars)"
                className="w-full px-4 py-2.5 border rounded-lg outline-none" />
              <button type="submit" disabled={loading}
                className="w-full py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50">
                {loading ? 'Resetting...' : 'Reset Password'}
              </button>
            </form>
          )}
          {step === 3 && (
            <div className="text-center">
              <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
              <p className="text-lg font-medium mb-2">Password Reset!</p>
              <Link to="/admin-login" className="text-red-600 font-medium hover:underline">Go to Admin Login</Link>
            </div>
          )}
          <div className="mt-6 text-center">
            <Link to="/admin-login" className="text-sm text-gray-500 hover:text-red-600">← Back to Admin Login</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
