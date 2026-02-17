import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { sitesApi } from '../api'
import type { SiteListResponse } from '../types'
import { SITE_TYPE_OPTIONS } from '../types'

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'expired', label: '已到期' },
]

function formatServiceTypes(s: string | undefined): string {
  if (!s) return '-'
  try {
    const arr = JSON.parse(s) as string[]
    return Array.isArray(arr) ? arr.join('、') : s
  } catch {
    return s
  }
}

function formatMoney(v: number | string | undefined | null): string {
  if (v === undefined || v === null || v === '') return '-'
  const n = Number(v)
  return Number.isNaN(n) ? '-' : n.toLocaleString()
}

export default function SiteHistory() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<SiteListResponse | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [q, setQ] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [status, setStatus] = useState('')

  const load = () => {
    setLoading(true)
    sitesApi
      .history({ page, page_size: pageSize, q: q || undefined, status: status || undefined })
      .then(setData)
      .catch(alert)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [page, pageSize, q, status])

  const handleSearch = () => setQ(searchInput.trim())

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-slate-800">案場歷史紀錄</h2>
        <Link to="/sites" className="btn-secondary">
          返回案場清單
        </Link>
      </div>

      <p className="text-slate-600 text-sm">
        僅顯示「到期且未續約」自動歸檔的案場；手動移除的案場不在此列表。可查看詳情與歷史資料（回饋、入帳、合約附件等）。
      </p>

      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            className="input w-52"
            placeholder="案場名稱 / 地址 / 客戶名稱"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button type="button" onClick={handleSearch} className="btn-primary">
            搜尋
          </button>
          <select className="input w-32" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          {loading && items.length === 0 ? (
            <div className="p-8 text-slate-500">載入中...</div>
          ) : (
            <table className="w-full text-left table-nowrap">
              <thead className="bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium" title="案場名稱">案場名稱</th>
                  <th className="px-4 py-3 font-medium" title="案場類型">案場類型</th>
                  <th className="px-4 py-3 font-medium" title="服務類型">服務類型</th>
                  <th className="px-4 py-3 font-medium" title="契約起～迄">契約起～迄</th>
                  <th className="px-4 py-3 font-medium" title="月服務費（含稅）">月服務費（含稅）</th>
                  <th className="px-4 py-3 font-medium" title="本月應收">本月應收</th>
                  <th className="px-4 py-3 font-medium" title="發票/收款期限">發票/收款期限</th>
                  <th className="px-4 py-3 font-medium" title="本月已入帳">本月已入帳</th>
                  <th className="px-4 py-3 font-medium" title="狀態">狀態</th>
                  <th className="px-4 py-3 font-medium text-right" title="操作">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((s) => {
                  const siteName = s.name ?? '-'
                  const serviceTypesStr = formatServiceTypes(s.service_types)
                  const contractRange = `${s.contract_start ?? '-'} ～ ${s.contract_end ?? '-'}`
                  const invoicePayment = `${s.invoice_due_day ?? '-'} 號 / ${s.payment_due_day ?? '-'} 號`
                  return (
                    <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2" title={siteName}>
                        <Link to={`/sites/${s.id}`} className="text-indigo-600 hover:underline font-medium">
                          {siteName}
                        </Link>
                      </td>
                      <td className="px-4 py-2" title={SITE_TYPE_OPTIONS.find((o) => o.value === s.site_type)?.label ?? s.site_type ?? '-'}>
                        {SITE_TYPE_OPTIONS.find((o) => o.value === s.site_type)?.label ?? s.site_type ?? '-'}
                      </td>
                      <td className="px-4 py-2 text-sm" title={serviceTypesStr}>{serviceTypesStr}</td>
                      <td className="px-4 py-2" title={contractRange}>{contractRange}</td>
                      <td className="px-4 py-2" title={formatMoney(s.monthly_fee_incl_tax)}>{formatMoney(s.monthly_fee_incl_tax)}</td>
                      <td className="px-4 py-2" title={formatMoney(s.current_month_expected_amount)}>{formatMoney(s.current_month_expected_amount)}</td>
                      <td className="px-4 py-2 text-sm" title={invoicePayment}>{invoicePayment}</td>
                      <td className="px-4 py-2" title={s.current_month_received ? '是' : '否'}>{s.current_month_received ? '是' : '否'}</td>
                      <td className="px-4 py-2">
                        {s.status === 'expired' && <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">已到期</span>}
                        {s.status === 'inactive' && <span className="px-2 py-0.5 rounded text-xs bg-slate-300 text-slate-700">已移除</span>}
                        {!s.status && '-'}
                      </td>
                      <td className="px-4 py-2 text-right" title="查看詳情">
                        <Link to={`/sites/${s.id}`} className="btn-primary text-sm whitespace-nowrap">
                          查看詳情
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          {!loading && items.length === 0 && (
            <div className="p-8 text-slate-500 text-center">尚無歷史案場資料，或篩選無結果。</div>
          )}
        </div>
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-slate-200 flex items-center justify-between">
            <span className="text-sm text-slate-600">共 {total} 筆</span>
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-secondary text-sm disabled:opacity-50"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                上一頁
              </button>
              <span className="py-2 text-sm">第 {page} / {totalPages} 頁</span>
              <button
                type="button"
                className="btn-secondary text-sm disabled:opacity-50"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                下一頁
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
