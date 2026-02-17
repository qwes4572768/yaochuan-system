import { BrowserMultiFormatReader, type IScannerControls } from '@zxing/browser'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { clearPatrolDeviceToken, patrolApi } from '../api'
import type { PatrolCheckinResponse, PatrolDeviceInfo } from '../types'

export default function PatrolPage() {
  const [deviceInfo, setDeviceInfo] = useState<PatrolDeviceInfo | null>(null)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PatrolCheckinResponse | null>(null)
  const [manualQr, setManualQr] = useState('')
  const [scanning, setScanning] = useState(false)
  const [loading, setLoading] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const scannerControlsRef = useRef<IScannerControls | null>(null)

  useEffect(() => {
    let mounted = true
    patrolApi.meDevice()
      .then((res) => {
        if (mounted) setDeviceInfo(res)
      })
      .catch((err) => {
        if (mounted) setError(err instanceof Error ? err.message : '請先完成設備綁定')
      })
    return () => {
      mounted = false
      scannerControlsRef.current?.stop()
    }
  }, [])

  async function submitCheckin(qrValue: string) {
    setLoading(true)
    setError('')
    try {
      const res = await patrolApi.checkin(qrValue)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '打點失敗')
    } finally {
      setLoading(false)
    }
  }

  async function startScan() {
    if (!videoRef.current) return
    setScanning(true)
    setError('')
    const reader = new BrowserMultiFormatReader()
    try {
      const controls = await reader.decodeFromVideoDevice(undefined, videoRef.current, (scanResult, scanError) => {
        if (scanResult) {
          const text = scanResult.getText()
          scannerControlsRef.current?.stop()
          setScanning(false)
          void submitCheckin(text)
          return
        }
        if (scanError) {
          // 持續掃描時會反覆丟出 not found，這裡忽略。
        }
      })
      scannerControlsRef.current = controls
    } catch (err) {
      setScanning(false)
      setError(err instanceof Error ? err.message : '無法啟用相機')
    }
  }

  function stopScan() {
    scannerControlsRef.current?.stop()
    setScanning(false)
  }

  function onManualSubmit(e: FormEvent) {
    e.preventDefault()
    if (!manualQr.trim()) return
    void submitCheckin(manualQr.trim())
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-2xl font-semibold">巡邏打點</h1>
        {deviceInfo && (
          <div className="rounded border border-slate-700 bg-slate-900/80 p-3 text-sm">
            <div>員工：{deviceInfo.employee_name}</div>
            <div>案場：{deviceInfo.site_name}</div>
            <div>綁定時間：{new Date(deviceInfo.bound_at).toLocaleString()}</div>
          </div>
        )}
        {error && <p className="text-sm text-rose-300">{error}</p>}
        <div className="rounded border border-slate-700 bg-slate-900/80 p-3 space-y-3">
          <video ref={videoRef} className="w-full rounded bg-black min-h-56" muted playsInline />
          <div className="flex gap-2">
            {!scanning ? (
              <button onClick={() => void startScan()} className="rounded bg-emerald-500 px-4 py-2 text-slate-950 font-semibold">
                掃描巡邏點 QR
              </button>
            ) : (
              <button onClick={stopScan} className="rounded bg-amber-400 px-4 py-2 text-slate-950 font-semibold">
                停止掃描
              </button>
            )}
          </div>
        </div>
        <form onSubmit={onManualSubmit} className="rounded border border-slate-700 bg-slate-900/80 p-3 space-y-2">
          <label className="block text-sm">手動貼上 QR 內容（備援）</label>
          <input
            value={manualQr}
            onChange={(e) => setManualQr(e.target.value)}
            className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="patrolpoint://checkin?point_id=..."
          />
          <button
            type="submit"
            disabled={loading || !manualQr.trim()}
            className="rounded bg-sky-500 px-4 py-2 text-slate-950 font-semibold disabled:opacity-60"
          >
            {loading ? '送出中...' : '送出打點'}
          </button>
        </form>
        {result && (
          <div className="rounded border border-emerald-500/50 bg-emerald-500/10 p-3 text-sm">
            <div className="font-semibold">打點成功</div>
            <div>{result.employee_name} / {result.site_name}</div>
            <div>{result.point_code} - {result.point_name}</div>
            <div>{result.checkin_date} {result.checkin_ampm} {result.checkin_time}</div>
          </div>
        )}
        <button
          onClick={() => {
            clearPatrolDeviceToken()
            window.location.href = '/patrol/bind'
          }}
          className="text-sm underline text-slate-300"
        >
          解除本機綁定（清除 device_token）
        </button>
      </div>
    </div>
  )
}
