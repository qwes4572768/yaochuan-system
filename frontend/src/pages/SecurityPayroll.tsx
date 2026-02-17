import { useState, useEffect, useRef, useMemo } from 'react'
import {
  accountingApi,
  downloadReportExcel,
  type SecurityPayrollCalcError,
  type SecurityPayrollResult,
  type PayrollType,
  type EmployeeLookupType,
  type SecurityPayrollHistoryStats,
} from '../api'
import { translateError } from '../utils/errorMsg'

const CALC_TYPES: { value: PayrollType; label: string }[] = [
  { value: 'security', label: '保全' },
  { value: 'property', label: '物業' },
]

const EXTRA_PAYROLL_TYPE_OPTIONS: { value: EmployeeLookupType; label: string }[] = [
  { value: 'security', label: '保全' },
  { value: 'property', label: '物業' },
  { value: 'smith', label: '史密斯' },
  { value: 'lixiang', label: '立翔人力' },
]

const thisYear = new Date().getFullYear()
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => thisYear - 2 + i)
const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1)
const STORAGE_KEYS = {
  type: 'securityPayroll.selectedType',
  year: 'securityPayroll.selectedYear',
  month: 'securityPayroll.selectedMonth',
}

const EMPTY_HISTORY_STATS: SecurityPayrollHistoryStats = {
  cash: 0,
  sec_first: 0,
  apt_first: 0,
  smith_first: 0,
  other_bank: 0,
  unset: 0,
}

type SalaryTypeFilter = 'ALL' | '領現' | '保全一銀' | '公寓一銀' | '史密斯一銀' | '其他銀行' | '未設定'

const FILTER_OPTIONS: { value: SalaryTypeFilter; label: string }[] = [
  { value: 'ALL', label: '全部' },
  { value: '領現', label: '領現' },
  { value: '保全一銀', label: '保全一銀' },
  { value: '公寓一銀', label: '公寓一銀' },
  { value: '史密斯一銀', label: '史密斯一銀' },
  { value: '其他銀行', label: '其他銀行' },
  { value: '未設定', label: '未設定' },
]

function isPayrollType(v: string): v is PayrollType {
  return CALC_TYPES.some((t) => t.value === v)
}

function parseHistoryMonths(months: string[]): { year: number; month: number }[] {
  return months
    .map((s) => {
      const [y, m] = String(s).split('-').map(Number)
      if (!Number.isFinite(y) || !Number.isFinite(m) || m < 1 || m > 12) return null
      return { year: y, month: m }
    })
    .filter((v): v is { year: number; month: number } => !!v)
}

function getInitialSelection(): { type: PayrollType; year: number; month: number; source: 'query' | 'storage' | 'default' } {
  const now = new Date()
  const fallback = { type: 'security' as PayrollType, year: now.getFullYear(), month: now.getMonth() + 1, source: 'default' as const }
  const qs = new URLSearchParams(window.location.search)
  const qYear = Number(qs.get('year'))
  const qMonth = Number(qs.get('month'))
  const qType = (qs.get('payroll_type') || qs.get('type') || '').trim() as PayrollType
  const queryType: PayrollType = isPayrollType(qType) ? qType : 'security'
  if (Number.isFinite(qYear) && Number.isFinite(qMonth) && qMonth >= 1 && qMonth <= 12) {
    return { type: queryType, year: qYear, month: qMonth, source: 'query' }
  }

  const sYear = Number(localStorage.getItem(STORAGE_KEYS.year))
  const sMonth = Number(localStorage.getItem(STORAGE_KEYS.month))
  const sType = (localStorage.getItem(STORAGE_KEYS.type) || '').trim() as PayrollType
  const storageType: PayrollType = isPayrollType(sType) ? sType : 'security'
  if (Number.isFinite(sYear) && Number.isFinite(sMonth) && sMonth >= 1 && sMonth <= 12) {
    return { type: storageType, year: sYear, month: sMonth, source: 'storage' }
  }
  return fallback
}

