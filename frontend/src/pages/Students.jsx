import { useState, useEffect } from 'react'
import { Users, Phone, Camera } from 'lucide-react'
import { getStudents } from '../services/api'

export default function Students() {
  const [students, setStudents] = useState([])
  const [total, setTotal] = useState(0)

  useEffect(() => { fetchStudents() }, [])

  const fetchStudents = async () => {
    try {
      const res = await getStudents()
      setStudents(res.data.students)
      setTotal(res.data.total)
    } catch (e) { console.error(e) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Students ({total})</h1>
        <p className="text-sm text-gray-400">Student management is available in the Admin Dashboard</p>
      </div>

      {students.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">
          <Users size={48} className="mx-auto mb-4 opacity-30" />
          <p>No students enrolled yet.</p>
          <p className="text-sm mt-2">Contact the administrator to enroll students.</p>
        </div>
      )}

      {students.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {students.map(s => (
            <div key={s.student_id || s._id} className="bg-white rounded-xl shadow-sm p-5 hover:shadow-md transition">
              <div className="flex items-center gap-4 mb-3">
                <div className="w-14 h-14 rounded-full bg-gray-100 border-2 border-gray-200 flex items-center justify-center overflow-hidden flex-shrink-0">
                  {s.photo_url ? (
                    <img src={s.photo_url} alt={s.name} className="w-full h-full object-cover" />
                  ) : (
                    <Camera size={20} className="text-gray-300" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 truncate">{s.name}</p>
                  <p className="text-sm text-primary-600 font-medium">{s.roll_number}</p>
                </div>
              </div>

              <div className="space-y-1 text-sm text-gray-600">
                <p><span className="text-gray-400">Dept:</span> {s.department || '-'} <span className="text-gray-300 mx-1">|</span> <span className="text-gray-400">Sec:</span> {s.section || '-'} <span className="text-gray-300 mx-1">|</span> <span className="text-gray-400">Sem:</span> {s.semester || '-'}</p>
                {s.mobile_number && (
                  <p className="flex items-center gap-1 text-green-600"><Phone size={12} />{s.mobile_number}</p>
                )}
                {s.parent_mobile && (
                  <p className="flex items-center gap-1 text-blue-600"><Phone size={12} />{s.parent_mobile} <span className="text-xs text-gray-400">(parent)</span></p>
                )}
              </div>

              <div className="pt-2 mt-2 border-t">
                <span className="text-xs text-gray-400">{s.student_id}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
