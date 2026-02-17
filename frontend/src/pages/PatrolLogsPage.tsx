import { useEffect, useState } from 'react'
import { downloadReportExcel, patrolApi } from '../api'
import type { PatrolLog } from '../types'

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
              <th className="text-left p-2">上午/下午</th>
              <th className="text-left p-2">時分秒</th>
              <th className="text-left p-2">案場</th>
              <th className="text-left p-2">巡邏點</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-slate-200">
                <td className="p-2">{r.employee_name}</td>
                <td className="p-2">{r.checkin_date}</td>
                <td className="p-2">{r.checkin_ampm}</td>
                <td className="p-2">{r.checkin_time}</td>
                <td className="p-2">{r.site_name}</td>
                <td className="p-2">{r.point_code} - {r.point_name}</td>
              </tr>
            ))}
            {!loading && rows.length === 0 && <tr><td className="p-3 text-slate-500" colSpan={6}>查無資料</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
