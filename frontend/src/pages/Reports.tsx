import { useState } from 'react'
import { reportsApi, downloadReportExcel } from '../api'
import { translateError } from '../utils/errorMsg'

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

export default function Reports() {
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')

  const handleDownload = async (
    urlPath: string,
    defaultFilename: string,
  ) => {
    setError('')
    setDownloading(true)
    try {
      await downloadReportExcel(urlPath, defaultFilename)
    } catch (e) {
      setError(translateError(e instanceof Error ? e.message : '下載失敗'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">報表匯出</h2>
      <p className="text-slate-600">選擇月份後可一鍵產生公司負擔總表、員工個人負擔明細、眷屬明細，並匯出 Excel。</p>

      <div className="card p-6 space-y-6">
        <section>
          <h3 className="font-semibold text-slate-700 mb-2">選擇月份</h3>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <select className="input w-24" value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {Array.from({ length: 5 }, (_, i) => currentYear - 2 + i).map((y) => (
                <option key={y} value={y}>{y} 年</option>
              ))}
            </select>
            <select className="input w-24" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>{m} 月</option>
              ))}
            </select>
          </div>

          <h4 className="font-medium text-slate-600 mb-2">依月份匯出 Excel</h4>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="btn-primary"
              disabled={downloading}
              onClick={() => handleDownload(reportsApi.monthlyBurdenExcel(year, month), `當月公司負擔明細_${year}${String(month).padStart(2, '0')}.xlsx`)}
            >
              公司負擔總表
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={downloading}
              onClick={() => handleDownload(reportsApi.personalBurdenExcel(year, month), `當月員工個人負擔明細_${year}${String(month).padStart(2, '0')}.xlsx`)}
            >
              員工個人負擔明細
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={downloading}
              onClick={() => handleDownload(reportsApi.dependentsExcel(), `眷屬清單_${new Date().toISOString().slice(0, 10)}.xlsx`)}
            >
              眷屬明細
            </button>
          </div>
          {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
          <p className="text-sm text-slate-500 mt-2">
            公司負擔總表：勞保/健保/職災/勞退/團保雇主負擔及小計。員工個人負擔明細：勞保+健保個人負擔。眷屬明細：全部眷屬清單（與月份無關）。
          </p>
        </section>

        <section className="pt-4 border-t border-slate-200">
          <h3 className="font-semibold text-slate-700 mb-2">其他報表</h3>
          <p className="text-sm text-slate-500 mb-3">員工清單：匯出所有員工基本資料。</p>
          <button
            type="button"
            className="btn-secondary"
            disabled={downloading}
            onClick={() => handleDownload(reportsApi.employeesExcel(), `員工清單_${new Date().toISOString().slice(0, 10)}.xlsx`)}
          >
            下載員工清單 Excel
          </button>
        </section>
      </div>
    </div>
  )
}
