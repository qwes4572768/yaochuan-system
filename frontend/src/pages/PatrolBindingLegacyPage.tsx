import QRCode from 'qrcode'
import { useEffect, useState } from 'react'
import { patrolApi } from '../api'
import type { PatrolBindingCode, PatrolPermanentQr } from '../types'

function downloadPng(dataUrl: string, filename: string) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  a.click()
}

export default function PatrolBindingLegacyPage() {
  const [data, setData] = useState<PatrolBindingCode | null>(null)
  const [legacyQrDataUrl, setLegacyQrDataUrl] = useState('')
  const [permanent, setPermanent] = useState<PatrolPermanentQr | null>(null)
  const [permanentQrDataUrl, setPermanentQrDataUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [permanentLoading, setPermanentLoading] = useState(false)
  const [error, setError] = useState('')

  async function createBinding() {
    setLoading(true)
    setError('')
    try {
      const res = await patrolApi.createBindingCode(10)
      setData(res)
      const url = await QRCode.toDataURL(res.qr_value, { width: 300, margin: 1 })
      setLegacyQrDataUrl(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : '產生失敗')
    } finally {
      setLoading(false)
    }
  }

  async function createPermanentBindingQr() {
    setPermanentLoading(true)
    setError('')
    try {
      const res = await patrolApi.createPermanentQr()
      setPermanent(res)
      const url = await QRCode.toDataURL(res.qr_url, { width: 300, margin: 1 })
      setPermanentQrDataUrl(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : '產生永久 QR 失敗')
    } finally {
      setPermanentLoading(false)
    }
  }

  useEffect(() => {
    void createBinding()
    void createPermanentBindingQr()
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">舊版設備綁定碼（10分鐘有效）</h1>
      <p className="text-sm text-slate-600">此頁面同時提供舊版 10 分鐘綁定 QR 與永久綁定 QR。</p>
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
          {legacyQrDataUrl && (
            <div className="space-y-2">
              <img src={legacyQrDataUrl} alt="binding-qr" className="w-64 h-64 object-contain border border-slate-200" />
              <button
                className="rounded border border-slate-300 px-2 py-1 text-xs"
                onClick={() => downloadPng(legacyQrDataUrl, `patrol_legacy_bind_${data.code}.png`)}
              >
                匯出 PNG
              </button>
            </div>
          )}
        </div>
      )}

      <div className="rounded border border-slate-300 p-4 bg-white space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">永久綁定 QR（永不過期）</h2>
          <button
            onClick={() => void createPermanentBindingQr()}
            disabled={permanentLoading}
            className="rounded bg-sky-500 px-3 py-1.5 text-white text-sm font-semibold disabled:opacity-60"
          >
            {permanentLoading ? '產生中...' : '重產生永久 QR'}
          </button>
        </div>
        {permanent && (
          <>
            <div className="text-sm">狀態：<span className="font-semibold text-emerald-700">永久有效</span></div>
            <div className="text-sm">裝置永久識別碼：<code>{permanent.device_public_id}</code></div>
            <div className="text-sm break-all">連結：{permanent.qr_url}</div>
            {permanentQrDataUrl && (
              <div className="space-y-2">
                <img src={permanentQrDataUrl} alt="permanent-binding-qr" className="w-64 h-64 object-contain border border-slate-200" />
                <button
                  className="rounded border border-slate-300 px-2 py-1 text-xs"
                  onClick={() => downloadPng(permanentQrDataUrl, `patrol_permanent_bind_${permanent.device_public_id}.png`)}
                >
                  匯出 PNG
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
