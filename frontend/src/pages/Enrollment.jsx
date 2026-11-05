import { useState, useEffect, useRef } from 'react'
import { Shield, CheckCircle, Phone, Camera, Upload, FileSpreadsheet, Download, FileText, CheckCircle2, AlertCircle, UserPlus } from 'lucide-react'
import { createStudent, getPrivacyNotice, uploadStudentsCsv, getSampleCsvUrl } from '../services/api'
import api from '../services/api'

export default function Enrollment() {
  const [activeTab, setActiveTab] = useState('single')
  const [formData, setFormData] = useState({
    name: '', roll_number: '', department: '', section: '', semester: '',
    mobile_number: '', parent_mobile: '', email: '',
  })
  const [photo, setPhoto] = useState(null)
  const [photoPreview, setPhotoPreview] = useState(null)
  const [status, setStatus] = useState({ type: '', message: '' })
  const [loading, setLoading] = useState(false)
  const fileRef = useRef(null)

  // CSV Bulk Enrollment State
  const [csvFile, setCsvFile] = useState(null)
  const [csvLoading, setCsvLoading] = useState(false)
  const [csvResult, setCsvResult] = useState(null)
  const csvFileRef = useRef(null)

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value })

  const handlePhoto = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setPhoto(file)
    const reader = new FileReader()
    reader.onload = (ev) => setPhotoPreview(ev.target.result)
    reader.readAsDataURL(file)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus({ type: '', message: '' })
    setLoading(true)

    try {
      // 1. Create student record
      const dataToSubmit = { ...formData, semester: formData.semester ? parseInt(formData.semester) : 0 }
      const res = await createStudent(dataToSubmit)
      const rollNumber = formData.roll_number

      // 2. Upload photo if provided
      let photoMsg = ''
      if (photo && rollNumber) {
        try {
          const fd = new FormData()
          fd.append('file', photo)
          const photoRes = await api.post(`/students/${rollNumber}/photo`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
          photoMsg = ` Photo uploaded (${photoRes.data.size_kb} KB).`
        } catch (photoErr) {
          photoMsg = ' (Photo upload failed, student created without photo)'
          console.error('Photo upload error:', photoErr)
        }
      }

      setStatus({ type: 'success', message: `Student ${res.data.name} enrolled! ID: ${res.data.student_id}.${photoMsg}` })
      setFormData({ name: '', roll_number: '', department: '', section: '', semester: '', mobile_number: '', parent_mobile: '', email: '' })
      setPhoto(null)
      setPhotoPreview(null)
    } catch (e) {
      console.error(e)
      setStatus({ type: 'error', message: e.response?.data?.detail || 'Failed to add student.' })
    } finally {
      setLoading(false)
    }
  }

  const handleCsvSelect = (e) => {
    const f = e.target.files[0]
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.csv')) {
      setStatus({ type: 'error', message: 'Please select a valid .csv file' })
      return
    }
    setCsvFile(f)
    setCsvResult(null)
    setStatus({ type: '', message: '' })
  }

  const handleCsvUpload = async () => {
    if (!csvFile) {
      setStatus({ type: 'error', message: 'Please select a CSV file first' })
      return
    }
    setCsvLoading(true)
    setCsvResult(null)
    try {
      const res = await uploadStudentsCsv(csvFile)
      setCsvResult(res.data)
      setStatus({ type: 'success', message: res.data.message || 'CSV enrolled successfully!' })
      setCsvFile(null)
      if (csvFileRef.current) csvFileRef.current.value = ''
    } catch (e) {
      console.error('CSV upload error:', e)
      const errDetail = e.response?.data?.detail || e.message || 'Failed to upload CSV file'
      setStatus({ type: 'error', message: errDetail })
    } finally {
      setCsvLoading(false)
    }
  }

  const handleDownloadSample = () => {
    window.open(getSampleCsvUrl(), '_blank')
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Student Enrollment</h1>
        {/* Tab Switcher */}
        <div className="flex bg-gray-100 p-1 rounded-xl border border-gray-200">
          <button
            type="button"
            onClick={() => { setActiveTab('single'); setStatus({ type: '', message: '' }); }}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'single' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <UserPlus size={14} /> Single Student
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('csv'); setStatus({ type: '', message: '' }); }}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'csv' ? 'bg-white text-emerald-800 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <FileSpreadsheet size={14} className="text-emerald-600" /> Bulk CSV Upload
          </button>
        </div>
      </div>

      <div className="bg-primary-50 border border-primary-200 rounded-xl p-4 mb-6">
        <div className="flex items-start gap-3">
          <Shield size={20} className="text-primary-600 mt-1" />
          <p className="text-xs text-primary-700">Enrolled student details are matched automatically during video monitoring to identify roll numbers and dispatch instant SMS alerts to student and parent phones.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        {status.message && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 border ${status.type === 'success' ? 'bg-green-50 text-green-800 border-green-200' : 'bg-red-50 text-red-800 border-red-200'}`}>
            {status.type === 'success' && <CheckCircle size={20} className="text-green-600 flex-shrink-0" />}
            <div>
              <p className="font-medium">{status.message}</p>
              {status.type === 'success' && <a href="/students" className="text-sm text-green-700 underline mt-1 inline-block">View all enrolled students</a>}
            </div>
          </div>
        )}

        {/* ─── Bulk CSV Upload Tab ─── */}
        {activeTab === 'csv' && (
          <div>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <FileSpreadsheet size={18} className="text-emerald-600" />
                  Upload Student CSV File
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Select a CSV file containing your student roster. Existing roll numbers will be updated automatically.
                </p>
              </div>
              <button
                type="button"
                onClick={handleDownloadSample}
                className="text-xs text-emerald-700 hover:bg-emerald-100 flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-300 font-semibold transition"
              >
                <Download size={13} /> Sample CSV Template
              </button>
            </div>

            {/* Supported Fields Legend */}
            <div className="mb-4 bg-gray-50 p-3 rounded-lg border text-xs">
              <p className="font-semibold text-gray-700 mb-1.5">Required & Optional CSV Columns:</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
                <span className="bg-emerald-50 text-emerald-900 px-2 py-1 rounded border border-emerald-200 font-bold">
                  Name *
                </span>
                <span className="bg-emerald-50 text-emerald-900 px-2 py-1 rounded border border-emerald-200 font-bold">
                  Roll Number *
                </span>
                <span className="bg-white px-2 py-1 rounded border text-gray-600">Department</span>
                <span className="bg-white px-2 py-1 rounded border text-gray-600">Section</span>
                <span className="bg-white px-2 py-1 rounded border text-gray-600">Semester</span>
                <span className="bg-white px-2 py-1 rounded border text-gray-600">Student Mobile</span>
                <span className="bg-white px-2 py-1 rounded border text-gray-600">Parent Mobile</span>
                <span className="bg-white px-2 py-1 rounded border text-gray-600">Email</span>
              </div>
            </div>

            {/* CSV File Input */}
            <input
              type="file"
              ref={csvFileRef}
              accept=".csv"
              onChange={handleCsvSelect}
              className="hidden"
            />

            {!csvFile ? (
              <div
                onClick={() => csvFileRef.current?.click()}
                className="border-2 border-dashed border-emerald-300 hover:border-emerald-500 bg-emerald-50/20 hover:bg-emerald-50/60 rounded-xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center group"
              >
                <FileSpreadsheet size={44} className="text-emerald-500 mb-2 group-hover:scale-110 transition" />
                <p className="text-sm font-semibold text-gray-800">Click to choose a CSV file or drag & drop here</p>
                <p className="text-xs text-gray-500 mt-1">Accepts standard .csv UTF-8 files</p>
              </div>
            ) : (
              <div className="border border-emerald-300 bg-emerald-50/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText size={22} className="text-emerald-700" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{csvFile.name}</p>
                    <p className="text-xs text-gray-500">{(csvFile.size / 1024).toFixed(1)} KB • Ready for upload</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => { setCsvFile(null); if (csvFileRef.current) csvFileRef.current.value = ''; }}
                    className="px-3 py-1.5 text-xs text-gray-600 hover:text-red-600 transition"
                  >
                    Change File
                  </button>
                  <button
                    type="button"
                    onClick={handleCsvUpload}
                    disabled={csvLoading}
                    className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                  >
                    <Upload size={14} />
                    {csvLoading ? 'Enrolling Students...' : 'Upload & Enroll'}
                  </button>
                </div>
              </div>
            )}

            {/* CSV Result Feedback */}
            {csvResult && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-emerald-300 text-xs">
                <div className="flex items-center gap-2 text-emerald-800 font-bold mb-2">
                  <CheckCircle2 size={16} className="text-emerald-600" />
                  <span>{csvResult.message}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-gray-700 py-2 border-y border-gray-200">
                  <div><span className="text-gray-400">Total Rows:</span> <strong>{csvResult.total_rows}</strong></div>
                  <div><span className="text-emerald-600">New Enrolled:</span> <strong>{csvResult.inserted}</strong></div>
                  <div><span className="text-blue-600">Updated:</span> <strong>{csvResult.updated}</strong></div>
                </div>
                {csvResult.errors && csvResult.errors.length > 0 && (
                  <div className="mt-3 text-red-600 bg-red-50 p-2.5 rounded border border-red-200">
                    <p className="font-semibold mb-1 flex items-center gap-1"><AlertCircle size={14} /> Skipped Rows ({csvResult.errors.length}):</p>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                      {csvResult.errors.map((err, i) => (
                        <li key={i}>Row {err.row}: {err.reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ─── Single Student Form ─── */}
        {activeTab === 'single' && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Photo Upload */}
          <div className="flex items-center gap-6 pb-4 border-b">
            <div className="w-24 h-24 rounded-full bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden flex-shrink-0 cursor-pointer hover:border-primary-400 transition"
              onClick={() => fileRef.current?.click()}>
              {photoPreview ? (
                <img src={photoPreview} alt="Preview" className="w-full h-full object-cover" />
              ) : (
                <Camera size={28} className="text-gray-400" />
              )}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700 mb-1">Student Photo</p>
              <p className="text-xs text-gray-500 mb-2">Upload a clear face photo for identity mapping</p>
              <input type="file" ref={fileRef} accept=".jpg,.jpeg,.png,.webp" onChange={handlePhoto} className="hidden" />
              <button type="button" onClick={() => fileRef.current?.click()}
                className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
                <Upload size={14} />{photo ? 'Change Photo' : 'Choose Photo'}
              </button>
              {photo && <p className="text-xs text-green-600 mt-1">{photo.name}</p>}
            </div>
          </div>

          {/* Name & Roll */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name <span className="text-red-500">*</span></label>
              <input type="text" name="name" required value={formData.name} onChange={handleChange}
                placeholder="e.g. Ravi Kumar"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Roll Number <span className="text-red-500">*</span></label>
              <input type="text" name="roll_number" required value={formData.roll_number} onChange={handleChange}
                placeholder="e.g. 22B01A001"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
              <input type="text" name="department" value={formData.department} onChange={handleChange}
                placeholder="CSE" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Section</label>
              <input type="text" name="section" value={formData.section} onChange={handleChange}
                placeholder="A" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Semester</label>
              <input type="number" name="semester" min="1" max="8" value={formData.semester} onChange={handleChange}
                placeholder="5" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
          </div>

          {/* Contact */}
          <div className="border-t pt-4">
            <div className="flex items-center gap-2 mb-3">
              <Phone size={16} className="text-gray-500" />
              <h3 className="text-sm font-semibold text-gray-700">Contact (for SMS alerts)</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Student Mobile</label>
                <input type="tel" name="mobile_number" value={formData.mobile_number} onChange={handleChange}
                  placeholder="9876543210" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Parent Mobile</label>
                <input type="tel" name="parent_mobile" value={formData.parent_mobile} onChange={handleChange}
                  placeholder="9876543211" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
              </div>
            </div>
            <div className="mt-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" name="email" value={formData.email} onChange={handleChange}
                placeholder="ravi@college.edu" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500 outline-none" />
            </div>
          </div>

          <button type="submit" disabled={loading}
            className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition mt-2">
            {loading ? 'Enrolling...' : 'Enroll Student'}
          </button>
        </form>
      )}
      </div>
    </div>
  )
}
