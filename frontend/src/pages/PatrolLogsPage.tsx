import { useEffect, useState } from 'react'
import { downloadReportExcel, patrolApi } from '../api'
import type { PatrolLog } from '../types'

const TZ = 'Asia/Taipei'

/** 依 Asia/Taipei 將 checkin_at 格式為：時段（早上/下午/晚上）+ 12 小時制 hh:mm:ss */
function formatCheckinAt(checkinAt: string | undefined): { period: string; time12: string } {
  const fallback = { period: '-', time12: '-' }
  if (!checkinAt) return fallback
  const date = new Date(checkinAt)
  if (Number.isNaN(date.getTime())) return fallback
  const formatter = new Intl.DateTimeFormat('zh-TW', {
    timeZone: TZ,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
  const parts = formatter.formatToParts(date)
  const hour = parts.find((p) => p.type === 'hour')?.value ?? '0'
  const minute = parts.find((p) => p.type === 'minute')?.value ?? '00'
  const second = parts.find((p) => p.type === 'second')?.value ?? '00'
  const h = parseInt(hour, 10)
  const period = h < 12 ? '早上' : h < 18 ? '下午' : '晚上'
  const h12 = h % 12
  const h12Display = h12 === 0 ? 12 : h12
  const time12 = `${String(h12Display).padStart(2, '0')}:${minute}:${second}`
  return { period, time12 }
}

export default function PatrolLogsPage() {
  const [rows, setRows] = useState<PatrolLog[]>([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [employeeName, setEmployeeName] = useState('')
  const [siteName, setSiteName] = useState('')
  const [pointCode, setPointCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function query() {
    setLoading(true)
    setError('')
    try {
      const list = await patrolApi.listLogs({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        employee_name: employeeName || undefined,
        site_name: siteName || undefined,
        point_code: pointCode || undefined,
        limit: 1000,
      })
      setRows(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : '讀取失敗')
    } finally {
      setLoading(false)
    }
  }

  async function exportExcel() {
    try {
      await downloadReportExcel(
        patrolApi.exportLogsUrl({
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          employee_name: employeeName || undefined,
          site_name: siteName || undefined,
          point_code: pointCode || undefined,
        }),
        `patrol_logs_${new Date().toISOString().slice(0, 10)}.xlsx`
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : '匯出失敗')
    }
  }

  useEffect(() => {
    void query()
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">巡邏紀錄</h1>
      <div className="rounded border border-slate-300 bg-white p-3 grid grid-cols-1 md:grid-cols-6 gap-2">
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
        <input value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} placeholder="員工" className="rounded border border-slate-300 px-2 py-1" />
        <input value={siteName} onChange={(e) => setSiteName(e.target.value)} placeholder="案場" className="rounded border border-slate-300 px-2 py-1" />
        <input value={pointCode} onChange={(e) => setPointCode(e.target.value)} placeholder="點位編號" className="rounded border border-slate-300 px-2 py-1" />
        <div className="flex gap-2">
          <button onClick={() => void query()} className="rounded bg-sky-500 text-white px-3 py-1">查詢</button>
          <button onClick={() => void exportExcel()} className="rounded bg-emerald-500 text-slate-950 px-3 py-1 font-semibold">匯出 Excel</button>
        </div>
      </div>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="rounded border border-slate-300 bg-white overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="text-left p-2">員工</th>
              <th className="text-left p-2">日期</th>
              <th className="text-left p-2">時段</th>
              <th className="text-left p-2">時間</th>
              <th className="text-left p-2">案場</th>
              <th className="text-left p-2">巡邏點</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const { period, time12 } = formatCheckinAt(r.checkin_at)
              return (
                <tr key={r.id} className="border-t border-slate-200">
                  <td className="p-2">{r.employee_name}</td>
                  <td className="p-2">{r.checkin_date}</td>
                  <td className="p-2">{period}</td>
                  <td className="p-2">{time12}</td>
                  <td className="p-2">{r.site_name}</td>
                  <td className="p-2">{r.point_code} - {r.point_name}</td>
                </tr>
              )
            })}
            {!loading && rows.length === 0 && <tr><td className="p-3 text-slate-500" colSpan={6}>查無資料</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
