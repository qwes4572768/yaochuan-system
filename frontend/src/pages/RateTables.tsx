import { useState, useEffect } from 'react'
import { rateTablesApi } from '../api'
import { translateError } from '../utils/errorMsg'
import type { RateTableRead } from '../types'

const TYPE_LABELS: Record<string, string> = {
  labor_insurance: '勞保',
  health_insurance: '健保',
  occupational_accident: '職災',
  labor_pension: '勞退',
}

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

export default function RateTables() {
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [effective, setEffective] = useState<Record<string, RateTableRead | null> | null>(null)
  const [allTables, setAllTables] = useState<RateTableRead[]>([])
  const [loading, setLoading] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [filterType, setFilterType] = useState<string>('')

  const loadEffective = async () => {
    setLoading(true)
    try {
      const data = await rateTablesApi.effective(year, month)
      setEffective(data)
    } catch (e) {
      setEffective({})
    } finally {
      setLoading(false)
    }
  }

  const loadAll = async () => {
    setLoading(true)
    try {
      const data = await rateTablesApi.list(filterType || undefined)
      setAllTables(data)
    } catch (e) {
      setAllTables([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEffective()
  }, [year, month])

  useEffect(() => {
    loadAll()
  }, [filterType])

  const handleUpload = async () => {
    if (!uploadFile) return
    setUploadError('')
    setUploadSuccess(false)
    try {
      await rateTablesApi.importFile(uploadFile)
      setUploadSuccess(true)
      setUploadFile(null)
      loadEffective()
      loadAll()
    } catch (e: unknown) {
      setUploadError(translateError(e instanceof Error ? e.message : '匯入失敗'))
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">級距與費率管理</h2>
      <p className="text-slate-600">
        選擇「計算月份」可檢視當月有效之級距表；試算與報表會依計算月份自動套用該版本。可上傳 JSON、Excel 或 Word（.docx）匯入/更新級距。
      </p>

      <div className="card p-6 space-y-6">
        <section>
          <h3 className="font-semibold text-slate-700 mb-2">當月有效級距表</h3>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <select
              className="input w-24"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            >
              {Array.from({ length: 5 }, (_, i) => currentYear - 2 + i).map((y) => (
                <option key={y} value={y}>{y} 年</option>
              ))}
            </select>
            <select
              className="input w-24"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>{m} 月</option>
              ))}
            </select>
          </div>
          {loading && effective === null ? (
            <p className="text-slate-500">載入中…</p>
          ) : effective ? (
            <div className="space-y-4">
              {(['labor_insurance', 'health_insurance', 'occupational_accident', 'labor_pension'] as const).map((t) => {
                const tbl = effective[t]
                return (
                  <div key={t} className="border border-slate-200 rounded p-3">
                    <h4 className="font-medium text-slate-700">
                      {TYPE_LABELS[t] ?? t}
                      {tbl ? ` · ${tbl.version}（${tbl.effective_from}～${tbl.effective_to ?? '迄今'}）` : ' · 無有效版本'}
                    </h4>
                    {tbl?.note && <p className="text-sm text-slate-500 mt-1">{tbl.note}</p>}
                    {tbl?.items?.length ? (
                      <div className="mt-2 overflow-x-auto">
                        <table className="w-full text-sm border-collapse">
                          <thead>
                            <tr className="bg-slate-100">
                              <th className="border border-slate-300 px-2 py-1 text-left">級距/名稱</th>
                              <th className="border border-slate-300 px-2 py-1 text-right">薪資下限</th>
                              <th className="border border-slate-300 px-2 py-1 text-right">薪資上限</th>
                              <th className="border border-slate-300 px-2 py-1 text-right">投保薪資</th>
                              <th className="border border-slate-300 px-2 py-1 text-right">個人%</th>
                              <th className="border border-slate-300 px-2 py-1 text-right">公司%</th>
                              <th className="border border-slate-300 px-2 py-1 text-right">政府%</th>
                            </tr>
                          </thead>
                          <tbody>
                            {tbl.items.slice(0, 20).map((it) => (
                              <tr key={it.id}>
                                <td className="border border-slate-300 px-2 py-1">{it.level_name ?? '—'}</td>
                                <td className="border border-slate-300 px-2 py-1 text-right">{it.salary_min}</td>
                                <td className="border border-slate-300 px-2 py-1 text-right">{it.salary_max}</td>
                                <td className="border border-slate-300 px-2 py-1 text-right">{it.insured_salary ?? '—'}</td>
                                <td className="border border-slate-300 px-2 py-1 text-right">{(Number(it.employee_rate) * 100).toFixed(2)}%</td>
                                <td className="border border-slate-300 px-2 py-1 text-right">{(Number(it.employer_rate) * 100).toFixed(2)}%</td>
                                <td className="border border-slate-300 px-2 py-1 text-right">{it.gov_rate != null ? `${(Number(it.gov_rate) * 100).toFixed(2)}%` : '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {tbl.items.length > 20 && (
                          <p className="text-sm text-slate-500 mt-1">僅顯示前 20 筆，共 {tbl.items.length} 筆</p>
                        )}
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>
          ) : null}
        </section>

        <section className="pt-4 border-t border-slate-200">
          <h3 className="font-semibold text-slate-700 mb-2">匯入 / 更新級距</h3>
          <p className="text-sm text-slate-500 mb-3">
            上傳 JSON、Excel（.xlsx）或 Word（.docx）。JSON 需含 tables 陣列；Excel/Word 每個工作表或表格需有 type、version、effective_from 及級距欄位（salary_min、salary_max、insured_salary、employee_rate、employer_rate、gov_rate 或中文：下限、上限、投保/級距、個人、公司、政府）。
          </p>
          <p className="text-xs text-slate-400 mb-2">
            若政府僅提供 PDF 或 ODT：請將表格內容複製到 Excel 後另存 .xlsx，或另存為 Word .docx 後上傳。
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="file"
              accept=".json,.xlsx,.docx"
              className="input max-w-xs"
              onChange={(e) => {
                const f = e.target.files?.[0]
                setUploadFile(f ?? null)
                setUploadError('')
                setUploadSuccess(false)
              }}
            />
            <button
              type="button"
              className="btn-primary"
              disabled={!uploadFile}
              onClick={handleUpload}
            >
              上傳匯入
            </button>
          </div>
          {uploadError && <p className="text-red-600 text-sm mt-2">{uploadError}</p>}
          {uploadSuccess && <p className="text-green-600 text-sm mt-2">匯入成功，已重新載入列表。</p>}
        </section>

        <section className="pt-4 border-t border-slate-200">
          <h3 className="font-semibold text-slate-700 mb-2">全部級距表</h3>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <select
              className="input w-40"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              <option value="">全部類型</option>
              {Object.entries(TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <button type="button" className="btn-secondary" onClick={loadAll}>重新載入</button>
          </div>
          <ul className="space-y-1 text-sm">
            {allTables.map((t) => (
              <li key={t.id} className="text-slate-600">
                {TYPE_LABELS[t.type] ?? t.type} · {t.version}（{t.effective_from}
                {t.effective_to ? `～${t.effective_to}` : '～迄今'}） · {t.items?.length ?? 0} 筆級距
              </li>
            ))}
            {allTables.length === 0 && !loading && <li className="text-slate-500">尚無級距表，請先執行 seed 或上傳匯入。</li>}
          </ul>
        </section>
      </div>
    </div>
  )
}
