import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Users, UserPlus, Bell, Trash2, Camera, Upload, LogOut, ChevronDown, ChevronUp, Phone, GraduationCap, FileSpreadsheet, Download, FileText, CheckCircle2, AlertCircle, Edit2, Save, X } from 'lucide-react'
import api, { uploadStudentsCsv, getSampleCsvUrl, updateStudent } from '../services/api'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState({ students: 0, teachers: 0, alerts: 0 })
  const [students, setStudents] = useState([])
  const [teachers, setTeachers] = useState([])
  const [showAddStudent, setShowAddStudent] = useState(false)
  const [showCsvUpload, setShowCsvUpload] = useState(false)
  const [csvFile, setCsvFile] = useState(null)
  const [csvLoading, setCsvLoading] = useState(false)
  const [csvResult, setCsvResult] = useState(null)
  const [showAddTeacher, setShowAddTeacher] = useState(false)
  const [msg, setMsg] = useState({ text: '', type: '' })
  const [stuForm, setStuForm] = useState({ name: '', roll_number: '', department: '', section: '', semester: '', mobile_number: '', parent_mobile: '', email: '' })
  const [stuPhoto, setStuPhoto] = useState(null)
  const [stuPhotoPreview, setStuPhotoPreview] = useState(null)
  const [editingStudent, setEditingStudent] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', roll_number: '', department: '', section: '', semester: '', mobile_number: '', parent_mobile: '', email: '' })
  const [editPhoto, setEditPhoto] = useState(null)
  const [editPhotoPreview, setEditPhotoPreview] = useState(null)
  const [tchForm, setTchForm] = useState({ name: '', email: '', password: '', department: '', employee_id: '' })
  const [loading, setLoading] = useState(false)
  const fileRef = useRef(null)
  const editFileRef = useRef(null)
  const csvFileRef = useRef(null)
  const token = localStorage.getItem('token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => { fetchAll() }, [])

  const fetchAll = async () => {
    try {
      const [s, st, t] = await Promise.all([
        api.get('/auth/admin/stats', { headers }),
        api.get('/students'),
        api.get('/auth/admin/teachers', { headers }),
      ])
      setStats(s.data)
      setStudents(st.data.students || [])
      setTeachers(t.data.teachers || [])
    } catch (e) { console.error(e) }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/admin-login')
  }

  const flash = (text, type = 'success') => { setMsg({ text, type }); setTimeout(() => setMsg({ text: '', type: '' }), 4000) }

  // Student management
  const handleAddStudent = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = { ...stuForm, semester: stuForm.semester ? parseInt(stuForm.semester) : 0 }
      const res = await api.post('/students', data)
      if (stuPhoto && stuForm.roll_number) {
        const fd = new FormData()
        fd.append('file', stuPhoto)
        await api.post(`/students/${stuForm.roll_number}/photo`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      }
      flash(`Student ${res.data.name} enrolled!`)
      setStuForm({ name: '', roll_number: '', department: '', section: '', semester: '', mobile_number: '', parent_mobile: '', email: '' })
      setStuPhoto(null); setStuPhotoPreview(null)
      setShowAddStudent(false)
      fetchAll()
    } catch (e) { flash(e.response?.data?.detail || 'Failed', 'error') }
    finally { setLoading(false) }
  }

  const handleDeleteStudent = async (roll) => {
    if (!confirm(`Delete student ${roll}?`)) return
    try { await api.delete(`/students/${roll}`); flash('Student deleted'); fetchAll() }
    catch (e) { flash('Delete failed', 'error') }
  }

  const handlePhotoSelect = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setStuPhoto(f)
    const r = new FileReader()
    r.onload = (ev) => setStuPhotoPreview(ev.target.result)
    r.readAsDataURL(f)
  }

  // Student Edit handlers
  const handleStartEditStudent = (student) => {
    setEditingStudent(student)
    setEditForm({
      name: student.name || '',
      roll_number: student.roll_number || '',
      department: student.department || '',
      section: student.section || '',
      semester: student.semester || '',
      mobile_number: student.mobile_number || '',
      parent_mobile: student.parent_mobile || '',
      email: student.email || '',
    })
    setEditPhoto(null)
    setEditPhotoPreview(student.photo_url || null)
  }

  const handleCancelEdit = () => {
    setEditingStudent(null)
    setEditForm({
      name: '',
      roll_number: '',
      department: '',
      section: '',
      semester: '',
      mobile_number: '',
      parent_mobile: '',
      email: '',
    })
    setEditPhoto(null)
    setEditPhotoPreview(null)
    if (editFileRef.current) editFileRef.current.value = ''
  }

  const handleEditPhotoSelect = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setEditPhoto(f)
    const r = new FileReader()
    r.onload = (ev) => setEditPhotoPreview(ev.target.result)
    r.readAsDataURL(f)
  }

  const handleUpdateStudent = async (e) => {
    e.preventDefault()
    if (!editingStudent) return
    setLoading(true)
    try {
      const data = {
        ...editForm,
        semester: editForm.semester ? parseInt(editForm.semester) : 0,
      }
      const res = await updateStudent(editingStudent.roll_number, data)
      const targetRoll = editForm.roll_number || editingStudent.roll_number

      // If a new photo was chosen, upload it
      if (editPhoto && targetRoll) {
        const fd = new FormData()
        fd.append('file', editPhoto)
        await api.post(`/students/${targetRoll}/photo`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }

      flash(res.data?.message || `Student ${editForm.name} updated successfully!`)
      handleCancelEdit()
      fetchAll()
    } catch (err) {
      console.error('Update student error:', err)
      const errMsg = err.response?.data?.detail || err.message || 'Failed to update student details'
      flash(errMsg, 'error')
    } finally {
      setLoading(false)
    }
  }

  // CSV Bulk Enrollment
  const handleCsvSelect = (e) => {
    const f = e.target.files[0]
    if (!f) return
    if (!f.name.toLowerCase().endsWith('.csv')) {
      flash('Please select a valid .csv file', 'error')
      return
    }
    setCsvFile(f)
    setCsvResult(null)
  }

  const handleCsvUpload = async () => {
    if (!csvFile) {
      flash('Please select a CSV file first', 'error')
      return
    }
    setCsvLoading(true)
    setCsvResult(null)
    try {
      const res = await uploadStudentsCsv(csvFile)
      setCsvResult(res.data)
      flash(res.data.message || 'CSV enrolled successfully!', 'success')
      setCsvFile(null)
      if (csvFileRef.current) csvFileRef.current.value = ''
      fetchAll()
    } catch (e) {
      console.error('CSV upload error:', e)
      const errDetail = e.response?.data?.detail || e.message || 'Failed to upload CSV file'
      flash(errDetail, 'error')
    } finally {
      setCsvLoading(false)
    }
  }

  const handleDownloadSample = () => {
    window.open(getSampleCsvUrl(), '_blank')
  }

  // Teacher management
  const handleAddTeacher = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/auth/admin/register-teacher', tchForm, { headers })
      flash(`Teacher ${tchForm.name} registered!`)
      setTchForm({ name: '', email: '', password: '', department: '', employee_id: '' })
      setShowAddTeacher(false)
      fetchAll()
    } catch (e) { flash(e.response?.data?.detail || 'Failed', 'error') }
    finally { setLoading(false) }
  }

  const handleDeleteTeacher = async (id) => {
    if (!confirm(`Delete teacher ${id}?`)) return
    try { await api.delete(`/auth/admin/teachers/${id}`, { headers }); flash('Teacher deleted'); fetchAll() }
    catch (e) { flash('Delete failed', 'error') }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-gray-900 text-white px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <Shield size={24} className="text-red-400" />
          <div>
            <h1 className="text-lg font-bold">Admin Dashboard</h1>
            <p className="text-xs text-gray-400">Classroom Monitoring System</p>
          </div>
        </div>
        <button onClick={handleLogout} className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">
          <LogOut size={16} />Logout
        </button>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        {/* Flash message */}
        {msg.text && (
          <div className={`mb-4 p-3 rounded-lg text-sm border ${msg.type === 'error' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-green-50 text-green-700 border-green-200'}`}>
            {msg.text}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm p-6 flex items-center gap-4">
            <div className="p-3 bg-blue-50 rounded-lg"><GraduationCap size={24} className="text-blue-600" /></div>
            <div><p className="text-sm text-gray-500">Students</p><p className="text-2xl font-bold">{stats.students}</p></div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 flex items-center gap-4">
            <div className="p-3 bg-green-50 rounded-lg"><Users size={24} className="text-green-600" /></div>
            <div><p className="text-sm text-gray-500">Teachers</p><p className="text-2xl font-bold">{stats.teachers}</p></div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 flex items-center gap-4">
            <div className="p-3 bg-red-50 rounded-lg"><Bell size={24} className="text-red-600" /></div>
            <div><p className="text-sm text-gray-500">Alerts</p><p className="text-2xl font-bold">{stats.alerts}</p></div>
          </div>
        </div>

        {/* Student Management */}
        <div className="bg-white rounded-xl shadow-sm mb-6">
          <div className="px-6 py-4 border-b flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <GraduationCap size={20} className="text-blue-600" />
              Student Management ({students.length})
            </h2>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleDownloadSample}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-medium border border-gray-300 transition"
                title="Download CSV template with required headers and sample data"
              >
                <Download size={14} /> Download Sample CSV
              </button>
              <button
                onClick={() => { setShowCsvUpload(!showCsvUpload); if (!showCsvUpload) setShowAddStudent(false); }}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  showCsvUpload ? 'bg-emerald-700 text-white' : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                }`}
              >
                <FileSpreadsheet size={15} />
                {showCsvUpload ? 'Close CSV Upload' : 'Upload CSV File'}
              </button>
              <button
                onClick={() => { setShowAddStudent(!showAddStudent); if (!showAddStudent) setShowCsvUpload(false); }}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition"
              >
                {showAddStudent ? <ChevronUp size={15} /> : <UserPlus size={15} />}
                {showAddStudent ? 'Cancel' : 'Add Single Student'}
              </button>
            </div>
          </div>

          {/* Bulk CSV Upload Panel */}
          {showCsvUpload && (
            <div className="p-6 border-b bg-emerald-50/50">
              <div className="max-w-3xl mx-auto">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <FileSpreadsheet size={18} className="text-emerald-600" />
                      Bulk Student Enrollment via CSV
                    </h3>
                    <p className="text-xs text-gray-600 mt-0.5">
                      Upload a CSV file containing student records. New students will be enrolled and existing roll numbers will be updated.
                    </p>
                  </div>
                  <button
                    onClick={handleDownloadSample}
                    className="text-xs text-emerald-700 hover:underline flex items-center gap-1 bg-white px-2.5 py-1 rounded border border-emerald-300 font-medium"
                  >
                    <Download size={12} /> Get Template (.csv)
                  </button>
                </div>

                {/* Supported Fields Legend */}
                <div className="mb-4 bg-white p-3 rounded-lg border border-emerald-200 text-xs">
                  <p className="font-semibold text-gray-700 mb-1.5">Supported CSV Columns:</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-gray-600 font-mono text-[11px]">
                    <span className="bg-emerald-50 px-2 py-1 rounded border border-emerald-100">
                      <strong className="text-emerald-900">Name</strong> *
                    </span>
                    <span className="bg-emerald-50 px-2 py-1 rounded border border-emerald-100">
                      <strong className="text-emerald-900">Roll Number</strong> *
                    </span>
                    <span className="bg-gray-50 px-2 py-1 rounded border">Department</span>
                    <span className="bg-gray-50 px-2 py-1 rounded border">Section</span>
                    <span className="bg-gray-50 px-2 py-1 rounded border">Semester</span>
                    <span className="bg-gray-50 px-2 py-1 rounded border">Student Mobile</span>
                    <span className="bg-gray-50 px-2 py-1 rounded border">Parent Mobile</span>
                    <span className="bg-gray-50 px-2 py-1 rounded border">Email</span>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-1.5 italic">* Name and Roll Number are mandatory. Headers are case-insensitive.</p>
                </div>

                {/* Upload Drag/Select Area */}
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
                    className="border-2 border-dashed border-emerald-300 bg-white hover:bg-emerald-50/50 rounded-xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center group"
                  >
                    <FileSpreadsheet size={40} className="text-emerald-500 mb-2 group-hover:scale-110 transition" />
                    <p className="text-sm font-semibold text-gray-700">Click to choose a CSV file or drag & drop</p>
                    <p className="text-xs text-gray-500 mt-1">Accepts standard .csv files with UTF-8 encoding</p>
                  </div>
                ) : (
                  <div className="bg-white border border-emerald-300 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <FileText size={20} className="text-emerald-700" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{csvFile.name}</p>
                        <p className="text-xs text-gray-500">{(csvFile.size / 1024).toFixed(1)} KB • CSV Document</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => { setCsvFile(null); if (csvFileRef.current) csvFileRef.current.value = ''; }}
                        className="px-3 py-1.5 text-xs text-gray-600 hover:text-red-600 hover:bg-gray-100 rounded transition"
                      >
                        Remove
                      </button>
                      <button
                        type="button"
                        onClick={handleCsvUpload}
                        disabled={csvLoading}
                        className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                      >
                        <Upload size={14} />
                        {csvLoading ? 'Uploading & Enrolling...' : 'Upload & Enroll Students'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Result Feedback Box */}
                {csvResult && (
                  <div className="mt-4 p-4 bg-white rounded-lg border border-emerald-300 shadow-sm text-xs">
                    <div className="flex items-center gap-2 text-emerald-800 font-bold mb-2">
                      <CheckCircle2 size={16} className="text-emerald-600" />
                      <span>{csvResult.message}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center text-gray-700 py-2 border-y border-gray-100">
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
            </div>
          )}

          {/* Add Student Form */}
          {showAddStudent && (
            <div className="px-6 py-4 border-b bg-blue-50">
              <form onSubmit={handleAddStudent} className="space-y-3">
                <div className="flex items-center gap-4 mb-2">
                  <div className="w-16 h-16 rounded-full bg-white border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden cursor-pointer hover:border-blue-400"
                    onClick={() => fileRef.current?.click()}>
                    {stuPhotoPreview ? <img src={stuPhotoPreview} className="w-full h-full object-cover" /> : <Camera size={20} className="text-gray-400" />}
                  </div>
                  <input type="file" ref={fileRef} accept=".jpg,.jpeg,.png" onChange={handlePhotoSelect} className="hidden" />
                  <div className="flex-1 grid grid-cols-2 gap-3">
                    <input type="text" required placeholder="Name *" value={stuForm.name}
                      onChange={e => setStuForm({...stuForm, name: e.target.value})}
                      className="px-3 py-2 border rounded-lg text-sm outline-none" />
                    <input type="text" required placeholder="Roll Number *" value={stuForm.roll_number}
                      onChange={e => setStuForm({...stuForm, roll_number: e.target.value})}
                      className="px-3 py-2 border rounded-lg text-sm outline-none" />
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  <input type="text" placeholder="Department" value={stuForm.department}
                    onChange={e => setStuForm({...stuForm, department: e.target.value})}
                    className="px-3 py-2 border rounded-lg text-sm outline-none" />
                  <input type="text" placeholder="Section" value={stuForm.section}
                    onChange={e => setStuForm({...stuForm, section: e.target.value})}
                    className="px-3 py-2 border rounded-lg text-sm outline-none" />
                  <input type="number" placeholder="Semester" min="1" max="8" value={stuForm.semester}
                    onChange={e => setStuForm({...stuForm, semester: e.target.value})}
                    className="px-3 py-2 border rounded-lg text-sm outline-none" />
                  <input type="email" placeholder="Email" value={stuForm.email}
                    onChange={e => setStuForm({...stuForm, email: e.target.value})}
                    className="px-3 py-2 border rounded-lg text-sm outline-none" />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <input type="tel" placeholder="Student Mobile" value={stuForm.mobile_number}
                    onChange={e => setStuForm({...stuForm, mobile_number: e.target.value})}
                    className="px-3 py-2 border rounded-lg text-sm outline-none" />
                  <input type="tel" placeholder="Parent Mobile" value={stuForm.parent_mobile}
                    onChange={e => setStuForm({...stuForm, parent_mobile: e.target.value})}
                    className="px-3 py-2 border rounded-lg text-sm outline-none" />
                  <button type="submit" disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                    {loading ? 'Enrolling...' : 'Enroll Student'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Student List */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Photo</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Roll No.</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Dept</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Mobile</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Parent</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {students.map(s => (
                  <tr key={s.student_id || s._id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="w-10 h-10 rounded-full bg-gray-100 overflow-hidden flex items-center justify-center">
                        {s.photo_url ? <img src={s.photo_url} className="w-full h-full object-cover" /> : <Camera size={16} className="text-gray-300" />}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium">{s.name}</td>
                    <td className="px-4 py-3 text-primary-600 font-medium">{s.roll_number}</td>
                    <td className="px-4 py-3 text-gray-500">{s.department || '-'}</td>
                    <td className="px-4 py-3">{s.mobile_number ? <span className="flex items-center gap-1 text-green-600"><Phone size={12} />{s.mobile_number}</span> : '-'}</td>
                    <td className="px-4 py-3">{s.parent_mobile ? <span className="flex items-center gap-1 text-blue-600"><Phone size={12} />{s.parent_mobile}</span> : '-'}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleStartEditStudent(s)}
                          className="p-1.5 text-blue-600 hover:bg-blue-50 hover:text-blue-700 rounded transition"
                          title="Edit Student Details"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDeleteStudent(s.roll_number)}
                          className="p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 rounded transition"
                          title="Delete Student"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {students.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No students enrolled</td></tr>}
              </tbody>
            </table>
          </div>

          {/* Edit Student Modal */}
          {editingStudent && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
              <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden border border-gray-100 animate-in fade-in zoom-in duration-150">
                {/* Modal Header */}
                <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 bg-white/20 rounded-xl">
                      <Edit2 size={18} />
                    </div>
                    <div>
                      <h3 className="text-base font-bold">Edit Student Details</h3>
                      <p className="text-xs text-blue-100">
                        Update enrolled record for {editingStudent.name} ({editingStudent.roll_number})
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleCancelEdit}
                    className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition"
                    title="Close"
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Modal Form */}
                <form onSubmit={handleUpdateStudent} className="p-6 space-y-4">
                  {/* Photo Upload Row */}
                  <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl border border-gray-100">
                    <div
                      className="w-16 h-16 rounded-full bg-white border-2 border-dashed border-blue-400 flex items-center justify-center overflow-hidden cursor-pointer hover:opacity-80 relative group"
                      onClick={() => editFileRef.current?.click()}
                      title="Click to change student photo"
                    >
                      {editPhotoPreview ? (
                        <img src={editPhotoPreview} alt="Preview" className="w-full h-full object-cover" />
                      ) : (
                        <Camera size={22} className="text-gray-400" />
                      )}
                      <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition text-white">
                        <Camera size={16} />
                      </div>
                    </div>
                    <input
                      type="file"
                      ref={editFileRef}
                      accept=".jpg,.jpeg,.png,.webp"
                      onChange={handleEditPhotoSelect}
                      className="hidden"
                    />
                    <div>
                      <p className="text-xs font-semibold text-gray-800">Student Profile Photo</p>
                      <p className="text-[11px] text-gray-500">
                        Click the avatar to upload or replace reference photo for facial matching.
                      </p>
                      {editPhoto && (
                        <span className="text-[11px] text-emerald-600 font-medium">
                          ✓ New photo selected: {editPhoto.name}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Basic Info */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">
                        Full Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={editForm.name}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="e.g. Rahul Sharma"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">
                        Roll Number <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={editForm.roll_number}
                        onChange={(e) => setEditForm({ ...editForm, roll_number: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono"
                        placeholder="e.g. 21CS101"
                      />
                    </div>
                  </div>

                  {/* Academic Details */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Department</label>
                      <input
                        type="text"
                        value={editForm.department}
                        onChange={(e) => setEditForm({ ...editForm, department: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="e.g. Computer Science"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Section</label>
                      <input
                        type="text"
                        value={editForm.section}
                        onChange={(e) => setEditForm({ ...editForm, section: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="e.g. A"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Semester</label>
                      <input
                        type="number"
                        min="1"
                        max="8"
                        value={editForm.semester}
                        onChange={(e) => setEditForm({ ...editForm, semester: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="e.g. 6"
                      />
                    </div>
                  </div>

                  {/* Contact Info */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Student Mobile</label>
                      <input
                        type="tel"
                        value={editForm.mobile_number}
                        onChange={(e) => setEditForm({ ...editForm, mobile_number: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="+919876543210"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Parent Mobile</label>
                      <input
                        type="tel"
                        value={editForm.parent_mobile}
                        onChange={(e) => setEditForm({ ...editForm, parent_mobile: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="+919876543211"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Email</label>
                      <input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        placeholder="student@example.edu"
                      />
                    </div>
                  </div>

                  {/* Modal Actions */}
                  <div className="flex items-center justify-end gap-2 pt-4 border-t border-gray-100">
                    <button
                      type="button"
                      onClick={handleCancelEdit}
                      disabled={loading}
                      className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex items-center gap-1.5 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition disabled:opacity-50"
                    >
                      <Save size={16} />
                      {loading ? 'Saving Changes...' : 'Save Changes'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>

        {/* Teacher Management */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2"><Users size={20} className="text-green-600" />Teacher Management ({teachers.length})</h2>
            <button onClick={() => setShowAddTeacher(!showAddTeacher)}
              className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
              {showAddTeacher ? <ChevronUp size={16} /> : <UserPlus size={16} />}
              {showAddTeacher ? 'Cancel' : 'Register Teacher'}
            </button>
          </div>

          {showAddTeacher && (
            <div className="px-6 py-4 border-b bg-green-50">
              <form onSubmit={handleAddTeacher} className="grid grid-cols-6 gap-3">
                <input type="text" required placeholder="Name *" value={tchForm.name}
                  onChange={e => setTchForm({...tchForm, name: e.target.value})}
                  className="px-3 py-2 border rounded-lg text-sm outline-none" />
                <input type="email" required placeholder="Email *" value={tchForm.email}
                  onChange={e => setTchForm({...tchForm, email: e.target.value})}
                  className="px-3 py-2 border rounded-lg text-sm outline-none" />
                <input type="password" required placeholder="Password *" value={tchForm.password}
                  onChange={e => setTchForm({...tchForm, password: e.target.value})}
                  className="px-3 py-2 border rounded-lg text-sm outline-none" />
                <input type="text" placeholder="Department" value={tchForm.department}
                  onChange={e => setTchForm({...tchForm, department: e.target.value})}
                  className="px-3 py-2 border rounded-lg text-sm outline-none" />
                <input type="text" placeholder="Employee ID" value={tchForm.employee_id}
                  onChange={e => setTchForm({...tchForm, employee_id: e.target.value})}
                  className="px-3 py-2 border rounded-lg text-sm outline-none" />
                <button type="submit" disabled={loading}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">
                  {loading ? 'Creating...' : 'Create'}
                </button>
              </form>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Email</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Department</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Employee ID</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {teachers.map(t => (
                  <tr key={t.teacher_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{t.name}</td>
                    <td className="px-4 py-3 text-gray-600">{t.email}</td>
                    <td className="px-4 py-3 text-gray-500">{t.department || '-'}</td>
                    <td className="px-4 py-3 text-gray-500">{t.employee_id || '-'}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => handleDeleteTeacher(t.teacher_id)} className="p-1.5 text-red-400 hover:bg-red-50 rounded"><Trash2 size={16} /></button>
                    </td>
                  </tr>
                ))}
                {teachers.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No teachers registered</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
