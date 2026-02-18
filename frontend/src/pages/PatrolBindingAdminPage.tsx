import QRCode from 'qrcode'
import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { patrolApi } from '../api'
import type { PatrolPoint } from '../types'

type FormState = {
  point_code: string
  point_name: string
  site_name: string
  location: string
}

const EMPTY_FORM: FormState = {
  point_code: '',
  point_name: '',
  site_name: '',
  location: '',
}

function downloadPng(dataUrl: string, filename: string) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  a.click()
}

export default function PatrolBindingAdminPage() {
  const [rows, setRows] = useState<PatrolPoint[]>([])
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [qrMap, setQrMap] = useState<Record<number, string>>({})

  async function loadPoints() {
    setLoading(true)
    try {
      const points = await patrolApi.listPoints()
      setRows(points)
      setQrMap({})
      await Promise.all(points.map(async (p) => {
        const dataUrl = await QRCode.toDataURL(p.qr_url, { width: 260, margin: 1 })
        setQrMap((prev) => ({ ...prev, [p.id]: dataUrl }))
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '讀取巡邏點失敗')
    } finally {
      setLoading(false)
    }
  }

  async function onCreatePoint(e: FormEvent) {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      await patrolApi.createPoint({
        point_code: form.point_code.trim(),
        point_name: form.point_name.trim(),
        site_name: form.site_name.trim() || null,
        location: form.location.trim() || null,
        is_active: true,
      })
      setForm(EMPTY_FORM)
      await loadPoints()
    } catch (err) {
      setError(err instanceof Error ? err.message : '新增巡邏點失敗')
    } finally {
      setCreating(false)
    }
  }

  useEffect(() => {
    void loadPoints()
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">永久巡邏點 QR</h1>
      <p className="text-sm text-slate-600">QR 內容固定為巡邏點網址，不會因部署或更新失效。</p>
      <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        舊版 10 分鐘綁定碼流程已移至
        {' '}
        <Link to="/patrol-admin/bindings/legacy" className="underline font-semibold">舊版設備綁定碼頁面</Link>
        。
      </div>
      <form onSubmit={onCreatePoint} className="rounded border border-slate-300 bg-white p-4 grid grid-cols-1 md:grid-cols-5 gap-3">
        <input
          value={form.point_code}
          onChange={(e) => setForm((s) => ({ ...s, point_code: e.target.value }))}
          required
          placeholder="巡邏點編號"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <input
          value={form.point_name}
          onChange={(e) => setForm((s) => ({ ...s, point_name: e.target.value }))}
          required
          placeholder="巡邏點名稱"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <input
          value={form.site_name}
          onChange={(e) => setForm((s) => ({ ...s, site_name: e.target.value }))}
          placeholder="案場名稱"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <input
          value={form.location}
          onChange={(e) => setForm((s) => ({ ...s, location: e.target.value }))}
          placeholder="位置說明"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={creating}
          className="rounded bg-emerald-500 px-4 py-2 text-slate-950 font-semibold disabled:opacity-60"
        >
          {creating ? '新增中...' : '新增巡邏點'}
        </button>
      </form>
      <button
        onClick={() => void loadPoints()}
        disabled={loading}
        className="rounded bg-sky-500 px-4 py-2 text-white font-semibold disabled:opacity-60"
      >
        {loading ? '讀取中...' : '重新載入巡邏點'}
      </button>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="rounded border border-slate-300 bg-white overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="text-left p-2">巡邏點</th>
              <th className="text-left p-2">案場</th>
              <th className="text-left p-2">固定 QR URL</th>
              <th className="text-left p-2">QR</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-200 align-top">
                <td className="p-2">
                  <div className="font-semibold">{row.point_name}</div>
                  <div className="text-xs text-slate-500">{row.point_code}</div>
                </td>
                <td className="p-2">{row.site_name || '-'}</td>
                <td className="p-2">
                  <div className="text-xs break-all max-w-md">{row.qr_url}</div>
                </td>
                <td className="p-2">
                  {qrMap[row.id] ? (
                    <div className="space-y-2">
                      <img src={qrMap[row.id]} alt={`patrol-point-${row.id}-qr`} className="w-40 h-40 border border-slate-200" />
                      <button
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                        onClick={() => downloadPng(qrMap[row.id], `patrol_point_${row.point_code}.png`)}
                      >
                        匯出 PNG
                      </button>
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400">產生中...</span>
                  )}
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr><td className="p-3 text-slate-500" colSpan={4}>尚無巡邏點，請先建立。</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
