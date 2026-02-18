import QRCode from 'qrcode'
import { FormEvent, useEffect, useState } from 'react'
import { patrolApi } from '../api'
import type { PatrolPoint, PatrolPointQr } from '../types'

type FormState = {
  point_code: string
  point_name: string
  site_name: string
  location: string
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  point_code: '',
  point_name: '',
  site_name: '',
  location: '',
  is_active: true,
}

function downloadDataUrl(dataUrl: string, filename: string) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  a.click()
}

export default function PatrolPointsPage() {
  const [rows, setRows] = useState<PatrolPoint[]>([])
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [qrMap, setQrMap] = useState<Record<number, { payload: PatrolPointQr; dataUrl: string }>>({})

  async function loadData() {
    setLoading(true)
    try {
      const items = await patrolApi.listPoints()
      setRows(items)
    } catch (err) {
      setError(err instanceof Error ? err.message : '讀取失敗')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  function bindEdit(row: PatrolPoint) {
    setEditingId(row.id)
    setForm({
      point_code: row.point_code,
      point_name: row.point_name,
      site_name: row.site_name || '',
      location: row.location || '',
      is_active: row.is_active,
    })
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      if (editingId) {
        await patrolApi.updatePoint(editingId, {
          point_code: form.point_code,
          point_name: form.point_name,
          site_name: form.site_name || null,
          location: form.location || null,
          is_active: form.is_active,
        })
      } else {
        await patrolApi.createPoint({
          point_code: form.point_code,
          point_name: form.point_name,
          site_name: form.site_name || null,
          location: form.location || null,
          is_active: form.is_active,
        })
      }
      setForm(EMPTY_FORM)
      setEditingId(null)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : '儲存失敗')
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm('確定刪除此巡邏點？')) return
    setError('')
    try {
      await patrolApi.deletePoint(id)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : '刪除失敗')
    }
  }

  async function onGenQr(row: PatrolPoint) {
    try {
      const payload = await patrolApi.getPointQr(row.public_id)
      const dataUrl = await QRCode.toDataURL(payload.qr_url, { width: 260, margin: 1 })
      setQrMap((prev) => ({ ...prev, [row.id]: { payload, dataUrl } }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '產生 QR 失敗')
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">巡邏點管理</h1>
      <form onSubmit={onSubmit} className="rounded border border-slate-300 bg-white p-4 grid grid-cols-1 md:grid-cols-4 gap-3">
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
          placeholder="位置說明（選填）"
          className="rounded border border-slate-300 px-3 py-2"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((s) => ({ ...s, is_active: e.target.checked }))}
          />
          啟用此巡邏點
        </label>
        <button className="rounded bg-sky-500 text-white font-semibold px-3 py-2">
          {editingId ? '更新巡邏點' : '新增巡邏點'}
        </button>
      </form>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="rounded border border-slate-300 bg-white overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="text-left p-2">編號</th>
              <th className="text-left p-2">名稱</th>
              <th className="text-left p-2">案場</th>
              <th className="text-left p-2">位置</th>
              <th className="text-left p-2">狀態</th>
              <th className="text-left p-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-slate-200 align-top">
                <td className="p-2">{r.point_code}</td>
                <td className="p-2">{r.point_name}</td>
                <td className="p-2">{r.site_name || '-'}</td>
                <td className="p-2">{r.location || '-'}</td>
                <td className="p-2">{r.is_active ? '啟用' : '停用'}</td>
                <td className="p-2 space-x-2">
                  <button className="underline" onClick={() => bindEdit(r)}>編輯</button>
                  <button className="underline text-rose-600" onClick={() => void onDelete(r.id)}>刪除</button>
                  <button className="underline text-emerald-700" onClick={() => void onGenQr(r)}>產生 QR</button>
                  {qrMap[r.id] && (
                    <div className="mt-2 space-y-2">
                      <img src={qrMap[r.id].dataUrl} alt={`point-${r.id}-qr`} className="w-40 h-40 border border-slate-200" />
                      <div className="text-xs break-all max-w-sm">{qrMap[r.id].payload.qr_url}</div>
                      <button
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                        onClick={() => downloadDataUrl(qrMap[r.id].dataUrl, `patrol_point_${r.point_code}.png`)}
                      >
                        下載 PNG
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr><td className="p-3 text-slate-500" colSpan={6}>尚無資料</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
