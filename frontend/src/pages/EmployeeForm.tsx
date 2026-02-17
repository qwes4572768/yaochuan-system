import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { employeesApi, insuranceApi, insuranceBracketsApi } from '../api'
import { REGISTRATION_OPTIONS } from '../constants/registrationType'
import type { Employee, Dependent, SalaryBracketItem } from '../types'

const RELATIONS = ['配偶', '子女', '父母', '祖父母', '其他']
const CITIES = ['桃園市', '台北市', '其他']
const DISABILITY_LEVELS = ['輕度', '中度', '重度', '極重度']
const SALARY_TYPES = ['月薪', '日薪', '時薪']
const PAY_METHOD_OPTIONS = [
  { value: 'SECURITY_FIRST', label: '保全一銀' },
  { value: 'APARTMENT_FIRST', label: '公寓一銀' },
  { value: 'SMITH_FIRST', label: '史密斯一銀' },
  { value: 'CASH', label: '領現' },
  { value: 'OTHER_BANK', label: '其他銀行' },
]
const COMPANY_PAY_MODE_OPTIONS = [
  { value: 'monthly', label: '月薪' },
  { value: 'hourly', label: '時薪' },
  { value: 'daily', label: '日薪' },
]

const emptyDependent: Omit<Dependent, 'id' | 'employee_id'> = {
  name: '',
  birth_date: '',
  national_id: '',
  relation: '子女',
  city: '',
  is_disabled: false,
  disability_level: '',
  notes: '',
}

