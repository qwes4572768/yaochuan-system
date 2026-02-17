import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { employeesApi } from '../api'
import { REGISTRATION_OPTIONS, registrationTypeLabel, type RegistrationType } from '../constants/registrationType'
import { maskNationalId } from '../utils/mask'
import type { Employee } from '../types'

type RegistrationFilter = 'all' | RegistrationType

export default function EmployeeList() {
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<RegistrationFilter>('all')
  const [allList, setAllList] = useState<Employee[]>([])

  const loadList = () => {
    setLoading(true)
    const params: { limit: number; registration_type?: 'security' | 'property' | 'smith' | 'lixiang' } = { limit: 500 }
    if (filter !== 'all') params.registration_type = filter
    employeesApi.list(params)
      .then((data) => {
        setAllList(data)
        if (import.meta.env.DEV) {
          const responseTypes = Array.from(new Set((data || []).map((e) => e.registration_type || 'security')))
          console.debug('[EmployeeList] registration filter options =', REGISTRATION_OPTIONS)
          console.debug('[EmployeeList] API registration_type values =', responseTypes)
        }
      })
      .catch(alert)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadList()
  }, [filter])

  const q = search.trim().toLowerCase()
  const list = q
    ? allList.filter((e) => {
        if (e.name && e.name.toLowerCase().includes(q)) return true
        const id = e.national_id || ""
        if (q.length === 4 && id.length >= 4 && id.slice(-4) === q) return true
        return false
      })
    : allList

  if (loading && list.length === 0) return <div className="text-slate-500">載入中...</div>

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-slate-800">員工清單</h2>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-600">登載身份：</span>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 rounded text-sm ${filter === 'all' ? 'bg-slate-700 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}`}
            >
              全部
            </button>
            {REGISTRATION_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setFilter(opt.key)}
                className={`px-3 py-1.5 rounded text-sm ${filter === opt.key ? 'bg-slate-700 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <input
            type="text"
            className="input w-52"
            placeholder="搜尋姓名或身分證後四碼"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          />
        </div>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-100 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">員工編號</th>
                <th className="px-4 py-3 font-medium">登載身份</th>
                <th className="px-4 py-3 font-medium">姓名</th>
                <th className="px-4 py-3 font-medium">身分證字號</th>
                <th className="px-4 py-3 font-medium">出生年月日</th>
                <th className="px-4 py-3 font-medium">投保薪資級距</th>
                <th className="px-4 py-3 font-medium">加保日期</th>
                <th className="px-4 py-3 font-medium">眷屬數量</th>
                <th className="px-4 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {list.map((e) => (
                <tr key={e.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2">{e.id}</td>
                  <td className="px-4 py-2">{registrationTypeLabel(e.registration_type)}</td>
                  <td className="px-4 py-2">{e.name}</td>
                  <td className="px-4 py-2">{e.national_id ? maskNationalId(e.national_id) : '-'}</td>
                  <td className="px-4 py-2">{e.birth_date || '-'}</td>
                  <td className="px-4 py-2">{e.insured_salary_level != null ? Number(e.insured_salary_level) : '-'}</td>
                  <td className="px-4 py-2">{e.enroll_date || '-'}</td>
                  <td className="px-4 py-2">{e.dependent_count ?? 0}</td>
                  <td className="px-4 py-2 text-right">
                    <Link to={`/employees/${e.id}`} className="btn-primary text-sm">
                      檢視
                    </Link>
                    <Link to={`/employees/${e.id}/edit`} className="btn-secondary text-sm ml-2">
                      編輯
                    </Link>
                    <button
                      type="button"
                      className="text-red-600 text-sm ml-2 hover:underline"
                      onClick={() => {
                        if (window.confirm(`確定要刪除「${e.name}」？`)) {
                          employeesApi.delete(e.id!).then(() => loadList()).catch(alert)
                        }
                      }}
                    >
                      刪除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {list.length === 0 && (
          <div className="py-12 text-center text-slate-500">尚無員工資料，請先新增員工。</div>
        )}
      </div>
    </div>
  )
}
