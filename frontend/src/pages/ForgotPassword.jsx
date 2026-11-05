import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Smartphone,
  KeyRound,
  CheckCircle,
  ArrowLeft,
  Eye,
  EyeOff,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Mail,
} from 'lucide-react'
import { API_BASE } from '../services/api'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1) // 1: mobile, 2: otp + new password, 3: success
  const [inputVal, setInputVal] = useState('')
  const [isEmailMode, setIsEmailMode] = useState(false)
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNewPw, setShowNewPw] = useState(false)
  const [showConfirmPw, setShowConfirmPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [smsStatus, setSmsStatus] = useState(null)

  // Feedback states
  const [maskedMobile, setMaskedMobile] = useState('')
  const [maskedEmail, setMaskedEmail] = useState('')
  const [deliveryChannel, setDeliveryChannel] = useState('Email')
  const [teacherName, setTeacherName] = useState('')
  const [resolvedEmail, setResolvedEmail] = useState('')
  const [cooldown, setCooldown] = useState(0)

  // Resend OTP countdown timer
  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setInterval(() => setCooldown((c) => c - 1), 1000)
    return () => clearInterval(timer)
  }, [cooldown])

  // Request OTP via SMS
  const handleRequestOtp = async (e) => {
    if (e) e.preventDefault()
    setError('')
    const clean = inputVal.trim()
    if (!clean) {
      setError(isEmailMode ? 'Please enter your registered email' : 'Please enter your 10-digit mobile number')
      return
    }

    if (!isEmailMode) {
      const digitsOnly = clean.replace(/\D/g, '')
      if (digitsOnly.length < 10) {
        setError('Please enter a valid 10-digit mobile number (e.g. 6363661265)')
        return
      }
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mobile_or_email: clean,
          mobile_number: isEmailMode ? '' : clean,
          email: isEmailMode ? clean : '',
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to send SMS to your mobile phone')
      }

      setMaskedMobile(data.masked_mobile || clean)
      setMaskedEmail(data.masked_email || data.email || '')
      setDeliveryChannel(data.delivery_channel || 'Email')
      setTeacherName(data.teacher_name || 'Teacher')
      setResolvedEmail(data.email || '')
      setSmsStatus(data.sms_dispatch || null)
      setCooldown(30)
      setStep(2)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Verify OTP and reset password
  const handleResetPassword = async (e) => {
    e.preventDefault()
    setError('')

    const cleanOtp = otp.trim()
    if (!cleanOtp || cleanOtp.length !== 6) {
      setError('Please enter the complete 6-digit OTP received on your mobile')
      return
    }

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters long')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation password do not match')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mobile_or_email: inputVal.trim(),
          otp: cleanOtp,
          reset_code: cleanOtp,
          new_password: newPassword,
        }),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to reset password')

      setStep(3)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-primary-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand header */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-white flex items-center justify-center gap-2">
            <span>🎓</span> Classroom Monitor
          </h1>
          <p className="text-gray-400 mt-1 text-sm">Intelligent AI Surveillance & Safety System</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-7 border border-gray-100">
          {/* Card Title */}
          <div className="flex items-center gap-2.5 pb-4 mb-5 border-b border-gray-100">
            <div className="w-9 h-9 rounded-xl bg-primary-50 flex items-center justify-center text-primary-600">
              {step === 1 && <Smartphone size={20} />}
              {step === 2 && <KeyRound size={20} />}
              {step === 3 && <CheckCircle size={20} className="text-green-600" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {step === 1 && 'Teacher Password Reset'}
                {step === 2 && 'Enter Mobile SMS OTP'}
                {step === 3 && 'Password Reset Complete!'}
              </h2>
              <p className="text-xs text-gray-500">
                {step === 1 && 'Send real SMS OTP to registered mobile number'}
                {step === 2 && `Enter 6-digit OTP sent to ${maskedMobile}`}
                {step === 3 && 'Account secured & updated'}
              </p>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-4 p-3.5 bg-red-50 text-red-700 rounded-xl text-xs border border-red-200 flex items-start gap-2.5 leading-relaxed">
              <AlertCircle size={18} className="shrink-0 mt-0.5 text-red-600" />
              <div>
                <p className="font-semibold text-red-800 mb-0.5">SMS Delivery Issue</p>
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════
              STEP 1: Ask Mobile Number
              ═══════════════════════════════════════════ */}
          {step === 1 && (
            <form onSubmit={handleRequestOtp} className="space-y-4">
              <p className="text-xs text-gray-600 leading-relaxed">
                Enter your registered teacher mobile number. A 6-digit numeric OTP will be dispatched via SMS directly to your mobile phone.
              </p>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-semibold text-gray-700">
                    {isEmailMode ? 'Registered Teacher Email' : 'Teacher Mobile Number'}
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setIsEmailMode(!isEmailMode)
                      setInputVal('')
                      setError('')
                    }}
                    className="text-xs text-primary-600 hover:underline flex items-center gap-1 font-medium"
                  >
                    {isEmailMode ? (
                      <>
                        <Smartphone size={12} /> Switch to Mobile Number
                      </>
                    ) : (
                      <>
                        <Mail size={12} /> Use Email Instead
                      </>
                    )}
                  </button>
                </div>

                {isEmailMode ? (
                  <div className="relative">
                    <input
                      type="email"
                      required
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      placeholder="teacher@college.edu"
                      className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
                    />
                  </div>
                ) : (
                  <div className="relative flex rounded-lg shadow-sm">
                    <span className="inline-flex items-center px-3 rounded-l-lg border border-r-0 border-gray-300 bg-gray-50 text-gray-600 font-mono text-sm">
                      🇮🇳 +91
                    </span>
                    <input
                      type="tel"
                      required
                      maxLength={10}
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value.replace(/\D/g, ''))}
                      placeholder="6363661265"
                      className="w-full px-3.5 py-2.5 border border-gray-300 rounded-r-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none font-mono text-sm tracking-wider"
                    />
                  </div>
                )}
              </div>

              {/* Quick-fill helper button */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsEmailMode(false)
                    setInputVal('6363661265')
                    setError('')
                  }}
                  className="w-full py-1.5 px-3 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <span>⚡ Quick-Fill:</span>
                  <span className="font-mono font-bold">6363661265 (Teacher HOD)</span>
                </button>
              </div>

              {/* Submit button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium text-sm disabled:opacity-50 transition shadow-sm flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Dispatching SMS to Mobile...</span>
                  </>
                ) : (
                  <>
                    <Smartphone size={16} />
                    <span>Send Verification OTP to Mobile</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* ═══════════════════════════════════════════
              STEP 2: Enter OTP & Set New Password
              ═══════════════════════════════════════════ */}
          {step === 2 && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              {/* Recipient info banner */}
              <div className="p-3.5 bg-green-50 border border-green-200 rounded-xl space-y-1 text-xs">
                <div className="flex items-center gap-1.5 text-green-800 font-semibold">
                  <CheckCircle size={15} className="text-green-600 shrink-0" />
                  <span>OTP dispatched via {deliveryChannel}! Check your inbox.</span>
                </div>
                {maskedEmail && (
                  <div className="text-gray-600 flex justify-between pt-1">
                    <span>Email Inbox:</span>
                    <span className="font-mono font-bold text-gray-900">{maskedEmail}</span>
                  </div>
                )}
                {maskedMobile && (
                  <div className="text-gray-600 flex justify-between">
                    <span>Mobile:</span>
                    <span className="font-mono text-gray-700">{maskedMobile}</span>
                  </div>
                )}
                <div className="text-gray-600 flex justify-between">
                  <span>Provider:</span>
                  <span className="font-medium text-emerald-700">Brevo Transactional Service</span>
                </div>
                <p className="text-[11px] text-gray-500 pt-1">
                  Please check your {deliveryChannel === 'Email' ? 'email inbox (or spam folder)' : 'inbox'} for the 6-digit verification code.
                </p>
              </div>

              {/* OTP Input */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Enter 6-Digit Verification OTP
                </label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="------"
                  className="w-full px-4 py-2.5 border-2 border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-600 outline-none font-mono text-center text-xl tracking-[0.5em] font-bold text-gray-800 bg-gray-50/50"
                />
              </div>

              {/* New Password */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">New Password</label>
                <div className="relative">
                  <input
                    type={showNewPw ? 'text' : 'password'}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 6 characters"
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPw(!showNewPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showNewPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Confirm New Password */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Confirm New Password</label>
                <div className="relative">
                  <input
                    type={showConfirmPw ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPw(!showConfirmPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirmPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Submit reset */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium text-sm disabled:opacity-50 transition shadow-sm flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Verifying OTP & Updating Password...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck size={16} />
                    <span>Verify OTP & Update Password</span>
                  </>
                )}
              </button>

              {/* Actions: Resend OTP and Change Number */}
              <div className="flex items-center justify-between text-xs pt-1 text-gray-500">
                <button
                  type="button"
                  onClick={() => {
                    setStep(1)
                    setError('')
                  }}
                  className="text-gray-500 hover:text-primary-600 flex items-center gap-1 cursor-pointer"
                >
                  <ArrowLeft size={13} /> Change Mobile
                </button>

                <button
                  type="button"
                  disabled={cooldown > 0 || loading}
                  onClick={handleRequestOtp}
                  className="text-primary-600 hover:underline disabled:text-gray-400 disabled:no-underline font-medium cursor-pointer"
                >
                  {cooldown > 0 ? `Resend SMS in ${cooldown}s` : 'Resend OTP via SMS'}
                </button>
              </div>
            </form>
          )}

          {/* ═══════════════════════════════════════════
              STEP 3: Success Screen
              ═══════════════════════════════════════════ */}
          {step === 3 && (
            <div className="text-center py-3 space-y-4">
              <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto shadow-inner">
                <CheckCircle size={36} />
              </div>

              <div>
                <h3 className="text-lg font-bold text-gray-900">Password Reset Successfully!</h3>
                <p className="text-xs text-gray-600 mt-1 max-w-xs mx-auto">
                  Your password has been updated. All previous student attendance, alerts, and analytics records remain safe and preserved.
                </p>
              </div>

              <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl text-xs text-left space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-500">Teacher:</span>
                  <span className="font-semibold text-gray-800">{teacherName || 'Teacher'}</span>
                </div>
                {resolvedEmail && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Login ID:</span>
                    <span className="font-mono text-gray-800">{resolvedEmail}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Mobile Verified:</span>
                  <span className="font-mono text-green-700 font-semibold">{maskedMobile}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() =>
                  navigate('/login', {
                    state: {
                      email: resolvedEmail || inputVal,
                      message: 'Password reset successfully! Please sign in with your new password.',
                    },
                  })
                }
                className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium text-sm transition shadow-sm cursor-pointer"
              >
                Proceed to Teacher Login →
              </button>
            </div>
          )}

          {/* Back to Login link */}
          {step !== 3 && (
            <div className="mt-5 pt-4 border-t border-gray-100 text-center">
              <Link
                to="/login"
                className="text-xs text-gray-500 hover:text-primary-600 flex items-center justify-center gap-1 font-medium"
              >
                <ArrowLeft size={13} /> Back to Teacher Login
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