export default function EmployeeForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = id && id !== 'new'
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [brackets, setBrackets] = useState<SalaryBracketItem[]>([])
  const [bracketSource, setBracketSource] = useState<{ file_name?: string; imported_at?: string; fromDb: boolean } | null>(null)
  const [form, setForm] = useState<Partial<Employee>>({
    name: '',
    birth_date: '',
    national_id: '',
    reg_address: '',
    live_address: '',
    live_same_as_reg: false,
    salary_type: '',
    salary_value: '',
    insured_salary_level: '',
    enroll_date: '',
    cancel_date: '',
    dependent_count: 0,
    pension_self_6: false,
    registration_type: 'security',
    notes: '',
    pay_method: 'CASH',
    bank_code: '',
    branch_code: '',
    bank_account: '',
    property_pay_mode: undefined,
    security_pay_mode: undefined,
    smith_pay_mode: undefined,
    lixiang_pay_mode: undefined,
    weekly_amount: '',
    property_salary: '',
  })
  const [dependents, setDependents] = useState<Omit<Dependent, 'id' | 'employee_id'>[]>([])
  const [salaryInput, setSalaryInput] = useState<string>('')

  useEffect(() => {
    insuranceApi.brackets().then(setBrackets).catch(() => [])
    insuranceBracketsApi.getLatest().then((r) => {
      if (r.has_import && r.file_name != null) {
        setBracketSource({
          file_name: r.file_name,
          imported_at: r.imported_at ?? undefined,
          fromDb: true,
        })
      } else {
        setBracketSource({ fromDb: false })
      }
    }).catch(() => setBracketSource({ fromDb: false }))
  }, [])

  useEffect(() => {
    if (!isEdit) {
      setLoading(false)
      return
    }
    employeesApi.get(Number(id)).then((e) => {
      setForm((prev) => ({
        ...prev,
        ...e,
        pension_self_6: e.pension_self_6 ?? prev.pension_self_6 ?? false,
        registration_type: (e.registration_type === 'property' || e.registration_type === 'smith' || e.registration_type === 'lixiang') ? e.registration_type : 'security',
      }))
      setDependents(
        (e.dependents || []).map((d) => ({
          name: d.name,
          birth_date: d.birth_date || '',
          national_id: d.national_id || '',
          relation: d.relation,
          city: d.city || '',
          is_disabled: d.is_disabled ?? false,
          disability_level: d.disability_level || '',
          notes: d.notes || '',
        }))
      )
    }).catch(alert).finally(() => setLoading(false))
  }, [id, isEdit])

  const update = (key: keyof Employee, value: any) => {
    setForm((f) => {
      const next = { ...f, [key]: value }
      if (key === 'live_same_as_reg' && value && f.reg_address) next.live_address = f.reg_address
      if (key === 'reg_address' && f.live_same_as_reg) next.live_address = value
       // 切換領薪方式為領現時，清空銀行欄位
      if (key === 'pay_method' && value === 'CASH') {
        next.bank_code = ''
        next.branch_code = ''
        next.bank_account = ''
      }
      return next
    })
  }

  const maxDependents = Math.max(0, form.dependent_count ?? 0)
  const addDependent = () => {
    setDependents((d) => (d.length >= maxDependents ? d : [...d, { ...emptyDependent }]))
  }

  const updateDependent = (index: number, key: keyof Dependent, value: any) => {
    setDependents((d) => {
      const next = [...d]
      next[index] = { ...next[index], [key]: value }
      return next
    })
  }

  const removeDependent = (index: number) => {
    setDependents((d) => d.filter((_, i) => i !== index))
  }

  const handleSalaryInputBlur = () => {
    const n = Number(salaryInput)
    if (!Number.isNaN(n) && n > 0) {
      insuranceApi.salaryToLevel(n).then((r) => update('insured_salary_level', r.insured_salary_level)).catch(() => {})
    }
  }

  const submit = async () => {
    if (!form.name?.trim()) {
      alert('請填寫姓名')
      return
    }
    if (!form.birth_date) {
      alert('請填寫出生年月日')
      return
    }
    if (!form.national_id?.trim()) {
      alert('請填寫身分證字號')
      return
    }
    if (form.national_id?.includes('*')) {
      alert('身分證字號不可為遮罩值，請由編輯頁重新載入取得完整資料後再儲存')
      return
    }
    if (!form.reg_address?.trim()) {
      alert('請填寫戶籍地址')
      return
    }
    if (form.reg_address?.includes('*')) {
      alert('戶籍地址不可為遮罩值，請由編輯頁重新載入取得完整資料後再儲存')
      return
    }
    if (!form.live_address?.trim()) {
      alert('請填寫居住地址')
      return
    }
    if (form.live_address?.includes('*')) {
      alert('居住地址不可為遮罩值，請由編輯頁重新載入取得完整資料後再儲存')
      return
    }
    const dependentWithMask = dependents.find((d) => d.national_id && d.national_id.includes('*'))
    if (dependentWithMask) {
      alert('眷屬身分證字號不可為遮罩值，請填寫完整資料')
      return
    }
    const payMethod = (form.pay_method as Employee['pay_method']) ?? 'CASH'
    const propertyPayMode = ((form.property_pay_mode as string) || '').trim() || undefined
    const securityPayMode = ((form.security_pay_mode as string) || '').trim() || undefined
    const smithPayMode = ((form.smith_pay_mode as string) || '').trim() || undefined
    const lixiangPayMode = ((form.lixiang_pay_mode as string) || '').trim() || undefined
    const isProperty = form.registration_type === 'property'
    const weeklyAmount = form.weekly_amount != null && form.weekly_amount !== '' ? Number(form.weekly_amount) : undefined
    const propertySalary = form.property_salary != null && form.property_salary !== '' ? Number(form.property_salary) : undefined
    const bankCode = (form.bank_code ?? '').trim()
    const branchCode = (form.branch_code ?? '').trim()
    const bankAccount = (form.bank_account ?? '').trim()
    if (bankCode.includes('*') || branchCode.includes('*') || bankAccount.includes('*')) {
      alert('銀行代碼/分行代碼/銀行帳號不可包含 *，請填寫完整數字')
      return
    }
    if (payMethod === 'CASH') {
      form.bank_code = ''
      form.branch_code = ''
      form.bank_account = ''
    } else {
      if (!bankCode || !branchCode || !bankAccount) {
        alert('非「領現」時，銀行代碼、分行代碼、銀行帳號皆為必填')
        return
      }
      if (!/^\d{3}$/.test(bankCode)) {
        alert('銀行代碼須為 3 碼數字')
        return
      }
      if (!/^\d{4}$/.test(branchCode)) {
        alert('分行代碼須為 4 碼數字')
        return
      }
      if (!/^\d{6,20}$/.test(bankAccount)) {
        alert('銀行帳號須為 6～20 碼數字')
        return
      }
    }
    setSaving(true)
    try {
      const payload: Employee = {
        ...form,
        name: form.name!.trim(),
        birth_date: form.birth_date!,
        national_id: form.national_id!.trim(),
        reg_address: form.reg_address!.trim(),
        live_address: form.live_address!.trim(),
        live_same_as_reg: form.live_same_as_reg ?? false,
        salary_type: form.salary_type || undefined,
        salary_value: form.salary_value != null ? Number(form.salary_value) : undefined,
        insured_salary_level: form.insured_salary_level != null ? Number(form.insured_salary_level) : undefined,
        pension_self_6: form.pension_self_6 ?? false,
        registration_type: (form.registration_type === 'property' || form.registration_type === 'smith' || form.registration_type === 'lixiang') ? form.registration_type : 'security',
        enroll_date: form.enroll_date || undefined,
        cancel_date: form.cancel_date || undefined,
        dependent_count: Math.max(0, form.dependent_count ?? 0),
        pay_method: payMethod,
        bank_code: payMethod === 'CASH' ? undefined : bankCode,
        branch_code: payMethod === 'CASH' ? undefined : branchCode,
        bank_account: payMethod === 'CASH' ? undefined : bankAccount,
        property_pay_mode: propertyPayMode as Employee['property_pay_mode'],
        security_pay_mode: securityPayMode as Employee['security_pay_mode'],
        smith_pay_mode: smithPayMode as Employee['smith_pay_mode'],
        lixiang_pay_mode: lixiangPayMode as Employee['lixiang_pay_mode'],
        weekly_amount: isProperty ? weeklyAmount : undefined,
        property_salary: isProperty ? propertySalary : undefined,
        dependents:
          dependents.filter((d) => d.name.trim()).length > 0
            ? dependents.filter((d) => d.name.trim()).map((d) => ({
                name: d.name.trim(),
                birth_date: d.birth_date || undefined,
                national_id: d.national_id || undefined,
                relation: d.relation || '其他',
                city: d.city || undefined,
                is_disabled: d.is_disabled ?? false,
                disability_level: d.is_disabled ? d.disability_level || undefined : undefined,
                notes: d.notes || undefined,
              }))
            : undefined,
      }
      if (isEdit) {
        await employeesApi.update(Number(id), payload)
        navigate(`/employees/${id}`)
      } else {
        const created = await employeesApi.create(payload)
        navigate(`/employees/${created.id}`)
      }
    } catch (e: any) {
      alert(e?.message || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const showDependents = (form.dependent_count ?? 0) > 0
  const dependentsToShow = showDependents ? dependents : []

  if (loading) return <div className="text-slate-500">載入中...</div>

  return (
    <div className="space-y-6 max-w-3xl">
      <h2 className="text-2xl font-bold">{isEdit ? '編輯員工' : '新增員工'}</h2>

      <div className="card p-6 space-y-4">
        <h3 className="font-semibold text-slate-700 border-b pb-2">基本資料</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="label">姓名 *</label>
            <input className="input" value={form.name ?? ''} onChange={(e) => update('name', e.target.value)} />
          </div>
          <div>
            <label className="label">出生年月日 *</label>
            <input
              type="date"
              className="input"
              value={form.birth_date ?? ''}
              onChange={(e) => update('birth_date', e.target.value)}
            />
          </div>
          <div>
            <label className="label">身分證字號 *</label>
            <input
              className="input"
              value={form.national_id ?? ''}
              onChange={(e) => update('national_id', e.target.value)}
              placeholder="A123456789"
              maxLength={10}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="label">戶籍地址 *</label>
            <input
              className="input"
              value={form.reg_address ?? ''}
              onChange={(e) => update('reg_address', e.target.value)}
            />
          </div>
          <div className="sm:col-span-2 flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.live_same_as_reg ?? false}
                onChange={(e) => update('live_same_as_reg', e.target.checked)}
              />
              <span>同戶籍</span>
            </label>
            <span className="text-slate-500 text-sm">（勾選後居住地址自動帶入戶籍地址並鎖定）</span>
          </div>
          <div className="sm:col-span-2">
            <label className="label">居住地址 *</label>
            <input
              className="input"
              value={form.live_address ?? ''}
              onChange={(e) => update('live_address', e.target.value)}
              disabled={form.live_same_as_reg ?? false}
              readOnly={form.live_same_as_reg ?? false}
              placeholder={form.live_same_as_reg ? '同戶籍地址' : ''}
            />
          </div>
          <div>
            <label className="label">薪資類型</label>
            <select
              className="input"
              value={form.salary_type ?? ''}
              onChange={(e) => update('salary_type', e.target.value)}
            >
              <option value="">--</option>
              {SALARY_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">薪資數值</label>
            <input
              type="number"
              min={0}
              step={1}
              className="input"
              value={form.salary_value ?? ''}
              onChange={(e) => update('salary_value', e.target.value ? Number(e.target.value) : '')}
            />
          </div>
          <div>
            <div className="mb-1 text-sm text-slate-600">
              {bracketSource?.fromDb && bracketSource.file_name
                ? `目前使用的級距來源：${bracketSource.file_name}${bracketSource.imported_at ? `（匯入時間：${bracketSource.imported_at.replace('T', ' ').slice(0, 16)}）` : ''}`
                : bracketSource ? '級距來源：系統預設（YAML）' : null}
            </div>
            <label className="label">加保投保薪資級距</label>
            <select
              className="input"
              value={form.insured_salary_level != null && form.insured_salary_level !== '' ? String(form.insured_salary_level) : ''}
              onChange={(e) => update('insured_salary_level', e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">-- 請選擇級距 --</option>
              {brackets.map((b) => (
                <option key={b.level} value={String(b.level)}>
                  {b.level}（{b.low}～{b.high}）
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">或輸入金額自動對應級距</label>
            <input
              type="number"
              min={0}
              className="input"
              value={salaryInput}
              onChange={(e) => setSalaryInput(e.target.value)}
              onBlur={handleSalaryInputBlur}
              placeholder="輸入薪資金額"
            />
          </div>
          <div>
            <label className="label">領薪方式</label>
            <select
              className="input"
              value={form.pay_method ?? 'CASH'}
              onChange={(e) => update('pay_method', e.target.value)}
            >
              {PAY_METHOD_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          {form.pay_method && form.pay_method !== 'CASH' && (
            <>
              <div>
                <label className="label">銀行代碼 *</label>
                <input
                  className="input"
                  value={form.bank_code ?? ''}
                  onChange={(e) => {
                    const v = e.target.value.replace(/\D/g, '').slice(0, 3)
                    update('bank_code', v)
                  }}
                  maxLength={3}
                  placeholder="3 碼數字"
                />
              </div>
              {form.bank_code && (
                <div>
                  <label className="label">分行代碼 *</label>
                  <input
                    className="input"
                    value={form.branch_code ?? ''}
                    onChange={(e) => {
                      const v = e.target.value.replace(/\D/g, '').slice(0, 4)
                      update('branch_code', v)
                    }}
                    maxLength={4}
                    placeholder="4 碼數字"
                  />
                </div>
              )}
              {form.bank_code && form.branch_code && (
                <div className="sm:col-span-2">
                  <label className="label">銀行帳號 *</label>
                  <input
                    className="input"
                    value={form.bank_account ?? ''}
                    onChange={(e) => {
                      const v = e.target.value.replace(/\D/g, '').slice(0, 20)
                      update('bank_account', v)
                    }}
                    maxLength={20}
                    placeholder="6～20 碼數字"
                  />
                </div>
              )}
            </>
          )}
          <div>
            <label className="label">登載身份</label>
            <div className="flex flex-wrap gap-4">
              {REGISTRATION_OPTIONS.map((opt) => (
                <label key={opt.key} className="inline-flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="registration_type"
                    checked={(form.registration_type ?? 'security') === opt.key}
                    onChange={() => update('registration_type', opt.key)}
                    className="border-slate-300"
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="sm:col-span-2">
            <h4 className="font-semibold text-slate-700 border-b pb-2 mb-3">計薪設定</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="label">物業計薪模式</label>
                <select
                  className="input"
                  value={form.property_pay_mode ?? ''}
                  onChange={(e) => update('property_pay_mode', e.target.value || undefined)}
                >
                  <option value="">-- 未設定 --</option>
                  {COMPANY_PAY_MODE_OPTIONS.map((opt) => (
                    <option key={`property-${opt.value}`} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">保全計薪模式</label>
                <select
                  className="input"
                  value={form.security_pay_mode ?? ''}
                  onChange={(e) => update('security_pay_mode', e.target.value || undefined)}
                >
                  <option value="">-- 未設定 --</option>
                  {COMPANY_PAY_MODE_OPTIONS.map((opt) => (
                    <option key={`security-${opt.value}`} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">史密斯計薪模式</label>
                <select
                  className="input"
                  value={form.smith_pay_mode ?? ''}
                  onChange={(e) => update('smith_pay_mode', e.target.value || undefined)}
                >
                  <option value="">-- 未設定 --</option>
                  {COMPANY_PAY_MODE_OPTIONS.map((opt) => (
                    <option key={`smith-${opt.value}`} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">立翔人力計薪模式</label>
                <select
                  className="input"
                  value={form.lixiang_pay_mode ?? ''}
                  onChange={(e) => update('lixiang_pay_mode', e.target.value || undefined)}
                >
                  <option value="">-- 未設定 --</option>
                  {COMPANY_PAY_MODE_OPTIONS.map((opt) => (
                    <option key={`lixiang-${opt.value}`} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          {form.registration_type === 'property' && (
            <>
              <div>
                <label className="label">物業月薪基準</label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  className="input"
                  value={form.property_salary ?? ''}
                  onChange={(e) => update('property_salary', e.target.value ? Number(e.target.value) : '')}
                  placeholder="請輸入月薪基準"
                />
              </div>
              <div>
                <label className="label">每週金額（選填）</label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  className="input"
                  value={form.weekly_amount ?? ''}
                  onChange={(e) => update('weekly_amount', e.target.value ? Number(e.target.value) : '')}
                  placeholder="可留空"
                />
              </div>
            </>
          )}
          <div>
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.pension_self_6 ?? false}
                onChange={(e) => update('pension_self_6', e.target.checked)}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-700">自提6%（金額同級距表公司負擔勞退6%，儲存後試算會帶入）</span>
            </label>
          </div>
          <div>
            <label className="label">加保日期</label>
            <input
              type="date"
              className="input"
              value={form.enroll_date ?? ''}
              onChange={(e) => update('enroll_date', e.target.value)}
            />
          </div>
          <div>
            <label className="label">退保日期</label>
            <input
              type="date"
              className="input"
              value={form.cancel_date ?? ''}
              onChange={(e) => update('cancel_date', e.target.value)}
            />
          </div>
          <div>
            <label className="label">眷屬數量</label>
            <input
              type="number"
              min={0}
              className="input w-24"
              value={form.dependent_count ?? 0}
              onChange={(e) => {
                const n = Math.max(0, parseInt(e.target.value, 10) || 0)
                update('dependent_count', n)
                setDependents((d) => d.slice(0, n))
              }}
            />
            <span className="text-slate-500 text-sm ml-2">（輸入後下方可新增眷屬，最多 N 筆）</span>
          </div>
          <div className="sm:col-span-2">
            <label className="label">備註</label>
            <textarea className="input min-h-[80px]" value={form.notes ?? ''} onChange={(e) => update('notes', e.target.value)} />
          </div>
        </div>
      </div>

      {showDependents && (
        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-700 border-b pb-2">眷屬資料</h3>
            <button
              type="button"
              onClick={addDependent}
              disabled={dependentsToShow.length >= maxDependents}
              className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              新增眷屬（{dependentsToShow.length}/{maxDependents}）
            </button>
          </div>
          {dependentsToShow.length === 0 ? (
            <p className="text-slate-500 text-sm">點「新增眷屬」新增眷屬，最多 {maxDependents} 筆。</p>
          ) : (
            <div className="space-y-3">
              {dependentsToShow.map((d, i) => (
                <div key={i} className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-slate-600">眷屬 #{i + 1}</span>
                    <button type="button" onClick={() => removeDependent(i)} className="text-red-600 text-sm hover:underline">
                      移除
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="label text-xs">關係</label>
                      <select className="input text-sm" value={d.relation} onChange={(e) => updateDependent(i, 'relation', e.target.value)}>
                        {RELATIONS.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="label text-xs">姓名</label>
                      <input className="input text-sm" value={d.name} onChange={(e) => updateDependent(i, 'name', e.target.value)} />
                    </div>
                    <div>
                      <label className="label text-xs">身分證字號</label>
                      <input className="input text-sm" value={d.national_id ?? ''} onChange={(e) => updateDependent(i, 'national_id', e.target.value)} maxLength={10} />
                    </div>
                    <div>
                      <label className="label text-xs">出生年月日</label>
                      <input type="date" className="input text-sm" value={d.birth_date ?? ''} onChange={(e) => updateDependent(i, 'birth_date', e.target.value)} />
                    </div>
                    <div>
                      <label className="label text-xs">居住縣市</label>
                      <select className="input text-sm" value={d.city ?? ''} onChange={(e) => updateDependent(i, 'city', e.target.value)}>
                        <option value="">--</option>
                        {CITIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-end">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={d.is_disabled} onChange={(e) => updateDependent(i, 'is_disabled', e.target.checked)} />
                        <span className="text-sm">是否身障</span>
                      </label>
                    </div>
                    {d.is_disabled && (
                      <div>
                        <label className="label text-xs">身障等級</label>
                        <select className="input text-sm" value={d.disability_level ?? ''} onChange={(e) => updateDependent(i, 'disability_level', e.target.value)}>
                          <option value="">--</option>
                          {DISABILITY_LEVELS.map((l) => (
                            <option key={l} value={l}>{l}</option>
                          ))}
                        </select>
                      </div>
                    )}
                    <div className="sm:col-span-2">
                      <label className="label text-xs">備註</label>
                      <input className="input text-sm" value={d.notes ?? ''} onChange={(e) => updateDependent(i, 'notes', e.target.value)} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={submit} disabled={saving} className="btn-primary">
          {saving ? '儲存中...' : '儲存'}
        </button>
        <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
          取消
        </button>
      </div>
    </div>
  )
}
