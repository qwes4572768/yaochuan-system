import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, formatApiError, patrolApi, setPatrolDeviceToken } from '../api'
import type { DeviceFingerprint, PatrolDeviceStatus } from '../types'

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

export default function PatrolBindPermanentPage() {
  const navigate = useNavigate()
  const { devicePublicId = '' } = useParams()
  const fingerprint = useMemo(() => buildFingerprint(), [])
  const [status, setStatus] = useState<PatrolDeviceStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [loadError, setLoadError] = useState<{ status: number | string; message: string } | null>(null)
  const [actionError, setActionError] = useState('')
  const [employeeName, setEmployeeName] = useState('')
  const [siteName, setSiteName] = useState('')
  const [password, setPassword] = useState('')
  const [loginEmployeeName, setLoginEmployeeName] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loggingIn, setLoggingIn] = useState(false)
  const [unbinding, setUnbinding] = useState(false)
  const [binding, setBinding] = useState(false)

  async function loadStatus() {
    if (!devicePublicId) return
    setLoading(true)
    setNotFound(false)
    setLoadError(null)
    setActionError('')
    try {
      const res = await patrolApi.getDeviceByPublicId(devicePublicId)
      setStatus(res)
      if (res.employee_name) setEmployeeName((prev) => prev || res.employee_name || '')
      if (res.site_name) setSiteName((prev) => prev || res.site_name || '')
      if (res.employee_name) setLoginEmployeeName((prev) => prev || res.employee_name || '')
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true)
        return
      }
      setNotFound(false)
      const status = err instanceof ApiError ? (err.status ?? 'unknown') : 'unknown'
      setLoadError({ status, message: formatApiError(err, '讀取裝置狀態失敗') })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadStatus()
  }, [devicePublicId])

  async function onLogin(e: FormEvent) {
    e.preventDefault()
    if (!devicePublicId) return
    setLoggingIn(true)
    setActionError('')
    try {
      const res = await patrolApi.loginByDevicePublicId(devicePublicId, {
        employee_name: loginEmployeeName.trim() || undefined,
        password: loginPassword.trim(),
        device_fingerprint: fingerprint,
      })
      setPatrolDeviceToken(res.device_token)
      navigate('/patrol', { replace: true })
    } catch (err) {
      setActionError(formatApiError(err, '登入失敗'))
    } finally {
      setLoggingIn(false)
    }
  }

  async function onBind(e: FormEvent) {
    e.preventDefault()
    if (!devicePublicId) return
    setBinding(true)
    setActionError('')
    try {
      const res = await patrolApi.bindByDevicePublicId(devicePublicId, {
        employee_name: employeeName.trim(),
        password: password.trim(),
        site_name: siteName.trim(),
        device_fingerprint: fingerprint,
      })
      setPatrolDeviceToken(res.device_token)
      navigate('/patrol', { replace: true })
    } catch (err) {
      setActionError(formatApiError(err, '綁定失敗'))
    } finally {
      setBinding(false)
    }
  }

  async function onUnbind() {
    if (!devicePublicId) return
    setUnbinding(true)
    setActionError('')
    try {
      await patrolApi.unbindByDevicePublicId(devicePublicId, {
        employee_name: loginEmployeeName.trim() || undefined,
        password: loginPassword.trim(),
        device_fingerprint: fingerprint,
      })
      setLoginPassword('')
      await loadStatus()
    } catch (err) {
      setActionError(formatApiError(err, '解除綁定失敗'))
    } finally {
      setUnbinding(false)
    }
  }

  const ua = status?.device_info?.ua || status?.ua || fingerprint.userAgent
  const platform = status?.device_info?.platform || status?.platform || fingerprint.platform
  const browser = status?.device_info?.browser || status?.browser || fingerprint.browser
  const language = status?.device_info?.lang || status?.language || fingerprint.language
  const screen = status?.device_info?.screen || status?.screen || fingerprint.screen
  const timezone = status?.device_info?.tz || status?.timezone || fingerprint.timezone

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900/80 p-5">
          <p className="text-sm text-slate-200">載入中…</p>
        </div>
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="w-full max-w-xl rounded-xl border border-amber-500/40 bg-slate-900/80 p-5 space-y-4">
          <h1 className="text-xl font-semibold">永久巡邏設備入口</h1>
          <p className="text-sm text-amber-200">未建立裝置資料，請先完成綁定。</p>
          <div className="flex flex-wrap gap-2">
            <Link to="/patrol-admin/bindings/legacy" className="rounded bg-sky-500 px-3 py-2 text-slate-950 font-semibold text-sm">
              回到綁定管理頁
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="w-full max-w-xl rounded-xl border border-rose-500/40 bg-slate-900/80 p-5 space-y-4">
          <h1 className="text-xl font-semibold">永久巡邏設備入口</h1>
          <p className="text-sm text-rose-200">載入失敗（status={loadError.status}）：{loadError.message}</p>
          <button
            onClick={() => void loadStatus()}
            className="rounded bg-amber-400 text-slate-950 font-semibold px-3 py-2 text-sm"
          >
            重試
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900/80 p-5 space-y-4">
        <h1 className="text-xl font-semibold">永久巡邏設備入口</h1>
        <p className="text-sm text-slate-300">此連結永久有效，可重複掃碼回到本頁。</p>
        <div className="grid grid-cols-1 gap-2 text-sm">
          <div><span className="text-slate-400">devicePublicId：</span><span className="break-all">{devicePublicId}</span></div>
          <div><span className="text-slate-400">綁定狀態：</span><span>{loading ? '查詢中...' : (status?.is_bound ? '已綁定' : '未綁定')}</span></div>
          <div><span className="text-slate-400">User Agent：</span><span className="break-all">{ua}</span></div>
          <div><span className="text-slate-400">平台：</span><span>{platform || '-'}</span></div>
          <div><span className="text-slate-400">瀏覽器：</span><span>{browser || '-'}</span></div>
          <div><span className="text-slate-400">語言：</span><span>{language || '-'}</span></div>
          <div><span className="text-slate-400">螢幕：</span><span>{screen || '-'}</span></div>
          <div><span className="text-slate-400">時區：</span><span>{timezone || '-'}</span></div>
          {status?.is_bound && (
            <>
              <div><span className="text-slate-400">員工：</span><span>{status.employee_name || '-'}</span></div>
              <div><span className="text-slate-400">案場：</span><span>{status.site_name || '-'}</span></div>
              <div><span className="text-slate-400">密碼：</span><span>{status.password_set ? '已設定' : '未設定'}</span></div>
            </>
          )}
        </div>

        {actionError && <p className="text-sm text-rose-300">{actionError}</p>}

        {status?.is_bound ? (
          <div className="space-y-3">
            <form onSubmit={onLogin} className="space-y-3">
              <div>
                <label className="block text-sm mb-1">員工姓名（可留空）</label>
                <input
                  value={loginEmployeeName}
                  onChange={(e) => setLoginEmployeeName(e.target.value)}
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  placeholder="可留空，留空時僅驗證密碼"
                />
              </div>
              <div>
                <label className="block text-sm mb-1">密碼</label>
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                />
              </div>
              <button
                type="submit"
                disabled={loggingIn || !loginPassword.trim()}
                className="w-full rounded bg-sky-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
              >
                {loggingIn ? '登入中...' : '已綁定開始巡邏'}
              </button>
            </form>

            <div>
              <button
                type="button"
                onClick={() => void onUnbind()}
                disabled={unbinding || !loginPassword.trim()}
                className="w-full rounded bg-rose-500 text-white font-semibold py-2 disabled:opacity-60"
              >
                {unbinding ? '解除中...' : '解除綁定（需密碼）'}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-amber-300">此永久裝置尚未綁定，請先完成綁定。</p>
            <form onSubmit={onBind} className="space-y-3">
              <div>
                <label className="block text-sm mb-1">員工姓名</label>
                <input
                  value={employeeName}
                  onChange={(e) => setEmployeeName(e.target.value)}
                  required
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm mb-1">案場名稱</label>
                <input
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  required
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm mb-1">密碼</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                />
              </div>
              <button
                type="submit"
                disabled={binding || !employeeName.trim() || !siteName.trim() || !password.trim()}
                className="w-full rounded bg-emerald-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
              >
                {binding ? '綁定中...' : '完成綁定'}
              </button>
            </form>
            <Link to="/patrol-admin/bindings/legacy" className="block text-sm underline text-slate-300">
              前往綁定管理頁（可產生一次性 QR）
            </Link>
          </div>
        )}
        <div className="pt-2">
          <Link to="/patrol-admin/bindings/legacy" className="text-sm underline text-slate-300">
            回到綁定管理頁
          </Link>
        </div>
      </div>
    </div>
  )
}
