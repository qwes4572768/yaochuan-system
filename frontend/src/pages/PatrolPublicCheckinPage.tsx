import { FormEvent, useEffect, useMemo, useState } from 'react'
import { authApi, employeesApi, getAuthToken, patrolApi, setAuthToken } from '../api'
import type { Employee, PatrolCheckinResponse } from '../types'

type Props = {
  publicId: string
}

export default function PatrolPublicCheckinPage({ publicId }: Props) {
  const [token, setTokenState] = useState<string | null>(() => getAuthToken())
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loadingLogin, setLoadingLogin] = useState(false)
  const [employees, setEmployees] = useState<Employee[]>([])
  const [employeeId, setEmployeeId] = useState<number | ''>('')
  const [loadingEmployees, setLoadingEmployees] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PatrolCheckinResponse | null>(null)

  const deviceInfo = useMemo(() => {
    const info = {
      userAgent: navigator.userAgent || '',
      platform: navigator.platform || '',
      language: navigator.language || '',
      screen: `${window.screen.width}x${window.screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    }
    return JSON.stringify(info)
  }, [])

  useEffect(() => {
    if (!token) return
    setLoadingEmployees(true)
    employeesApi.list({ limit: 500 })
      .then((rows) => setEmployees(rows))
      .catch((err) => setError(err instanceof Error ? err.message : '讀取員工失敗'))
      .finally(() => setLoadingEmployees(false))
  }, [token])

  async function onLogin(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoadingLogin(true)
    try {
      const data = await authApi.login(username.trim(), password)
      setAuthToken(data.access_token)
      setTokenState(data.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : '登入失敗')
    } finally {
      setLoadingLogin(false)
    }
  }

  async function onSubmitCheckin(e: FormEvent) {
    e.preventDefault()
    if (!employeeId) {
      setError('請先選擇員工')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      const res = await patrolApi.checkinByPublicId(publicId, {
        employee_id: employeeId,
        device_info: deviceInfo,
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '打卡失敗')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <div className="max-w-xl mx-auto space-y-4">
        <h1 className="text-2xl font-semibold">巡邏打卡</h1>
        <p className="text-sm text-slate-300 break-all">巡邏點 ID：{publicId}</p>
        {error && <p className="text-sm text-rose-300">{error}</p>}

        {!token ? (
          <form onSubmit={onLogin} className="rounded border border-slate-700 bg-slate-900/80 p-4 space-y-3">
            <h2 className="font-semibold">請先登入</h2>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="帳號"
              required
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="密碼"
              required
            />
            <button
              type="submit"
              disabled={loadingLogin}
              className="w-full rounded bg-emerald-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
            >
              {loadingLogin ? '登入中...' : '登入並繼續'}
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmitCheckin} className="rounded border border-slate-700 bg-slate-900/80 p-4 space-y-3">
            <h2 className="font-semibold">完成巡邏</h2>
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value ? Number(e.target.value) : '')}
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              required
            >
              <option value="">請選擇員工</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>{emp.name}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={submitting || loadingEmployees || !employeeId}
              className="w-full rounded bg-sky-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
            >
              {submitting ? '送出中...' : '完成巡邏'}
            </button>
          </form>
        )}

        {result && (
          <div className="rounded border border-emerald-500/50 bg-emerald-500/10 p-3 text-sm">
            <div className="font-semibold">打卡成功</div>
            <div>{result.employee_name}</div>
            <div>{result.point_code} - {result.point_name}</div>
            <div>{result.checkin_date} {result.checkin_ampm} {result.checkin_time}</div>
          </div>
        )}
      </div>
    </div>
  )
}
