import QRCode from 'qrcode'
import { useEffect, useState } from 'react'
import { patrolApi } from '../api'
import type { PatrolBindingCode } from '../types'

export default function PatrolBindingLegacyPage() {
  const [data, setData] = useState<PatrolBindingCode | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function createBinding() {
    setLoading(true)
    setError('')
    try {
      const res = await patrolApi.createBindingCode(10)
      setData(res)
      const url = await QRCode.toDataURL(res.qr_value, { width: 300, margin: 1 })
      setQrDataUrl(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : '產生失敗')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void createBinding()
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">舊版設備綁定碼（10分鐘有效）</h1>
      <p className="text-sm text-slate-600">此頁面保留舊流程，供需要裝置綁定時使用。</p>
      <button
        onClick={() => void createBinding()}
        disabled={loading}
        className="rounded bg-emerald-500 px-4 py-2 text-slate-950 font-semibold disabled:opacity-60"
      >
        {loading ? '產生中...' : '重新產生綁定 QR'}
      </button>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {data && (
        <div className="rounded border border-slate-300 p-4 bg-white">
          <div className="text-sm mb-2">綁定碼：<code>{data.code}</code></div>
          <div className="text-sm mb-2">到期：{new Date(data.expires_at).toLocaleString()}</div>
          <div className="text-sm mb-3 break-all">連結：{data.bind_url}</div>
          {qrDataUrl && <img src={qrDataUrl} alt="binding-qr" className="w-64 h-64 object-contain border border-slate-200" />}
        </div>
      )}
    </div>
  )
}
