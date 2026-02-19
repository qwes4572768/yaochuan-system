import { FormEvent, useEffect, useMemo, useState } from 'react'
import { ApiError, patrolApi } from '../api'
import type { PatrolDeviceBindingAdminItem } from '../types'

/** 格式：yyyy/MM/dd HH:mm，無值回傳 "-" */
function formatDateTime(v?: string): string {
  if (!v) return '-'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  const y = d.getFullYear()
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${y}/${M}/${day} ${h}:${m}`
}

/** 綁定狀態：已綁定 | 未綁定 | 停用 */
function getBindingStatus(
  row: PatrolDeviceBindingAdminItem
): 'bound' | 'unbound' | 'disabled' {
  if (!row.is_active && row.unbound_at) return 'disabled'
  if (row.is_active && row.employee_name?.trim() && row.site_name?.trim()) return 'bound'
  return 'unbound'
}

const BINDING_STATUS_MAP = {
  bound: { label: '已綁定', className: 'bg-emerald-100 text-emerald-800' },
  unbound: { label: '未綁定', className: 'bg-amber-100 text-amber-800' },
  disabled: { label: '停用', className: 'bg-slate-200 text-slate-700' },
} as const

export default function PatrolDeviceBindingsAdminPage() {
  const [rows, setRows] = useState<PatrolDeviceBindingAdminItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [employee, setEmployee] = useState('')
  const [site, setSite] = useState('')
  const [status, setStatus] = useState<'all' | 'active' | 'inactive'>('active')
  /** 詳情 modal：顯示哪一筆的裝置完整資訊（row.id） */
  const [detailRowId, setDetailRowId] = useState<number | null>(null)

  const logsExportUrl = useMemo(() => patrolApi.exportLogsUrl(), [])

  /** status=active 時只顯示已綁定且啟用中的設備；status=all/inactive 顯示 API 回傳的完整資料 */
  const filtered = useMemo(() => {
    if (status !== 'active') return rows
    return rows.filter(
      (item) =>
        item.is_active === true &&
        !!item.bound_at &&
        !item.unbound_at
    )
  }, [rows, status])

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

  /** 裝置 ID 顯示：前 8 碼 + … */
  function shortDeviceId(id: string): string {
    if (!id) return '-'
    return id.length <= 8 ? id : `${id.slice(0, 8)}…`
  }

  function copyFullId(id: string) {
    if (!id) return
    navigator.clipboard.writeText(id).then(
      () => {},
      () => {}
    )
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
    const rowsText = filtered.map((row) => ([
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

  const detailRow = detailRowId != null ? filtered.find((r) => r.id === detailRowId) : null

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">巡邏設備管理</h1>
      <p className="text-sm text-slate-600">管理員可查詢、重設密碼、解除綁定與匯出。</p>

      <form onSubmit={onSearch} className="rounded border border-slate-300 bg-white p-4 grid grid-cols-1 md:grid-cols-5 gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜尋（裝置ID／員工／案場）"
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
          <option value="active">已綁定</option>
          <option value="inactive">已解除</option>
        </select>
        <button type="submit" disabled={loading} className="rounded bg-sky-500 text-white font-semibold px-4 py-2 disabled:opacity-60">
          {loading ? '查詢中...' : '搜尋／篩選'}
        </button>
      </form>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="flex items-center gap-2">
        <div className="text-sm text-slate-600">共 {filtered.length} 筆</div>
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
              <th className="text-left p-2">裝置 ID</th>
              <th className="text-left p-2">員工</th>
              <th className="text-left p-2">案場</th>
              <th className="text-left p-2">綁定狀態</th>
              <th className="text-left p-2">裝置資訊</th>
              <th className="text-left p-2">綁定時間</th>
              <th className="text-left p-2">解除時間</th>
              <th className="text-left p-2">密碼狀態</th>
              <th className="text-left p-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => {
              const bindingStatus = getBindingStatus(row)
              const statusConf = BINDING_STATUS_MAP[bindingStatus]
              return (
                <tr key={row.id} className="border-t border-slate-200 align-top">
                  <td className="p-2">
                    <div className="flex items-center gap-1 flex-wrap">
                      <span className="font-mono text-xs">{shortDeviceId(row.device_public_id)}</span>
                      <button
                        type="button"
                        onClick={() => copyFullId(row.device_public_id)}
                        className="rounded border border-slate-300 px-1.5 py-0.5 text-xs hover:bg-slate-100"
                      >
                        複製完整ID
                      </button>
                    </div>
                  </td>
                  <td className="p-2">{row.employee_name?.trim() || '-'}</td>
                  <td className="p-2">{row.site_name?.trim() || '-'}</td>
                  <td className="p-2">
                    <span className={`inline-block text-xs px-2 py-1 rounded ${statusConf.className}`}>
                      {statusConf.label}
                    </span>
                  </td>
                  <td className="p-2">
                    <div className="flex flex-wrap gap-1 items-center">
                      {(row.platform || row.browser || row.timezone || row.ip_address) && (
                        <>
                          {row.platform && (
                            <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs">
                              {row.platform}
                            </span>
                          )}
                          {row.browser && (
                            <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs">
                              {row.browser}
                            </span>
                          )}
                          {row.timezone && (
                            <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs">
                              {row.timezone}
                            </span>
                          )}
                          {row.ip_address && (
                            <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs">
                              IP:{row.ip_address}
                            </span>
                          )}
                        </>
                      )}
                      <button
                        type="button"
                        onClick={() => setDetailRowId(row.id)}
                        className="rounded border border-sky-300 px-2 py-0.5 text-xs text-sky-700 hover:bg-sky-50"
                      >
                        詳情
                      </button>
                    </div>
                  </td>
                  <td className="p-2">{formatDateTime(row.bound_at)}</td>
                  <td className="p-2 text-slate-500">{formatDateTime(row.unbound_at)}</td>
                  <td className="p-2">{row.password_set ? '已設定' : '未設定'}</td>
                  <td className="p-2 space-y-2">
                    <button
                      type="button"
                      onClick={() => void onResetPassword(row)}
                      className="w-full rounded border border-sky-300 px-2 py-1 text-xs text-sky-700 hover:bg-sky-50"
                    >
                      重設設備密碼
                    </button>
                    <button
                      type="button"
                      onClick={() => void onUnbind(row)}
                      className="w-full rounded border border-rose-300 px-2 py-1 text-xs text-rose-700 hover:bg-rose-50"
                    >
                      解除設備綁定
                    </button>
                  </td>
                </tr>
              )
            })}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={9} className="p-3 text-slate-500">
                  查無裝置綁定資料。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 裝置詳情 Modal */}
      {detailRow != null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setDetailRowId(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="device-detail-title"
        >
          <div
            className="rounded-lg border border-slate-300 bg-white shadow-lg max-w-lg w-full max-h-[80vh] overflow-auto p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="device-detail-title" className="text-lg font-semibold mb-3">
              裝置完整資訊
            </h2>
            <dl className="grid grid-cols-1 gap-2 text-sm">
              <div>
                <dt className="text-slate-500">平台</dt>
                <dd className="font-mono">{detailRow.platform || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">瀏覽器</dt>
                <dd className="font-mono">{detailRow.browser || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">語言</dt>
                <dd className="font-mono">{detailRow.language || detailRow.device_info?.lang || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">螢幕</dt>
                <dd className="font-mono">{detailRow.screen_size || detailRow.screen || detailRow.device_info?.screen || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">時區</dt>
                <dd className="font-mono">{detailRow.timezone || detailRow.device_info?.tz || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">IP</dt>
                <dd className="font-mono">{detailRow.ip_address || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">User-Agent</dt>
                <dd className="font-mono text-xs break-all">{detailRow.ua || detailRow.device_info?.ua || '-'}</dd>
              </div>
            </dl>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setDetailRowId(null)}
                className="rounded bg-slate-200 px-3 py-1.5 text-sm hover:bg-slate-300"
              >
                關閉
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
