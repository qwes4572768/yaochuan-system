import { FormEvent, useEffect, useState } from 'react'
import { formatApiError, patrolApi } from '../api'
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
      setError(formatApiError(err, '讀取裝置綁定列表失敗'))
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
      setError(formatApiError(err, '重設密碼失敗'))
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
      setError(formatApiError(err, '解除綁定失敗'))
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">巡邏裝置綁定後台管理</h1>
      <p className="text-sm text-slate-600">可檢視綁定狀態、重設密碼與解除綁定（不顯示明碼）。</p>

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
      <div className="text-sm text-slate-600">共 {total} 筆</div>

      <div className="rounded border border-slate-300 bg-white overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="text-left p-2">devicePublicId</th>
              <th className="text-left p-2">狀態</th>
              <th className="text-left p-2">員工 / 案場</th>
              <th className="text-left p-2">bound_at / last_seen_at</th>
              <th className="text-left p-2">裝置資訊</th>
              <th className="text-left p-2">密碼</th>
              <th className="text-left p-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-200 align-top">
                <td className="p-2">
                  <div className="font-mono text-xs break-all max-w-[220px]">{row.device_public_id}</div>
                </td>
                <td className="p-2">
                  <span className={`text-xs px-2 py-1 rounded ${row.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}>
                    {row.is_active ? 'is_active' : 'inactive'}
                  </span>
                </td>
                <td className="p-2">
                  <div>{row.employee_name || '-'}</div>
                  <div className="text-slate-500">{row.site_name || '-'}</div>
                </td>
                <td className="p-2">
                  <div>{row.bound_at ? new Date(row.bound_at).toLocaleString() : '-'}</div>
                  <div className="text-slate-500">{row.last_seen_at ? new Date(row.last_seen_at).toLocaleString() : '-'}</div>
                </td>
                <td className="p-2">
                  <div className="text-xs break-all">UA: {row.ua || '-'}</div>
                  <div className="text-xs">平台: {row.platform || '-'} / {row.browser || '-'}</div>
                  <div className="text-xs">語言: {row.language || '-'} / 時區: {row.timezone || '-'}</div>
                  <div className="text-xs">螢幕: {row.screen || '-'}</div>
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
                <td colSpan={7} className="p-3 text-slate-500">查無裝置綁定資料。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