export default function SecurityPayroll() {
  const initialSelection = getInitialSelection()
  const initSourceRef = useRef<'query' | 'storage' | 'default'>(initialSelection.source)
  const hydratedDefaultFromMonthsRef = useRef(false)

  const [calcType, setCalcType] = useState<PayrollType>(initialSelection.type)
  const [year, setYear] = useState<number>(initialSelection.year)
  const [month, setMonth] = useState<number>(initialSelection.month)
  const [file, setFile] = useState<File | null>(null)
  const [extraPayrollTypes, setExtraPayrollTypes] = useState<EmployeeLookupType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState<SecurityPayrollResult[]>([])
  const [errors, setErrors] = useState<SecurityPayrollCalcError[]>([])

  const [historyMonths, setHistoryMonths] = useState<{ year: number; month: number }[]>([])
  const [historyYearMonth, setHistoryYearMonth] = useState<{ year: number; month: number } | null>(null)
  const [historyData, setHistoryData] = useState<{
    results: SecurityPayrollResult[]
    summary: { total_gross: number; total_net: number; total_deductions: number; row_count: number }
    stats: SecurityPayrollHistoryStats
  } | null>(null)
  const [salaryTypeFilter, setSalaryTypeFilter] = useState<SalaryTypeFilter>('ALL')
  const [historyLoading, setHistoryLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [deletingHistory, setDeletingHistory] = useState(false)
  const [historyActionMsg, setHistoryActionMsg] = useState('')

  const hasTypeYearMonth = calcType && year >= thisYear - 2 && year <= thisYear + 2 && month >= 1 && month <= 12

  const applyHistoryMonths = (
    months: { year: number; month: number }[],
    preferred?: { year: number; month: number }
  ) => {
    // 僅首次（無 query/localStorage）才用 DB 最新月份初始化年/月，避免後續跳月
    if (initSourceRef.current === 'default' && !hydratedDefaultFromMonthsRef.current && months.length > 0) {
      setYear(months[0].year)
      setMonth(months[0].month)
      hydratedDefaultFromMonthsRef.current = true
    }
    setHistoryMonths(months)
    setHistoryYearMonth((prev) => {
      if (months.length === 0) return null
      if (preferred && months.some((m) => m.year === preferred.year && m.month === preferred.month)) return preferred
      if (prev && months.some((m) => m.year === prev.year && m.month === prev.month)) return prev
      return { year: months[0].year, month: months[0].month }
    })
  }

  const handleCalculate = async () => {
    if (!calcType || !year || !month) {
      setError('請先選擇計算類型與年月')
      return
    }
    if (!file) {
      setError('請先選擇時數檔案')
      return
    }
    setError('')
    setResults([])
    setErrors([])
    setLoading(true)
    try {
      const dedupExtraTypes = Array.from(new Set(extraPayrollTypes.filter((t) => t !== calcType)))
      const data = await accountingApi.securityPayrollUpload(file, year, month, calcType, dedupExtraTypes)
      setResults(data.results ?? [])
      setErrors(data.errors ?? [])
      if ((data.results ?? []).length > 0) {
        const monthResp = await accountingApi.months(calcType)
        applyHistoryMonths(parseHistoryMonths(monthResp.months ?? []), { year, month })
      }
    } catch (e: unknown) {
      setError(translateError(e instanceof Error ? e.message : '計算失敗'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    accountingApi
      .months(calcType)
      .then((resp) => applyHistoryMonths(parseHistoryMonths(resp.months ?? [])))
      .catch(() => applyHistoryMonths([]))
  }, [calcType])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.type, calcType)
    localStorage.setItem(STORAGE_KEYS.year, String(year))
    localStorage.setItem(STORAGE_KEYS.month, String(month))
    const params = new URLSearchParams(window.location.search)
    params.set('year', String(year))
    params.set('month', String(month))
    params.set('payroll_type', calcType)
    const next = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, '', next)
  }, [calcType, year, month])

  useEffect(() => {
    if (!historyYearMonth) {
      setHistoryData(null)
      return
    }
    setHistoryLoading(true)
    accountingApi
      .history(historyYearMonth.year, historyYearMonth.month, calcType)
      .then((d) => setHistoryData({ results: d.results, summary: d.summary, stats: d.stats ?? EMPTY_HISTORY_STATS }))
      .catch(() => setHistoryData(null))
      .finally(() => setHistoryLoading(false))
  }, [historyYearMonth, calcType])

  useEffect(() => {
    setSalaryTypeFilter('ALL')
  }, [historyYearMonth, calcType])

  const filteredHistoryResults = useMemo(() => {
    if (!historyData) return []
    if (salaryTypeFilter === 'ALL') return historyData.results
    return historyData.results.filter((row) => (row.salary_type || '未設定') === salaryTypeFilter)
  }, [historyData, salaryTypeFilter])

  const filterCountByType = useMemo(() => {
    const stats = historyData?.stats ?? EMPTY_HISTORY_STATS
    return {
      ALL: historyData?.summary.row_count ?? 0,
      領現: stats.cash ?? 0,
      保全一銀: stats.sec_first ?? 0,
      公寓一銀: stats.apt_first ?? 0,
      史密斯一銀: stats.smith_first ?? 0,
      其他銀行: stats.other_bank ?? 0,
      未設定: stats.unset ?? 0,
    } as Record<SalaryTypeFilter, number>
  }, [historyData])

  const handleExportCurrent = async () => {
    if (results.length === 0) return
    setExporting(true)
    try {
      await accountingApi.exportCurrent(year, month, calcType, results)
    } catch (e: unknown) {
      setError(translateError(e instanceof Error ? e.message : '匯出失敗'))
    } finally {
      setExporting(false)
    }
  }

  const handleExportHistory = async () => {
    if (!historyYearMonth) return
    setExporting(true)
    try {
      await downloadReportExcel(
        accountingApi.exportHistoryUrl(historyYearMonth.year, historyYearMonth.month, calcType),
        `${CALC_TYPES.find((t) => t.value === calcType)?.label ?? '薪資'}核薪_${historyYearMonth.year}_${String(historyYearMonth.month).padStart(2, '0')}.xlsx`
      )
    } catch (e: unknown) {
      setError(translateError(e instanceof Error ? e.message : '匯出失敗'))
    } finally {
      setExporting(false)
    }
  }

  const handleDeleteHistory = async () => {
    if (!historyYearMonth) return
    const y = historyYearMonth.year
    const m = historyYearMonth.month
    const ok = window.confirm(`確定刪除 ${y}年${String(m).padStart(2, '0')}月 的歷史資料？此動作無法復原。`)
    if (!ok) return
    setDeletingHistory(true)
    setHistoryActionMsg('')
    setError('')
    try {
      const res = await accountingApi.deleteHistory(y, m, calcType)
      const monthResp = await accountingApi.months(calcType)
      applyHistoryMonths(parseHistoryMonths(monthResp.months ?? []))
      setHistoryActionMsg(`已刪除 ${y}年${String(m).padStart(2, '0')}月資料，共 ${res.deleted_count} 筆。`)
    } catch (e: unknown) {
      setError(translateError(e instanceof Error ? e.message : '刪除失敗'))
    } finally {
      setDeletingHistory(false)
    }
  }

  const titleMonth = `${year}年${String(month).padStart(2, '0')}月`
  const pageTitle = `${CALC_TYPES.find((t) => t.value === calcType)?.label ?? '薪資'}薪資計算 - ${titleMonth}`

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">{pageTitle}</h2>
      <p className="text-slate-600">
        請先選擇計算類型與年月，再上傳時數檔案。表頭需含：案場名稱、員工姓名、日期、工時。支援 xlsx / xls / ods。
      </p>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">步驟一：選擇計算類型</h3>
        <div className="flex flex-wrap gap-3 items-center">
          <label className="text-sm text-slate-600">計算類型</label>
          <select
            className="input w-40"
            value={calcType}
            onChange={(e) => setCalcType(e.target.value as PayrollType)}
          >
            {CALC_TYPES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-4">
          <h4 className="text-sm font-medium text-slate-700 mb-2">跨公司別查詢員工資料（選填）</h4>
          <div className="flex flex-wrap gap-4">
            {EXTRA_PAYROLL_TYPE_OPTIONS.map((opt) => {
              const checked = extraPayrollTypes.includes(opt.value)
              return (
                <label key={opt.value} className="inline-flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      setExtraPayrollTypes((prev) => {
                        if (e.target.checked) return Array.from(new Set([...prev, opt.value]))
                        return prev.filter((v) => v !== opt.value)
                      })
                    }}
                  />
                  {opt.label}
                </label>
              )
            })}
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">步驟二：選擇年、月</h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-slate-600 mb-1">年</label>
            <select
              className="input w-28"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            >
              {YEAR_OPTIONS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">月</label>
            <select
              className="input w-28"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
            >
              {MONTH_OPTIONS.map((m) => (
                <option key={m} value={m}>{m}月</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">步驟三：上傳檔案與計算</h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-sm text-slate-600 mb-1">選擇時數檔案</label>
            <input
              type="file"
              accept=".xlsx,.xls,.ods"
              className="input"
              disabled={!hasTypeYearMonth || loading}
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null)
                setError('')
              }}
            />
          </div>
          <button
            type="button"
            className="btn primary"
            onClick={handleCalculate}
            disabled={loading || !file || !hasTypeYearMonth}
          >
            {loading ? '計算中…' : '計算'}
          </button>
        </div>
        {!hasTypeYearMonth ? (
          <p className="mt-2 text-slate-500 text-sm">請先選擇計算類型與年月，計算按鈕才會啟用。</p>
        ) : null}
        {error && <p className="mt-2 text-red-600">{error}</p>}
      </div>

      {errors.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">錯誤與問題清單</h3>
          <ul className="list-disc list-inside space-y-2 text-red-600">
            {errors.map((item, i) => (
              <li key={i}>
                <span>{item.message}</span>
                {item.type === 'missing_pay_config' && item.employee_id ? (
                  <button
                    type="button"
                    className="ml-2 text-sm underline text-blue-700 hover:text-blue-900"
                    onClick={() => {
                      const targetType = encodeURIComponent(item.current_payroll_type || calcType)
                      window.location.href = `/employees/${item.employee_id}?tab=payroll&payroll_type=${targetType}`
                    }}
                  >
                    前往員工設定
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.length > 0 && (
        <div className="card p-6 overflow-x-auto">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2 mb-4">
            <h3 className="font-semibold text-slate-700">計算結果（{titleMonth}）</h3>
            <div className="flex items-center gap-2">
              <span className="text-sm text-emerald-600">已自動存檔至系統（依類別／年／月）</span>
              <button
                type="button"
                className="btn secondary"
                onClick={handleExportCurrent}
                disabled={exporting}
              >
                {exporting ? '匯出中…' : '匯出當次結果 Excel'}
              </button>
            </div>
          </div>
          <table className="w-full border-collapse border border-slate-300 text-sm">
            <thead>
              <tr className="bg-slate-100">
                <th className="border border-slate-300 px-2 py-1.5 text-left">案場</th>
                <th className="border border-slate-300 px-2 py-1.5 text-left">員工</th>
                <th className="border border-slate-300 px-2 py-1.5 text-center">薪制</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">總工時</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">應發</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">勞保</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">健保</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">團保</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">自提6%</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">扣款合計</th>
                <th className="border border-slate-300 px-2 py-1.5 text-right">實發</th>
                <th className="border border-slate-300 px-2 py-1.5 text-center">狀態</th>
              </tr>
            </thead>
            <tbody>
              {results.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="border border-slate-300 px-2 py-1.5">{row.site}</td>
                  <td className="border border-slate-300 px-2 py-1.5">{row.employee}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-center">{row.pay_type === 'monthly' ? '月薪' : row.pay_type === 'daily' ? '日薪' : '時薪'}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{row.total_hours}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.gross_salary ?? row.total_salary).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.labor_insurance_employee ?? 0).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.health_insurance_employee ?? 0).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.group_insurance ?? 0).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.self_pension_6 ?? 0).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.deductions_total ?? 0).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-right font-medium">{(row.net_salary ?? row.total_salary).toLocaleString()}</td>
                  <td className="border border-slate-300 px-2 py-1.5 text-center">{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">歷史查詢</h3>
        <p className="text-slate-600 text-sm mb-4">依類別／年／月查詢已存檔的薪資結果，並可匯出 Excel。</p>
        <div className="flex flex-wrap gap-3 items-end mb-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">選擇月份</label>
            <select
              className="input w-48"
              value={historyYearMonth ? `${historyYearMonth.year}-${historyYearMonth.month}` : ''}
              onChange={(e) => {
                const v = e.target.value
                if (!v) {
                  setHistoryYearMonth(null)
                  return
                }
                const [y, m] = v.split('-').map(Number)
                setHistoryYearMonth({ year: y, month: m })
              }}
            >
              <option value="">— 請選擇 —</option>
              {historyMonths.map(({ year: y, month: m }) => (
                <option key={`${y}-${m}`} value={`${y}-${m}`}>
                  {y}年{String(m).padStart(2, '0')}月
                </option>
              ))}
            </select>
          </div>
          {historyYearMonth && historyData && historyData.summary.row_count > 0 && (
            <button
              type="button"
              className="btn secondary"
              onClick={handleExportHistory}
              disabled={exporting || deletingHistory}
            >
              {exporting ? '匯出中…' : '匯出歷史 Excel'}
            </button>
          )}
          {historyYearMonth && (
            <button
              type="button"
              className="btn secondary text-red-700 border-red-300"
              onClick={handleDeleteHistory}
              disabled={deletingHistory || exporting || historyLoading}
            >
              {deletingHistory ? '刪除中…' : '刪除此月份歷史'}
            </button>
          )}
        </div>
        {historyActionMsg ? <p className="mb-3 text-sm text-emerald-600">{historyActionMsg}</p> : null}
        {historyYearMonth ? (
          <p className="mb-3 text-xs text-slate-500">刪除僅會影響目前選擇的年月與類型，不會刪到其他月份。</p>
        ) : null}
        {historyLoading && <p className="text-slate-500 text-sm">載入中…</p>}
        {!historyLoading && historyYearMonth && historyData && (
          <>
            <div className="flex flex-wrap gap-4 text-sm text-slate-600 mb-4">
              <span>應發合計：{(historyData.summary.total_gross ?? 0).toLocaleString()}</span>
              <span>實發合計：{(historyData.summary.total_net ?? 0).toLocaleString()}</span>
              <span>扣款合計：{(historyData.summary.total_deductions ?? 0).toLocaleString()}</span>
              <span>筆數：{historyData.summary.row_count}</span>
            </div>
            <div className="flex flex-wrap gap-4 text-sm text-slate-600 mb-4">
              <span>領現：{historyData.stats.cash ?? 0} 人</span>
              <span>保全一銀：{historyData.stats.sec_first ?? 0} 人</span>
              <span>公寓一銀：{historyData.stats.apt_first ?? 0} 人</span>
              <span>史密斯一銀：{historyData.stats.smith_first ?? 0} 人</span>
              <span>其他銀行：{historyData.stats.other_bank ?? 0} 人</span>
              <span>未設定：{historyData.stats.unset ?? 0} 人</span>
            </div>
            <div className="mb-4 space-y-2">
              <div className="hidden md:flex flex-wrap gap-2">
                {FILTER_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`btn secondary text-sm ${salaryTypeFilter === opt.value ? 'ring-2 ring-slate-400' : ''}`}
                    onClick={() => setSalaryTypeFilter(opt.value)}
                  >
                    {opt.label}({filterCountByType[opt.value] ?? 0})
                  </button>
                ))}
              </div>
              <div className="md:hidden">
                <label className="block text-sm text-slate-600 mb-1">分類篩選</label>
                <select
                  className="input w-full"
                  value={salaryTypeFilter}
                  onChange={(e) => setSalaryTypeFilter(e.target.value as SalaryTypeFilter)}
                >
                  {FILTER_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}({filterCountByType[opt.value] ?? 0})
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-slate-500">
                目前顯示筆數：{filteredHistoryResults.length} / 總筆數：{historyData.summary.row_count}
              </p>
            </div>
            {historyData.results.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border border-slate-300 text-sm">
                  <thead>
                    <tr className="bg-slate-100">
                      <th className="border border-slate-300 px-2 py-1.5 text-left">案場</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-left">員工</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-center">薪制</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">總工時</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">應發</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">勞保</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">健保</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">團保</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">自提6%</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">扣款合計</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-right">實發</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-center">狀態</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-center">領薪方式</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-center">銀行代碼</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-center">分行代碼</th>
                      <th className="border border-slate-300 px-2 py-1.5 text-center">銀行帳號</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistoryResults.map((row, i) => (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="border border-slate-300 px-2 py-1.5">{row.site}</td>
                        <td className="border border-slate-300 px-2 py-1.5">{row.employee}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-center">{row.pay_type === 'monthly' ? '月薪' : row.pay_type === 'daily' ? '日薪' : '時薪'}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{row.total_hours}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.gross_salary ?? row.total_salary).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.labor_insurance_employee ?? 0).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.health_insurance_employee ?? 0).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.group_insurance ?? 0).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.self_pension_6 ?? 0).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right">{(row.deductions_total ?? 0).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-right font-medium">{(row.net_salary ?? row.total_salary).toLocaleString()}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-center">
                          <span>{row.status}</span>
                          {row.conflict ? <span className="ml-1 text-amber-600" title={`同名候選 ${row.matched_candidates_count ?? 0} 筆`}>⚠</span> : null}
                        </td>
                        <td className="border border-slate-300 px-2 py-1.5 text-center">{row.salary_type || '未設定'}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-center">{row.salary_type === '領現' ? '—' : (row.bank_code || '')}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-center">{row.salary_type === '領現' ? '—' : (row.branch_code || '')}</td>
                        <td className="border border-slate-300 px-2 py-1.5 text-center">{row.salary_type === '領現' ? '—' : (row.account_number || '')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredHistoryResults.length === 0 ? (
                  <p className="text-slate-500 text-sm mt-3">此分類沒有資料</p>
                ) : null}
              </div>
            ) : (
              <p className="text-slate-500 text-sm">該月份尚無存檔資料。</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
