import { useEffect, useState, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { sitesApi, rebatesApi, monthlyReceiptsApi } from '../api'
import type { Site, SiteRebate, SiteRebateCreate, SiteMonthlyReceipt } from '../types'
import { SITE_TYPE_OPTIONS } from '../types'

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

export default function SiteDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [site, setSite] = useState<Site | null>(null)
  const [rebates, setRebates] = useState<SiteRebate[]>([])
  const [monthlyReceipts, setMonthlyReceipts] = useState<SiteMonthlyReceipt[]>([])
  const [rebatesLoading, setRebatesLoading] = useState(false)
  const [receiptsLoading, setReceiptsLoading] = useState(false)
  const [monthlyYear, setMonthlyYear] = useState(new Date().getFullYear())
  const [removeModal, setRemoveModal] = useState(false)
  const [adminTokenInput, setAdminTokenInput] = useState('')
  const [removing, setRemoving] = useState(false)
  const [addRebateModal, setAddRebateModal] = useState(false)
  const [editRebateModal, setEditRebateModal] = useState<SiteRebate | null>(null)
  const [rebateForm, setRebateForm] = useState<SiteRebateCreate>({ item_name: '', is_completed: false })
  const [savingRebate, setSavingRebate] = useState(false)
  const [generatingMonths, setGeneratingMonths] = useState(false)
  const [editReceiptModal, setEditReceiptModal] = useState<SiteMonthlyReceipt | null>(null)
  const receiptFileRef = useRef<Record<number, HTMLInputElement | null>>({})
  const proofFileRef = useRef<Record<number, HTMLInputElement | null>>({})

  const siteId = id && id !== 'new' ? Number(id) : 0

  useEffect(() => {
    if (!siteId) return
    sitesApi
      .get(siteId)
      .then(setSite)
      .catch(alert)
      .finally(() => setLoading(false))
  }, [siteId])

  const loadRebates = () => {
    if (!siteId) return
    setRebatesLoading(true)
    sitesApi
      .listRebates(siteId)
      .then(setRebates)
      .catch(alert)
      .finally(() => setRebatesLoading(false))
  }

  const loadMonthlyReceipts = () => {
    if (!siteId) return
    setReceiptsLoading(true)
    sitesApi
      .listMonthlyReceipts(siteId, monthlyYear)
      .then(setMonthlyReceipts)
      .catch(alert)
      .finally(() => setReceiptsLoading(false))
  }

  useEffect(() => {
    if (siteId) loadRebates()
  }, [siteId])
  useEffect(() => {
    if (siteId) loadMonthlyReceipts()
  }, [siteId, monthlyYear])

  if (loading && !site) return <div className="text-slate-500">載入中...</div>
  if (!site) return <div className="text-slate-500">案場不存在</div>

  const isInactive = site.is_active === false
  const isArchived = site.is_archived === true

  return (
    <div className="space-y-6">
      {isArchived && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded-lg text-sm flex items-center gap-2">
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-200">歷史案場</span>
          <span>此案場為歷史案場（到期未續約），僅供查閱；無法編輯。可查看合約附件、回饋項目、每月入帳等資料。</span>
        </div>
      )}
      {isInactive && !isArchived && (
        <div className="bg-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm">
          此案場已移除，僅供查閱；無法編輯或再次移除。
        </div>
      )}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          {site.name}
          {isArchived && <span className="px-2 py-0.5 rounded text-sm font-normal bg-amber-100 text-amber-800">歷史案場</span>}
        </h2>
        <div className="flex gap-2">
          {isInactive ? (
            <span className="btn-primary opacity-50 cursor-not-allowed inline-block">編輯</span>
          ) : (
            <Link to={`/sites/${id}/edit`} className="btn-primary">
              編輯
            </Link>
          )}
          {!isInactive && (
            <button type="button" className="btn-danger" onClick={() => setRemoveModal(true)}>
              移除
            </button>
          )}
          <Link to={isArchived ? "/sites/history" : "/sites"} className="btn-secondary">
            {isArchived ? "返回歷史紀錄" : "返回清單"}
          </Link>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">基本資料</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">案場名稱</dt>
            <dd className="font-medium">{site.name}</dd>
          </div>
          <div>
            <dt className="text-slate-500">案場地址</dt>
            <dd>{site.address ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">案場類型</dt>
            <dd>{SITE_TYPE_OPTIONS.find((o) => o.value === site.site_type)?.label ?? site.site_type ?? '-'}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">服務類型</dt>
            <dd>{formatServiceTypes(site.service_types)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">契約起日</dt>
            <dd>{site.contract_start ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">契約迄日</dt>
            <dd>{site.contract_end ?? '-'}</dd>
          </div>
        </dl>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">費用與稅額</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">月服務費未稅</dt>
            <dd>{formatMoney(site.monthly_fee_excl_tax)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">稅率</dt>
            <dd>{site.tax_rate != null ? Number(site.tax_rate) * 100 : '-'}%</dd>
          </div>
          <div>
            <dt className="text-slate-500">月服務費含稅</dt>
            <dd>{formatMoney(site.monthly_fee_incl_tax)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">發票期限日</dt>
            <dd>{site.invoice_due_day != null ? `每月 ${site.invoice_due_day} 號前` : '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">收款期限日</dt>
            <dd>{site.payment_due_day != null ? `每月 ${site.payment_due_day} 號前` : '-'}</dd>
          </div>
        </dl>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">客戶資料</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">客戶名稱</dt>
            <dd>{site.customer_name ?? site.client_name ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">統一編號</dt>
            <dd>{site.customer_tax_id ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">聯絡人</dt>
            <dd>{site.customer_contact ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">電話</dt>
            <dd>{site.customer_phone ?? '-'}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Email</dt>
            <dd>{site.customer_email ?? '-'}</dd>
          </div>
        </dl>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">發票資訊</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="sm:col-span-2">
            <dt className="text-slate-500">發票抬頭</dt>
            <dd>{site.invoice_title ?? '-'}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">郵寄地址</dt>
            <dd>{site.invoice_mail_address ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">收件人</dt>
            <dd>{site.invoice_receiver ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-slate-500">契約到期提醒天數</dt>
            <dd>{site.remind_days ?? 30} 天</dd>
          </div>
        </dl>
      </div>

      {/* A) 案場回饋 */}
      <div className="card p-6">
        <div className="flex items-center justify-between border-b pb-2 mb-4">
          <h3 className="font-semibold text-slate-700">案場回饋</h3>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              setRebateForm({ item_name: '', is_completed: false })
              setAddRebateModal(true)
            }}
          >
            新增回饋
          </button>
        </div>
        {rebatesLoading ? (
          <p className="text-slate-500 text-sm">載入中...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-600 border-b">
                  <th className="py-2 pr-2">回饋日期</th>
                  <th className="py-2 pr-2">回饋項目</th>
                  <th className="py-2 pr-2">金額</th>
                  <th className="py-2 pr-2">是否完成</th>
                  <th className="py-2 pr-2">備註</th>
                  <th className="py-2 pr-2">回饋依據 PDF</th>
                  <th className="py-2 pr-2 w-24">操作</th>
                </tr>
              </thead>
              <tbody>
                {rebates.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-4 text-slate-500 text-center">
                      尚無回饋紀錄
                    </td>
                  </tr>
                ) : (
                  rebates.map((r) => (
                    <tr key={r.id} className="border-b border-slate-100">
                      <td className="py-2 pr-2">{r.completed_date ?? '-'}</td>
                      <td className="py-2 pr-2">{r.item_name}</td>
                      <td className="py-2 pr-2">{formatMoney(r.cost_amount)}</td>
                      <td className="py-2 pr-2">{r.is_completed ? '是' : '否'}</td>
                      <td className="py-2 pr-2 max-w-[120px] truncate" title={r.notes ?? ''}>
                        {r.notes ?? '-'}
                      </td>
                      <td className="py-2 pr-2">
                        {r.receipt_pdf_path ? (
                          <span className="flex items-center gap-1 flex-wrap">
                            <a
                              href={rebatesApi.receiptUrl(r.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline"
                            >
                              預覽
                            </a>
                            <a
                              href={rebatesApi.receiptUrl(r.id)}
                              download
                              className="text-blue-600 hover:underline"
                            >
                              下載
                            </a>
                            <label className="cursor-pointer text-blue-600 hover:underline">
                              更換
                              <input
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                ref={(el) => {
                                  receiptFileRef.current[r.id] = el
                                }}
                                onChange={(e) => {
                                  const f = e.target.files?.[0]
                                  if (!f) return
                                  rebatesApi
                                    .uploadReceipt(r.id, f)
                                    .then(() => {
                                      loadRebates()
                                      e.target.value = ''
                                    })
                                    .catch(alert)
                                }}
                              />
                            </label>
                          </span>
                        ) : (
                          <label className="cursor-pointer text-blue-600 hover:underline">
                            上傳 PDF
                            <input
                              type="file"
                              accept=".pdf"
                              className="hidden"
                              ref={(el) => {
                                receiptFileRef.current[r.id] = el
                              }}
                              onChange={(e) => {
                                const f = e.target.files?.[0]
                                if (!f) return
                                rebatesApi
                                  .uploadReceipt(r.id, f)
                                  .then(() => {
                                    loadRebates()
                                    e.target.value = ''
                                  })
                                  .catch(alert)
                              }}
                            />
                          </label>
                        )}
                      </td>
                      <td className="py-2 pr-2">
                        <button
                          type="button"
                          className="text-blue-600 hover:underline text-xs mr-2"
                          onClick={() => {
                            setEditRebateModal(r)
                            setRebateForm({
                              item_name: r.item_name,
                              is_completed: r.is_completed,
                              completed_date: r.completed_date ?? undefined,
                              cost_amount: r.cost_amount != null ? Number(r.cost_amount) : undefined,
                              notes: r.notes ?? undefined,
                            })
                          }}
                        >
                          編輯
                        </button>
                        <button
                          type="button"
                          className="text-red-600 hover:underline text-xs"
                          onClick={() => {
                            if (!window.confirm('確定要刪除此筆回饋紀錄？')) return
                            rebatesApi.delete(r.id).then(loadRebates).catch(alert)
                          }}
                        >
                          刪除
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* B) 每月收款/入帳 */}
      <div className="card p-6">
        <div className="flex items-center justify-between border-b pb-2 mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-700">每月入帳</h3>
            <select
              className="input w-24 py-1 text-sm"
              value={monthlyYear}
              onChange={(e) => setMonthlyYear(Number(e.target.value))}
            >
              {[new Date().getFullYear(), new Date().getFullYear() - 1, new Date().getFullYear() - 2].map((y) => (
                <option key={y} value={y}>
                  {y} 年
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="btn-secondary"
            disabled={generatingMonths}
            onClick={() => {
              setGeneratingMonths(true)
              sitesApi
                .createMonthlyReceipt(siteId, { year: monthlyYear })
                .then(() => {
                  loadMonthlyReceipts()
                  alert('已產生該年度 1～12 月入帳紀錄（已存在的月份不會重複建立）')
                })
                .catch(alert)
                .finally(() => setGeneratingMonths(false))
            }}
          >
            {generatingMonths ? '處理中...' : `一鍵產生 ${monthlyYear} 年月份`}
          </button>
        </div>
        {receiptsLoading ? (
          <p className="text-slate-500 text-sm">載入中...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-600 border-b">
                  <th className="py-2 pr-2">月份</th>
                  <th className="py-2 pr-2">應收金額</th>
                  <th className="py-2 pr-2">已入帳</th>
                  <th className="py-2 pr-2">入帳日期</th>
                  <th className="py-2 pr-2">實收金額</th>
                  <th className="py-2 pr-2">付款方式</th>
                  <th className="py-2 pr-2">備註</th>
                  <th className="py-2 pr-2">匯款證明 PDF</th>
                  <th className="py-2 pr-2 w-20">操作</th>
                </tr>
              </thead>
              <tbody>
                {monthlyReceipts.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-4 text-slate-500 text-center">
                      尚無入帳紀錄，可點「一鍵產生今年月份」建立
                    </td>
                  </tr>
                ) : (
                  monthlyReceipts.map((rec) => (
                    <tr key={rec.id} className="border-b border-slate-100">
                      <td className="py-2 pr-2">{rec.billing_month}</td>
                      <td className="py-2 pr-2">{formatMoney(rec.expected_amount)}</td>
                      <td className="py-2 pr-2">{rec.is_received ? '是' : '否'}</td>
                      <td className="py-2 pr-2">{rec.received_date ?? '-'}</td>
                      <td className="py-2 pr-2">{formatMoney(rec.received_amount)}</td>
                      <td className="py-2 pr-2">{rec.payment_method ?? '-'}</td>
                      <td className="py-2 pr-2 max-w-[100px] truncate" title={rec.notes ?? ''}>
                        {rec.notes ?? '-'}
                      </td>
                      <td className="py-2 pr-2">
                        {rec.proof_pdf_path ? (
                          <span className="flex items-center gap-1 flex-wrap">
                            <a
                              href={monthlyReceiptsApi.proofUrl(rec.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline"
                            >
                              預覽
                            </a>
                            <a
                              href={monthlyReceiptsApi.proofUrl(rec.id)}
                              download
                              className="text-blue-600 hover:underline"
                            >
                              下載
                            </a>
                            <label className="cursor-pointer text-blue-600 hover:underline">
                              更換
                              <input
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                ref={(el) => {
                                  proofFileRef.current[rec.id] = el
                                }}
                                onChange={(e) => {
                                  const f = e.target.files?.[0]
                                  if (!f) return
                                  monthlyReceiptsApi
                                    .uploadProof(rec.id, f)
                                    .then(() => {
                                      loadMonthlyReceipts()
                                      e.target.value = ''
                                    })
                                    .catch(alert)
                                }}
                              />
                            </label>
                          </span>
                        ) : (
                          <label className="cursor-pointer text-blue-600 hover:underline">
                            上傳 PDF
                            <input
                              type="file"
                              accept=".pdf"
                              className="hidden"
                              ref={(el) => {
                                proofFileRef.current[rec.id] = el
                              }}
                              onChange={(e) => {
                                const f = e.target.files?.[0]
                                if (!f) return
                                monthlyReceiptsApi
                                  .uploadProof(rec.id, f)
                                  .then(() => {
                                    loadMonthlyReceipts()
                                    e.target.value = ''
                                  })
                                  .catch(alert)
                              }}
                            />
                          </label>
                        )}
                      </td>
                      <td className="py-2 pr-2">
                        <button
                          type="button"
                          className="text-blue-600 hover:underline text-xs"
                          onClick={() => setEditReceiptModal(rec)}
                        >
                          編輯
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 編輯回饋 Modal */}
      {editRebateModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !savingRebate && setEditRebateModal(null)}
        >
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full mx-4 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-slate-800">編輯回饋</h3>
            <div className="space-y-3">
              <div>
                <label className="label">回饋項目 *</label>
                <input
                  className="input"
                  value={rebateForm.item_name}
                  onChange={(e) => setRebateForm((f) => ({ ...f, item_name: e.target.value }))}
                  placeholder="例：年節禮品"
                />
              </div>
              <div>
                <label className="label">回饋日期</label>
                <input
                  type="date"
                  className="input"
                  value={rebateForm.completed_date ?? ''}
                  onChange={(e) => setRebateForm((f) => ({ ...f, completed_date: e.target.value || undefined }))}
                />
              </div>
              <div>
                <label className="label">金額</label>
                <input
                  type="number"
                  className="input"
                  value={rebateForm.cost_amount ?? ''}
                  onChange={(e) =>
                    setRebateForm((f) => ({
                      ...f,
                      cost_amount: e.target.value === '' ? undefined : Number(e.target.value),
                    }))
                  }
                  placeholder="0"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="edit-rebate-completed"
                  checked={rebateForm.is_completed}
                  onChange={(e) => setRebateForm((f) => ({ ...f, is_completed: e.target.checked }))}
                />
                <label htmlFor="edit-rebate-completed">是否完成</label>
              </div>
              <div>
                <label className="label">備註</label>
                <textarea
                  className="input min-h-[60px]"
                  value={rebateForm.notes ?? ''}
                  onChange={(e) => setRebateForm((f) => ({ ...f, notes: e.target.value || undefined }))}
                  placeholder="選填"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setEditRebateModal(null)}
                disabled={savingRebate}
              >
                取消
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={savingRebate || !rebateForm.item_name.trim()}
                onClick={() => {
                  setSavingRebate(true)
                  rebatesApi
                    .update(editRebateModal.id, {
                      item_name: rebateForm.item_name.trim(),
                      is_completed: rebateForm.is_completed,
                      completed_date: rebateForm.completed_date || undefined,
                      cost_amount: rebateForm.cost_amount,
                      notes: rebateForm.notes || undefined,
                    })
                    .then(() => {
                      setEditRebateModal(null)
                      loadRebates()
                    })
                    .catch(alert)
                    .finally(() => setSavingRebate(false))
                }}
              >
                {savingRebate ? '儲存中...' : '儲存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 新增回饋 Modal */}
      {addRebateModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !savingRebate && setAddRebateModal(false)}
        >
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full mx-4 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-slate-800">新增回饋</h3>
            <div className="space-y-3">
              <div>
                <label className="label">回饋項目 *</label>
                <input
                  className="input"
                  value={rebateForm.item_name}
                  onChange={(e) => setRebateForm((f) => ({ ...f, item_name: e.target.value }))}
                  placeholder="例：年節禮品"
                />
              </div>
              <div>
                <label className="label">回饋日期</label>
                <input
                  type="date"
                  className="input"
                  value={rebateForm.completed_date ?? ''}
                  onChange={(e) => setRebateForm((f) => ({ ...f, completed_date: e.target.value || undefined }))}
                />
              </div>
              <div>
                <label className="label">金額</label>
                <input
                  type="number"
                  className="input"
                  value={rebateForm.cost_amount ?? ''}
                  onChange={(e) =>
                    setRebateForm((f) => ({
                      ...f,
                      cost_amount: e.target.value === '' ? undefined : Number(e.target.value),
                    }))
                  }
                  placeholder="0"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="rebate-completed"
                  checked={rebateForm.is_completed}
                  onChange={(e) => setRebateForm((f) => ({ ...f, is_completed: e.target.checked }))}
                />
                <label htmlFor="rebate-completed">是否完成</label>
              </div>
              <div>
                <label className="label">備註</label>
                <textarea
                  className="input min-h-[60px]"
                  value={rebateForm.notes ?? ''}
                  onChange={(e) => setRebateForm((f) => ({ ...f, notes: e.target.value || undefined }))}
                  placeholder="選填"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setAddRebateModal(false)}
                disabled={savingRebate}
              >
                取消
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={savingRebate || !rebateForm.item_name.trim()}
                onClick={() => {
                  setSavingRebate(true)
                  sitesApi
                    .createRebate(siteId, {
                      item_name: rebateForm.item_name.trim(),
                      is_completed: rebateForm.is_completed,
                      completed_date: rebateForm.completed_date || undefined,
                      cost_amount: rebateForm.cost_amount,
                      notes: rebateForm.notes || undefined,
                    })
                    .then(() => {
                      setAddRebateModal(false)
                      setRebateForm({ item_name: '', is_completed: false })
                      loadRebates()
                    })
                    .catch(alert)
                    .finally(() => setSavingRebate(false))
                }}
              >
                {savingRebate ? '儲存中...' : '儲存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 編輯每月入帳 Modal */}
      {editReceiptModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setEditReceiptModal(null)}
        >
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full mx-4 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-slate-800">編輯入帳 — {editReceiptModal.billing_month}</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="receipt-is-received"
                  checked={editReceiptModal.is_received}
                  onChange={(e) =>
                    setEditReceiptModal((r) => (r ? { ...r, is_received: e.target.checked } : null))
                  }
                />
                <label htmlFor="receipt-is-received">已入帳</label>
              </div>
              <div>
                <label className="label">入帳日期</label>
                <input
                  type="date"
                  className="input"
                  value={editReceiptModal.received_date ?? ''}
                  onChange={(e) =>
                    setEditReceiptModal((r) =>
                      r ? { ...r, received_date: e.target.value || undefined } : null
                    )
                  }
                />
              </div>
              <div>
                <label className="label">實收金額</label>
                <input
                  type="number"
                  className="input"
                  value={editReceiptModal.received_amount ?? ''}
                  onChange={(e) =>
                    setEditReceiptModal((r) =>
                      r
                        ? {
                            ...r,
                            received_amount:
                              e.target.value === '' ? undefined : Number(e.target.value),
                          }
                        : null
                    )
                  }
                  placeholder="與應收相同可留空"
                />
              </div>
              <div>
                <label className="label">付款方式</label>
                <select
                  className="input"
                  value={editReceiptModal.payment_method ?? ''}
                  onChange={(e) =>
                    setEditReceiptModal((r) =>
                      r ? { ...r, payment_method: e.target.value || undefined } : null
                    )
                  }
                >
                  <option value="">—</option>
                  <option value="transfer">匯款</option>
                  <option value="cash">現金</option>
                  <option value="check">支票</option>
                  <option value="other">其他</option>
                </select>
              </div>
              <div>
                <label className="label">備註</label>
                <textarea
                  className="input min-h-[60px]"
                  value={editReceiptModal.notes ?? ''}
                  onChange={(e) =>
                    setEditReceiptModal((r) => (r ? { ...r, notes: e.target.value || undefined } : null))
                  }
                  placeholder="選填"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button type="button" className="btn-secondary" onClick={() => setEditReceiptModal(null)}>
                取消
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  monthlyReceiptsApi
                    .update(editReceiptModal.id, {
                      is_received: editReceiptModal.is_received,
                      received_date: editReceiptModal.received_date || undefined,
                      received_amount: editReceiptModal.received_amount,
                      payment_method: editReceiptModal.payment_method || undefined,
                      notes: editReceiptModal.notes || undefined,
                    })
                    .then(() => {
                      setEditReceiptModal(null)
                      loadMonthlyReceipts()
                    })
                    .catch(alert)
                }}
              >
                儲存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 移除案場確認 Modal */}
      {removeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => !removing && setRemoveModal(false)}>
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full mx-4 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-slate-800">移除案場</h3>
            <p className="text-slate-600 text-sm whitespace-pre-line">
              {`是否確定要移除此案場？${site.name ? `（${site.name}）` : ''}
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
              <button type="button" className="btn-secondary" onClick={() => setRemoveModal(false)} disabled={removing}>
                取消
              </button>
              <button
                type="button"
                className="btn-danger"
                disabled={removing || !adminTokenInput.trim()}
                onClick={() => {
                  if (!id) return
                  setRemoving(true)
                  sitesApi
                    .deactivate(Number(id), adminTokenInput.trim())
                    .then(() => {
                      setRemoveModal(false)
                      setAdminTokenInput('')
                      navigate('/sites')
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
