import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { sitesApi } from '../api'
import type { SiteListItem, SiteListResponse } from '../types'
import { SITE_TYPE_OPTIONS, SERVICE_TYPE_OPTIONS } from '../types'

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'normal', label: '正常' },
  { value: 'expiring', label: '即將到期' },
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

export default function SiteList() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<SiteListResponse | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [q, setQ] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [siteType, setSiteType] = useState('')
  const [serviceType, setServiceType] = useState('')
  const [status, setStatus] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [removeModal, setRemoveModal] = useState<{ site: SiteListItem } | null>(null)
  const [adminTokenInput, setAdminTokenInput] = useState('')
  const [removing, setRemoving] = useState(false)

  const load = () => {
    setLoading(true)
    sitesApi
      .list({
        page,
        page_size: pageSize,
        q: q || undefined,
        site_type: siteType || undefined,
        service_type: serviceType || undefined,
        status: status || undefined,
        include_inactive: includeInactive,
      })
      .then(setData)
      .catch(alert)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [page, pageSize, q, siteType, serviceType, status, includeInactive])

  const handleSearch = () => setQ(searchInput.trim())

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-slate-800">案場清單</h2>
        <div className="flex gap-2">
          <Link to="/sites/new" className="btn-primary">
            新增案場
          </Link>
          <Link to="/sites/history" className="btn-secondary">
            案場歷史紀錄
          </Link>
        </div>
      </div>

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
          <select className="input w-32" value={siteType} onChange={(e) => setSiteType(e.target.value)}>
            <option value="">案場類型</option>
            {SITE_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select className="input w-40" value={serviceType} onChange={(e) => setServiceType(e.target.value)}>
            <option value="">服務類型</option>
            {SERVICE_TYPE_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select className="input w-32" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => setIncludeInactive(e.target.checked)}
            />
            <span>包含已移除</span>
          </label>
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
                  <th className="px-4 py-3 font-medium" title="月服務費（未稅）">月服務費（未稅）</th>
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
                      <td className="px-4 py-2" title={formatMoney(s.monthly_fee_excl_tax)}>{formatMoney(s.monthly_fee_excl_tax)}</td>
                      <td className="px-4 py-2" title={formatMoney(s.monthly_fee_incl_tax)}>{formatMoney(s.monthly_fee_incl_tax)}</td>
                      <td className="px-4 py-2" title={formatMoney(s.current_month_expected_amount)}>{formatMoney(s.current_month_expected_amount)}</td>
                      <td className="px-4 py-2 text-sm" title={invoicePayment}>{invoicePayment}</td>
                      <td className="px-4 py-2" title={s.current_month_received ? '是' : '否'}>{s.current_month_received ? '是' : '否'}</td>
                      <td className="px-4 py-2" title={s.status === 'expired' ? '已到期' : s.status === 'expiring' ? '即將到期' : s.status === 'normal' ? '正常' : s.status === 'inactive' ? '已移除' : '-'}>
                        {s.status === 'expired' && <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">已到期</span>}
                        {s.status === 'expiring' && <span className="px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-800">即將到期</span>}
                        {s.status === 'normal' && <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-600">正常</span>}
                        {s.status === 'inactive' && <span className="px-2 py-0.5 rounded text-xs bg-slate-300 text-slate-700">已移除</span>}
                        {!s.status && s.status !== 'inactive' && '-'}
                      </td>
                      <td className="px-4 py-2 text-right" title={s.is_active === false ? '已移除，操作已停用' : '詳情、編輯、移除'}>
                        {s.is_active === false ? (
                          <>
                            <span className="btn-primary text-sm mr-1 whitespace-nowrap opacity-50 cursor-not-allowed inline-block">詳情</span>
                            <span className="btn-secondary text-sm mr-1 whitespace-nowrap opacity-50 cursor-not-allowed inline-block">編輯</span>
                            <span className="btn-danger text-sm whitespace-nowrap opacity-50 cursor-not-allowed inline-block">移除</span>
                          </>
                        ) : (
                          <>
                            <Link to={`/sites/${s.id}`} className="btn-primary text-sm mr-1 whitespace-nowrap">詳情</Link>
                            <Link to={`/sites/${s.id}/edit`} className="btn-secondary text-sm mr-1 whitespace-nowrap">編輯</Link>
                            <button
                              type="button"
                              className="btn-danger text-sm whitespace-nowrap"
                              onClick={() => setRemoveModal({ site: s })}
                            >
                              移除
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          {!loading && items.length === 0 && (
            <div className="p-8 text-slate-500 text-center">尚無案場資料，或篩選無結果。</div>
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

      {/* 移除案場確認 Modal */}
      {removeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => !removing && setRemoveModal(null)}>
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full mx-4 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-slate-800">移除案場</h3>
            <p className="text-slate-600 text-sm whitespace-pre-line">
              {`是否確定要移除此案場？${removeModal.site.name ? `（${removeModal.site.name}）` : ''}
移除後：
- 案場將不再顯示於列表
- 歷史資料仍保留供查帳與備查
- 不會刪除已產生的帳務、回饋、發票、入帳紀錄`}
            </p>
            <div>
              <label className="label">管理員 Token（必填，與備份還原相同）</label>
              <input
                type="password"
                className="input"
                placeholder="請輸入管理員 Token"
                value={adminTokenInput}
                onChange={(e) => setAdminTokenInput(e.target.value)}
                disabled={removing}
              />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setRemoveModal(null)}
                disabled={removing}
              >
                取消
              </button>
              <button
                type="button"
                className="btn-danger"
                disabled={removing || !adminTokenInput.trim()}
                onClick={() => {
                  setRemoving(true)
                  sitesApi
                    .deactivate(removeModal.site.id, adminTokenInput.trim())
                    .then(() => {
                      setRemoveModal(null)
                      setAdminTokenInput('')
                      load()
                      alert('已移除案場')
                    })
                    .catch((e) => {
                      alert(e instanceof Error ? e.message : '移除失敗')
                    })
                    .finally(() => setRemoving(false))
                }}
              >
                {removing ? '處理中...' : '確定移除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
