import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sitesApi } from '../api'
import type { Site } from '../types'
import { SITE_TYPE_OPTIONS, SERVICE_TYPE_OPTIONS } from '../types'

const defaultTaxRate = 0.05

function parseServiceTypes(s: string | undefined): string[] {
  if (!s) return []
  try {
    const arr = JSON.parse(s) as string[]
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

export default function SiteForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id && id !== 'new')
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Partial<Site>>({
    name: '',
    address: '',
    contract_start: '',
    contract_end: '',
    site_type: '',
    service_types: '',
    monthly_fee_excl_tax: '',
    tax_rate: defaultTaxRate,
    monthly_fee_incl_tax: '',
    invoice_due_day: undefined,
    payment_due_day: undefined,
    remind_days: 30,
    customer_name: '',
    customer_tax_id: '',
    customer_contact: '',
    customer_phone: '',
    customer_email: '',
    invoice_title: '',
    invoice_mail_address: '',
    invoice_receiver: '',
    client_name: '',
    monthly_amount: '',
    payment_method: 'transfer',
    receivable_day: 1,
    notes: '',
  })

  useEffect(() => {
    if (!isEdit) {
      setLoading(false)
      return
    }
    sitesApi
      .get(Number(id))
      .then((s) => {
        setForm({
          ...s,
          contract_start: s.contract_start ?? '',
          contract_end: s.contract_end ?? '',
          monthly_fee_excl_tax: s.monthly_fee_excl_tax ?? '',
          tax_rate: s.tax_rate ?? defaultTaxRate,
          monthly_fee_incl_tax: s.monthly_fee_incl_tax ?? '',
          client_name: s.client_name ?? s.customer_name ?? '',
          monthly_amount: s.monthly_amount ?? s.monthly_fee_incl_tax ?? '',
          receivable_day: s.receivable_day ?? s.payment_due_day ?? undefined,
        })
      })
      .catch(alert)
      .finally(() => setLoading(false))
  }, [id, isEdit])

  const update = (key: keyof Site, value: unknown) => {
    setForm((f) => {
      const next = { ...f, [key]: value }
      if (key === 'monthly_fee_excl_tax' || key === 'tax_rate') {
        const excl = key === 'monthly_fee_excl_tax' ? Number(value) : Number(f.monthly_fee_excl_tax)
        const rate = key === 'tax_rate' ? Number(value) : Number(f.tax_rate ?? defaultTaxRate)
        if (!Number.isNaN(excl)) {
          next.monthly_fee_incl_tax = Math.round(excl * (1 + rate) * 100) / 100
        }
      }
      return next
    })
  }

  const serviceTypesArr = parseServiceTypes(form.service_types)
  const toggleServiceType = (label: string) => {
    const next = serviceTypesArr.includes(label) ? serviceTypesArr.filter((x) => x !== label) : [...serviceTypesArr, label]
    update('service_types', next.length ? JSON.stringify(next) : '')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const inclTax = form.monthly_fee_incl_tax != null && form.monthly_fee_incl_tax !== '' ? Number(form.monthly_fee_incl_tax) : undefined
    const payload: Partial<Site> = {
      ...form,
      name: form.name?.trim() || '',
      address: form.address?.trim() || '',
      contract_start: form.contract_start || '',
      contract_end: form.contract_end || undefined,
      customer_name: form.customer_name?.trim() || undefined,
      client_name: form.client_name?.trim() || form.customer_name?.trim() || form.name?.trim() || '',
      monthly_fee_incl_tax: inclTax,
      monthly_fee_excl_tax: form.monthly_fee_excl_tax != null && form.monthly_fee_excl_tax !== '' ? Number(form.monthly_fee_excl_tax) : undefined,
      tax_rate: form.tax_rate != null && form.tax_rate !== '' ? Number(form.tax_rate) : undefined,
      monthly_amount: form.monthly_amount != null && form.monthly_amount !== '' ? Number(form.monthly_amount) : inclTax,
      payment_method: form.payment_method || 'transfer',
      receivable_day: form.receivable_day ?? form.payment_due_day ?? 1,
      invoice_due_day: form.invoice_due_day ?? undefined,
      payment_due_day: form.payment_due_day ?? undefined,
      remind_days: form.remind_days ?? 30,
    }
    setSaving(true)
    const promise = isEdit ? sitesApi.update(Number(id), payload) : sitesApi.create(payload as Site)
    promise
      .then((site) => {
        alert(isEdit ? '已儲存' : '已新增')
        navigate(`/sites/${site.id}`)
      })
      .catch(alert)
      .finally(() => setSaving(false))
  }

  if (loading) return <div className="text-slate-500">載入中...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800">{isEdit ? '編輯案場' : '新增案場'}</h2>
        <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
          返回
        </button>
      </div>

      <form onSubmit={handleSubmit} className="card p-6 space-y-8">
        <div>
          <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">基本資料</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="label">案場名稱 *</label>
              <input className="input" value={form.name ?? ''} onChange={(e) => update('name', e.target.value)} required />
            </div>
            <div className="sm:col-span-2">
              <label className="label">案場地址 *</label>
              <input className="input" value={form.address ?? ''} onChange={(e) => update('address', e.target.value)} required />
            </div>
            <div>
              <label className="label">案場類型</label>
              <select className="input" value={form.site_type ?? ''} onChange={(e) => update('site_type', e.target.value)}>
                <option value="">--</option>
                {SITE_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="label">服務類型（可多選）</label>
              <div className="flex flex-wrap gap-2">
                {SERVICE_TYPE_OPTIONS.map((s) => (
                  <label key={s} className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={serviceTypesArr.includes(s)}
                      onChange={() => toggleServiceType(s)}
                    />
                    <span>{s}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="label">契約起日 *</label>
              <input type="date" className="input" value={form.contract_start ?? ''} onChange={(e) => update('contract_start', e.target.value)} required />
            </div>
            <div>
              <label className="label">契約迄日</label>
              <input type="date" className="input" value={form.contract_end ?? ''} onChange={(e) => update('contract_end', e.target.value)} />
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">費用與稅額</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="label">月服務費未稅</label>
              <input
                type="number"
                min={0}
                step={1}
                className="input"
                value={form.monthly_fee_excl_tax ?? ''}
                onChange={(e) => update('monthly_fee_excl_tax', e.target.value ? Number(e.target.value) : '')}
              />
            </div>
            <div>
              <label className="label">稅率（預設 5%）</label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                className="input"
                value={form.tax_rate ?? defaultTaxRate}
                onChange={(e) => update('tax_rate', e.target.value ? Number(e.target.value) : defaultTaxRate)}
              />
            </div>
            <div>
              <label className="label">月服務費含稅（自動計算）</label>
              <input className="input bg-slate-50" readOnly value={form.monthly_fee_incl_tax ?? ''} />
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">發票與收款期限</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">每月幾號前需將發票給客戶（1-31）</label>
              <input
                type="number"
                min={1}
                max={31}
                className="input w-24"
                value={form.invoice_due_day ?? ''}
                onChange={(e) => update('invoice_due_day', e.target.value ? Number(e.target.value) : undefined)}
              />
            </div>
            <div>
              <label className="label">每月幾號前客戶需繳交服務費（1-31）</label>
              <input
                type="number"
                min={1}
                max={31}
                className="input w-24"
                value={form.payment_due_day ?? ''}
                onChange={(e) => update('payment_due_day', e.target.value ? Number(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">客戶資料（開票與聯絡）</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">客戶名稱</label>
              <input className="input" value={form.customer_name ?? ''} onChange={(e) => update('customer_name', e.target.value)} />
            </div>
            <div>
              <label className="label">統一編號</label>
              <input className="input" value={form.customer_tax_id ?? ''} onChange={(e) => update('customer_tax_id', e.target.value)} />
            </div>
            <div>
              <label className="label">聯絡人</label>
              <input className="input" value={form.customer_contact ?? ''} onChange={(e) => update('customer_contact', e.target.value)} />
            </div>
            <div>
              <label className="label">電話</label>
              <input className="input" value={form.customer_phone ?? ''} onChange={(e) => update('customer_phone', e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Email</label>
              <input type="email" className="input" value={form.customer_email ?? ''} onChange={(e) => update('customer_email', e.target.value)} />
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">發票資訊</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="label">發票抬頭</label>
              <input className="input" value={form.invoice_title ?? ''} onChange={(e) => update('invoice_title', e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <label className="label">郵寄地址</label>
              <input className="input" value={form.invoice_mail_address ?? ''} onChange={(e) => update('invoice_mail_address', e.target.value)} />
            </div>
            <div>
              <label className="label">收件人</label>
              <input className="input" value={form.invoice_receiver ?? ''} onChange={(e) => update('invoice_receiver', e.target.value)} />
            </div>
            <div>
              <label className="label">契約到期提醒天數（預設 30）</label>
              <input
                type="number"
                min={1}
                max={365}
                className="input w-24"
                value={form.remind_days ?? 30}
                onChange={(e) => update('remind_days', e.target.value ? Number(e.target.value) : 30)}
              />
            </div>
          </div>
        </div>

        <div className="flex gap-2 pt-4">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? '儲存中...' : (isEdit ? '儲存' : '新增')}
          </button>
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
