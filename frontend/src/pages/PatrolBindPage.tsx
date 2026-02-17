import { FormEvent, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { patrolApi, setPatrolDeviceToken } from '../api'
import type { DeviceFingerprint } from '../types'

function detectBrowser(ua: string): string {
  const s = ua.toLowerCase()
  if (s.includes('edg/')) return 'Edge'
  if (s.includes('chrome/') && !s.includes('edg/')) return 'Chrome'
  if (s.includes('safari/') && !s.includes('chrome/')) return 'Safari'
  if (s.includes('firefox/')) return 'Firefox'
  if (s.includes('samsungbrowser/')) return 'Samsung Internet'
  return 'Unknown'
}

function buildFingerprint(): DeviceFingerprint {
  const userAgent = navigator.userAgent || ''
  return {
    userAgent,
    platform: navigator.platform || '',
    browser: detectBrowser(userAgent),
    language: navigator.language || '',
    screen: `${window.screen.width}x${window.screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    ip: null,
  }
}

export default function PatrolBindPage() {
  const [params] = useSearchParams()
  const code = params.get('code') || ''
  const [employeeName, setEmployeeName] = useState('')
  const [siteName, setSiteName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const fingerprint = useMemo(() => buildFingerprint(), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!code) {
      setError('缺少綁定碼，請重新掃描 QR')
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await patrolApi.bind({
        code,
        employee_name: employeeName.trim(),
        site_name: siteName.trim(),
        device_fingerprint: fingerprint,
      })
      setPatrolDeviceToken(res.device_token)
      navigate('/patrol', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '綁定失敗')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900/80 p-5">
        <h1 className="text-xl font-semibold mb-1">巡邏設備綁定</h1>
        <p className="text-sm text-slate-300 mb-4">請確認設備資訊並填寫員工與案場名稱。</p>

        <div className="grid grid-cols-1 gap-2 text-sm mb-4">
          <div><span className="text-slate-400">綁定碼：</span><span>{code || '（未帶入）'}</span></div>
          <div><span className="text-slate-400">User Agent：</span><span className="break-all">{fingerprint.userAgent}</span></div>
          <div><span className="text-slate-400">平台：</span><span>{fingerprint.platform || '-'}</span></div>
          <div><span className="text-slate-400">瀏覽器：</span><span>{fingerprint.browser}</span></div>
          <div><span className="text-slate-400">語言：</span><span>{fingerprint.language || '-'}</span></div>
          <div><span className="text-slate-400">螢幕：</span><span>{fingerprint.screen || '-'}</span></div>
          <div><span className="text-slate-400">時區：</span><span>{fingerprint.timezone || '-'}</span></div>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="block text-sm mb-1">員工姓名</label>
            <input
              value={employeeName}
              onChange={(e) => setEmployeeName(e.target.value)}
              required
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="請輸入員工姓名"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">巡邏案場名稱</label>
            <input
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              required
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="請輸入案場名稱"
            />
          </div>
          {error && <p className="text-sm text-rose-300">{error}</p>}
          <button
            type="submit"
            disabled={loading || !employeeName.trim() || !siteName.trim()}
            className="w-full rounded bg-emerald-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
          >
            {loading ? '綁定中...' : '完成綁定'}
          </button>
        </form>
      </div>
    </div>
  )
}
