import { FormEvent, useEffect, useMemo, useState } from 'react'
import { ApiError, patrolApi } from '../api'
import type { PatrolDeviceBindingAdminItem } from '../types'

export default function PatrolDeviceBindingsAdminPage() {
  const [rows, setRows] = useState<PatrolDeviceBindingAdminItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [employee, setEmployee] = useState('')
  const [site, setSite] = useState('')
  const [status, setStatus] = useState<'all' | 'active' | 'inactive'>('all')
  const [total, setTotal] = useState(0)

  const logsExportUrl = useMemo(() => patrolApi.exportLogsUrl(), [])

  function formatErrorWithDetail(err: unknown, fallback: string): string {
    if (err instanceof ApiError) {
      const status = err.status ?? 'unknown'
      const detail = err.rawDetail || err.message || fallback
      if (status === 401 || status === 403) {
        return '請先登入管理系統'
      }
      return `status=${status} detail=${detail}`
    }
    if (err instanceof Error) return err.message || fallback
    return fallback
  }

  function toDisplayTime(v?: string): string {
    if (!v) return '-'
    const d = new Date(v)
    return Number.isNaN(d.getTime()) ? v : d.toLocaleString()
  }

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await patrolApi.listDeviceBindings({
        query,
        employee_name: employee,
        site_name: site,
        status,
        limit: 500,
      })
      setRows(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(formatErrorWithDetail(err, '讀取裝置綁定列表失敗'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function onSearch(e: FormEvent) {
    e.preventDefault()
    await load()
  }

  async function onResetPassword(row: PatrolDeviceBindingAdminItem) {
    const password = window.prompt(`請輸入新密碼（裝置：${row.device_public_id}）`)
    if (!password || !password.trim()) return
    setError('')
    try {
      await patrolApi.resetDeviceBindingPassword(row.id, password.trim())
      await load()
    } catch (err) {
      setError(formatErrorWithDetail(err, '重設密碼失敗'))
    }
  }

  async function onUnbind(row: PatrolDeviceBindingAdminItem) {
    const ok = window.confirm(`確定解除綁定？\n裝置：${row.device_public_id}\n員工：${row.employee_name || '-'}`)
    if (!ok) return
    setError('')
    try {
      await patrolApi.adminUnbindDeviceBinding(row.id)
      await load()
    } catch (err) {
      setError(formatErrorWithDetail(err, '解除綁定失敗'))
    }
  }

  function onExportCsv() {
    const headers = [
      'binding_id',
      'device_public_id',
      'employee_name',
      'site_name',
      'platform',
      'browser',
      'language',
      'screen_size',
      'timezone',
      'ip_address',
      'is_active',
      'bound_at',
      'unbound_at',
    ]
    const escapeCell = (value: unknown) => {
      const text = String(value ?? '')
      if (text.includes('"') || text.includes(',') || text.includes('\n')) {
        return `"${text.replace(/"/g, '""')}"`
      }
      return text
    }
    const rowsText = rows.map((row) => ([
      row.binding_id ?? row.id,
      row.device_public_id,
      row.employee_name ?? '',
      row.site_name ?? '',
      row.platform ?? '',
      row.browser ?? '',
      row.language ?? '',
      row.screen_size ?? row.screen ?? '',
      row.timezone ?? '',
      row.ip_address ?? '',
      row.is_active ? 'true' : 'false',
      row.bound_at ?? '',
      row.unbound_at ?? '',
    ].map(escapeCell).join(',')))
    const csv = '\uFEFF' + [headers.join(','), ...rowsText].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `patrol_device_bindings_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">巡邏設備管理</h1>
      <p className="text-sm text-slate-600">管理員可查詢、重設密碼、解除綁定與匯出。</p>

      <form onSubmit={onSearch} className="rounded border border-slate-300 bg-white p-4 grid grid-cols-1 md:grid-cols-5 gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜尋（裝置ID/員工/案場）"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <input
          value={employee}
          onChange={(e) => setEmployee(e.target.value)}
          placeholder="員工"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <input
          value={site}
          onChange={(e) => setSite(e.target.value)}
          placeholder="案場"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as 'all' | 'active' | 'inactive')}
          className="rounded border border-slate-300 px-3 py-2"
        >
          <option value="all">全部狀態</option>
          <option value="active">啟用中</option>
          <option value="inactive">已解除</option>
        </select>
        <button type="submit" disabled={loading} className="rounded bg-sky-500 text-white font-semibold px-4 py-2 disabled:opacity-60">
          {loading ? '查詢中...' : '搜尋/篩選'}
        </button>
      </form>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="flex items-center gap-2">
        <div className="text-sm text-slate-600">共 {total} 筆</div>
        <button
          type="button"
          onClick={onExportCsv}
          className="rounded border border-slate-300 px-3 py-1.5 text-xs"
        >
          匯出綁定清單 CSV
        </button>
        <a
          href={logsExportUrl}
          target="_blank"
          rel="noreferrer"
          className="rounded border border-sky-300 px-3 py-1.5 text-xs text-sky-700"
        >
          匯出巡邏紀錄 Excel
        </a>
      </div>

      <div className="rounded border border-slate-300 bg-white overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="text-left p-2">binding_id</th>
              <th className="text-left p-2">device_public_id</th>
              <th className="text-left p-2">employee_name</th>
              <th className="text-left p-2">site_name</th>
              <th className="text-left p-2">裝置資訊</th>
              <th className="text-left p-2">is_active</th>
              <th className="text-left p-2">bound_at / unbound_at</th>
              <th className="text-left p-2">密碼</th>
              <th className="text-left p-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-200 align-top">
                <td className="p-2">
                  <div className="font-mono text-xs">{row.binding_id ?? row.id}</div>
                </td>
                <td className="p-2">
                  <div className="font-mono text-xs break-all max-w-[220px]">{row.device_public_id}</div>
                </td>
                <td className="p-2">
                  <div>{row.employee_name || '-'}</div>
                </td>
                <td className="p-2">
                  <div>{row.site_name || '-'}</div>
                </td>
                <td className="p-2">
                  <div className="text-xs">platform: {row.platform || '-'}</div>
                  <div className="text-xs">browser: {row.browser || '-'}</div>
                  <div className="text-xs">language: {row.language || '-'}</div>
                  <div className="text-xs">screen_size: {row.screen_size || row.screen || '-'}</div>
                  <div className="text-xs">timezone: {row.timezone || '-'}</div>
                  <div className="text-xs">ip_address: {row.ip_address || '-'}</div>
                </td>
                <td className="p-2">
                  <span className={`text-xs px-2 py-1 rounded ${row.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}>
                    {row.is_active ? 'true' : 'false'}
                  </span>
                </td>
                <td className="p-2">
                  <div>{toDisplayTime(row.bound_at)}</div>
                  <div className="text-slate-500">{toDisplayTime(row.unbound_at)}</div>
                </td>
                <td className="p-2">{row.password_set ? '已設定' : '未設定'}</td>
                <td className="p-2 space-y-2">
                  <button
                    type="button"
                    onClick={() => void onResetPassword(row)}
                    className="w-full rounded border border-sky-300 px-2 py-1 text-xs text-sky-700"
                  >
                    重設密碼
                  </button>
                  <button
                    type="button"
                    onClick={() => void onUnbind(row)}
                    className="w-full rounded border border-rose-300 px-2 py-1 text-xs text-rose-700"
                  >
                    解除綁定
                  </button>
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={9} className="p-3 text-slate-500">查無裝置綁定資料。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
