import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { employeesApi, documentsApi, insuranceApi } from '../api'
import { maskNationalId, maskAddress } from '../utils/mask'
import type { Employee, DocumentInfo, InsuranceEstimate } from '../types'

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>()
  const [emp, setEmp] = useState<Employee | null>(null)
  const [docs, setDocs] = useState<DocumentInfo[]>([])
  const [estimate, setEstimate] = useState<InsuranceEstimate | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState<string | null>(null)
  const [excelEstimate, setExcelEstimate] = useState<InsuranceEstimate | null>(null)
  const [uploadingExcel, setUploadingExcel] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const excelFileRef = useRef<HTMLInputElement>(null)
  const [uploadType, setUploadType] = useState<'security_check' | '84_1'>('security_check')

  const loadDocs = () => {
    if (id) documentsApi.list(Number(id)).then(setDocs).catch(() => setDocs([]))
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth() + 1
    setExcelEstimate(null)
    Promise.all([
      employeesApi.get(Number(id)),
      documentsApi.list(Number(id)).catch(() => []),
    ]).then(([e, d]) => {
      setEmp(e)
      setDocs(d)
      insuranceApi.estimate({
        employee_id: Number(id),
        year,
        month,
        pension_self_6: e.pension_self_6 ?? false,
      }).then(setEstimate).catch(() => setEstimate(null))
    }).catch(alert).finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (emp && id && !excelEstimate) {
      const now = new Date()
      insuranceApi.estimate({
        employee_id: Number(id),
        year: now.getFullYear(),
        month: now.getMonth() + 1,
        pension_self_6: emp.pension_self_6 ?? false,
      }).then(setEstimate).catch(() => setEstimate(null))
    }
  }, [emp?.insured_salary_level, emp?.dependent_count, emp?.dependents?.length, emp?.pension_self_6, id, excelEstimate])

  const PDF_MAX_MB = 10
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !id) return
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      alert('僅接受 PDF 檔案（application/pdf）')
      return
    }
    if (file.size > PDF_MAX_MB * 1024 * 1024) {
      alert(`檔案大小不得超過 ${PDF_MAX_MB} MB`)
      return
    }
    setUploading(uploadType)
    try {
      await documentsApi.upload(Number(id), uploadType, file)
      loadDocs()
      employeesApi.get(Number(id)).then(setEmp)
    } catch (err: any) {
      alert(err?.message || '上傳失敗')
    } finally {
      setUploading(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !id) return
    if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
      alert('僅接受 .xlsx 或 .xls 試算檔')
      return
    }
    setUploadingExcel(true)
    try {
      const now = new Date()
      const res = await insuranceApi.estimateFromExcel(
        Number(id),
        now.getFullYear(),
        now.getMonth() + 1,
        file
      )
      setExcelEstimate(res)
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : '上傳失敗')
    } finally {
      setUploadingExcel(false)
      if (excelFileRef.current) excelFileRef.current.value = ''
    }
  }

  const displayEstimate = excelEstimate ?? estimate

  if (loading || !emp) return <div className="text-slate-500">載入中...</div>

  const docLabel = (t: string) => (t === 'security_check' ? '安全查核 PDF' : '84-1 PDF')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">員工詳情 · {emp.name}</h2>
        <Link to={`/employees/${id}/edit`} className="btn-primary">編輯</Link>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">基本資料</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div><span className="text-slate-500">員工編號</span> {emp.id}</div>
          <div><span className="text-slate-500">姓名</span> {emp.name}</div>
          <div><span className="text-slate-500">出生年月日</span> {emp.birth_date || '－'}</div>
          <div><span className="text-slate-500">身分證字號</span> {maskNationalId(emp.national_id)}</div>
          <div className="sm:col-span-2"><span className="text-slate-500">戶籍地址</span> {maskAddress(emp.reg_address)}</div>
          <div className="sm:col-span-2"><span className="text-slate-500">居住地址</span> {maskAddress(emp.live_address)} {emp.live_same_as_reg && '(同戶籍)'}</div>
          <div><span className="text-slate-500">薪資類型</span> {emp.salary_type || '－'}</div>
          <div><span className="text-slate-500">薪資數值</span> {emp.salary_value != null ? Number(emp.salary_value) : '－'}</div>
          <div><span className="text-slate-500">投保薪資級距</span> {emp.insured_salary_level != null ? Number(emp.insured_salary_level) : '－'}</div>
          <div><span className="text-slate-500">加保日期</span> {emp.enroll_date || '－'}</div>
          <div><span className="text-slate-500">退保日期</span> {emp.cancel_date || '－'}</div>
          <div><span className="text-slate-500">眷屬數量</span> {emp.dependent_count ?? 0}</div>
          <div><span className="text-slate-500">領薪方式</span> {emp.pay_method || '－'}</div>
          {emp.pay_method && emp.pay_method !== 'CASH' && (
            <>
              <div><span className="text-slate-500">銀行代碼</span> {emp.bank_code || '－'}</div>
              <div><span className="text-slate-500">分行代碼</span> {emp.branch_code || '－'}</div>
              <div className="sm:col-span-2"><span className="text-slate-500">銀行帳號</span> {emp.bank_account || '－'}</div>
            </>
          )}
          {emp.notes && (
            <div className="sm:col-span-2">
              <span className="text-slate-500">備註</span>
              <p className="mt-1 text-slate-700 whitespace-pre-wrap">{emp.notes}</p>
            </div>
          )}
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">眷屬資料</h3>
        {!emp.dependents?.length ? (
          <p className="text-slate-500 text-sm">尚無眷屬資料。</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-2 pr-4">關係</th>
                  <th className="py-2 pr-4">姓名</th>
                  <th className="py-2 pr-4">身分證</th>
                  <th className="py-2 pr-4">出生年月日</th>
                  <th className="py-2 pr-4">居住縣市</th>
                  <th className="py-2 pr-4">是否身障</th>
                  <th className="py-2">身障等級</th>
                </tr>
              </thead>
              <tbody>
                {emp.dependents.map((d) => (
                  <tr key={d.id} className="border-b">
                    <td className="py-2 pr-4">{d.relation}</td>
                    <td className="py-2 pr-4">{d.name}</td>
                    <td className="py-2 pr-4">{maskNationalId(d.national_id)}</td>
                    <td className="py-2 pr-4">{d.birth_date || '－'}</td>
                    <td className="py-2 pr-4">{d.city || '－'}</td>
                    <td className="py-2 pr-4">{d.is_disabled ? '是' : '否'}</td>
                    <td className="py-2">{d.disability_level || '－'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">當月費用試算（本人 + 眷屬，眷屬最多計 3 人）</h3>
        {!displayEstimate ? (
          <p className="text-slate-600">
            尚未匯入級距表或找不到此員工的投保級距。請先至 <Link to="/bracket-import" className="text-indigo-600 hover:underline">級距表匯入</Link> 上傳 Excel 後再試算。
          </p>
        ) : (
          <>
          {displayEstimate.from_excel && (
            <p className="text-sm font-medium text-indigo-700 bg-indigo-50 px-3 py-2 rounded-lg mb-3">
              本結果來自 Excel 試算檔（公司負擔、員工負擔、合計以 Excel 為準，含勞退 6% 等所有項目）
            </p>
          )}
          <div className="flex flex-wrap gap-2 items-center mb-3">
            <input
              ref={excelFileRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={handleExcelUpload}
            />
            <button
              type="button"
              onClick={() => excelFileRef.current?.click()}
              disabled={uploadingExcel}
              className="btn-secondary text-sm"
            >
              {uploadingExcel ? '上傳中...' : '上傳 Excel 試算檔'}
            </button>
            {excelEstimate && (
              <span className="text-sm text-slate-500">已使用 Excel 試算結果 · 切換員工或重新整理後可改回系統試算</span>
            )}
          </div>
          {!displayEstimate.from_excel && (
            <div className="mb-3">
              <p className="text-sm text-slate-500">
                計算月份：{new Date().getFullYear()} 年 {new Date().getMonth() + 1} 月 · 投保級距：{Number(displayEstimate.insured_salary_level)} · 眷屬計入：{displayEstimate.dependent_count} 人
                {emp?.pension_self_6 && ' · 自提6%：已勾選（依員工資料）'}
              </p>
              {displayEstimate.from_bracket_table && displayEstimate.bracket_source && (
                <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-3 py-2 mt-2">
                  本計算使用級距表：{displayEstimate.bracket_source.file_name}（匯入時間：{displayEstimate.bracket_source.imported_at}）
                </p>
              )}
              {displayEstimate.billing_note && !displayEstimate.from_bracket_table && (
                <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-2">
                  {displayEstimate.billing_note}
                </p>
              )}
            </div>
          )}
          {!displayEstimate.from_excel && displayEstimate.calculation_steps && displayEstimate.calculation_steps.length > 0 && (
            <div className="mb-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <h4 className="font-medium text-slate-700 mb-3">計算過程（如何得出下列表格金額）</h4>
              <ul className="space-y-4 text-sm">
                {displayEstimate.calculation_steps.map((step, i) => (
                  <li key={i} className="border-b border-slate-200 pb-3 last:border-0 last:pb-0">
                    <span className="font-medium text-slate-800">{step.item}</span>
                    <p className="text-slate-600 mt-1.5 whitespace-pre-line leading-relaxed">{step.detail}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-2 pr-4">項目</th>
                  <th className="py-2 pr-4 text-right">雇主</th>
                  <th className="py-2 pr-4 text-right">員工</th>
                  <th className="py-2 text-right">小計</th>
                </tr>
              </thead>
              <tbody>
                {[displayEstimate.labor_insurance, displayEstimate.occupational_accident, displayEstimate.labor_pension, displayEstimate.group_insurance].map((row) => (
                  <tr key={row.name} className="border-b">
                    <td className="py-2 pr-4">{row.name}</td>
                    <td className="py-2 pr-4 text-right">{Number(row.employer).toFixed(2)}</td>
                    <td className="py-2 pr-4 text-right">{Number(row.employee).toFixed(2)}</td>
                    <td className="py-2 text-right">{Number(row.total).toFixed(2)}</td>
                  </tr>
                ))}
                {displayEstimate.pension_self_6 && (
                  <tr className="border-b">
                    <td className="py-2 pr-4">{displayEstimate.pension_self_6.name}</td>
                    <td className="py-2 pr-4 text-right">{Number(displayEstimate.pension_self_6.employer).toFixed(2)}</td>
                    <td className="py-2 pr-4 text-right">{Number(displayEstimate.pension_self_6.employee).toFixed(2)}</td>
                    <td className="py-2 text-right">{Number(displayEstimate.pension_self_6.total).toFixed(2)}</td>
                  </tr>
                )}
                <tr className="border-b bg-slate-50">
                  <td className="py-2 pr-4">健保</td>
                  <td className="py-2 pr-4 text-right">{Number(displayEstimate.health_insurance.employer).toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right">{Number(displayEstimate.health_insurance.employee).toFixed(2)}</td>
                  <td className="py-2 text-right">{Number(displayEstimate.health_insurance.total).toFixed(2)}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr className="font-medium border-t-2">
                  <td className="py-2 pr-4">合計</td>
                  <td className="py-2 pr-4 text-right">{Number(displayEstimate.total_employer).toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right">{Number(displayEstimate.total_employee).toFixed(2)}</td>
                  <td className="py-2 text-right">{Number(displayEstimate.total).toFixed(2)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          {displayEstimate.health_insurance_breakdown && (
            <div className="mt-6 pt-4 border-t border-slate-200">
              <h4 className="font-medium text-slate-700 mb-2">健保分攤／減免明細</h4>
              <p className="text-sm text-slate-500 mb-2">
                原本個人負擔合計：{Number(displayEstimate.health_insurance_breakdown.original_personal_total).toFixed(2)} 元 ·
                減免後個人負擔合計：{Number(displayEstimate.health_insurance_breakdown.reduced_personal_total).toFixed(2)} 元 ·
                公司負擔：{Number(displayEstimate.health_insurance_breakdown.employer_total).toFixed(2)} 元
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-2 pr-4">姓名</th>
                      <th className="py-2 pr-4">本人/眷屬</th>
                      <th className="py-2 pr-4">套用規則</th>
                      <th className="py-2 pr-4 text-right">原本個人負擔</th>
                      <th className="py-2 text-right">減免後個人負擔</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayEstimate.health_insurance_breakdown.detail.map((row, i) => (
                      <tr key={i} className="border-b">
                        <td className="py-2 pr-4">{row.name}</td>
                        <td className="py-2 pr-4">{row.role}</td>
                        <td className="py-2 pr-4">{row.rule_applied?.length ? row.rule_applied.join('、') : '—'}</td>
                        <td className="py-2 pr-4 text-right">{Number(row.original_personal).toFixed(2)}</td>
                        <td className="py-2 text-right">{Number(row.reduced_personal).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          </>
        )}
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">檔案上傳</h3>
        <p className="text-sm text-slate-500 mb-3">安全查核 PDF、84-1 PDF（僅接受 application/pdf，單檔最大 10MB）</p>
        <div className="flex flex-wrap gap-2 items-center mb-4">
          <select className="input w-40" value={uploadType} onChange={(e) => setUploadType(e.target.value as 'security_check' | '84_1')}>
            <option value="security_check">安全查核 PDF</option>
            <option value="84_1">84-1 PDF</option>
          </select>
          <input ref={fileRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={handleUpload} />
          <button type="button" onClick={() => fileRef.current?.click()} disabled={!!uploading} className="btn-primary text-sm">
            {uploading ? '上傳中...' : '選擇檔案並上傳'}
          </button>
        </div>
        {docs.length > 0 ? (
          <ul className="space-y-1">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center gap-2 text-sm">
                <span className="text-slate-600">{docLabel(d.document_type)}</span>
                <a href={documentsApi.downloadUrl(d.id)} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">
                  {d.file_name}
                </a>
                <span className="text-slate-400">({d.uploaded_at?.slice(0, 10)})</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500 text-sm">尚無上傳檔案。</p>
        )}
      </div>
    </div>
  )
}
