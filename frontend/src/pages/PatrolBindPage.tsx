import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { patrolApi, setPatrolDeviceToken } from '../api'
import type { DeviceFingerprint, PatrolBindingStatus } from '../types'

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
  const devicePublicId = params.get('device_public_id') || ''
  const [employeeName, setEmployeeName] = useState('')
  const [siteName, setSiteName] = useState('')
  const [password, setPassword] = useState('')
  const [loginEmployeeName, setLoginEmployeeName] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [bindingStatus, setBindingStatus] = useState<PatrolBindingStatus | null>(null)
  const [checkingStatus, setCheckingStatus] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [unbindLoading, setUnbindLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const fingerprint = useMemo(() => buildFingerprint(), [])

  useEffect(() => {
    void (async () => {
      setCheckingStatus(true)
      try {
        const status = await patrolApi.bindingStatus(fingerprint)
        setBindingStatus(status)
        if (status.is_bound) {
          setLoginEmployeeName(status.employee_name || '')
          setEmployeeName((prev) => prev || status.employee_name || '')
          setSiteName((prev) => prev || status.site_name || '')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '查詢綁定狀態失敗')
      } finally {
        setCheckingStatus(false)
      }
    })()
  }, [fingerprint])

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
        device_public_id: devicePublicId || undefined,
        employee_name: employeeName.trim(),
        password: password.trim(),
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

  async function onBoundLogin(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoginLoading(true)
    try {
      const res = await patrolApi.boundLogin({
        employee_name: loginEmployeeName.trim(),
        password: loginPassword.trim(),
        device_fingerprint: fingerprint,
      })
      setPatrolDeviceToken(res.device_token)
      navigate('/patrol', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '登入失敗')
    } finally {
      setLoginLoading(false)
    }
  }

  async function onUnbind() {
    setError('')
    setUnbindLoading(true)
    try {
      const employee = loginEmployeeName.trim() || employeeName.trim()
      if (!employee) throw new Error('請先輸入員工姓名')
      const pwd = loginPassword.trim() || password.trim()
      if (!pwd) throw new Error('解除綁定需輸入密碼')
      await patrolApi.unbind({
        employee_name: employee,
        password: pwd,
        device_fingerprint: fingerprint,
      })
      setBindingStatus({ is_bound: false, password_set: false })
      setLoginPassword('')
      setPassword('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '解除綁定失敗')
    } finally {
      setUnbindLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900/80 p-5">
        <h1 className="text-xl font-semibold mb-1">巡邏設備綁定</h1>
        <p className="text-sm text-slate-300 mb-4">請確認設備資訊並完成綁定，或使用已綁定登入。</p>

        <div className="grid grid-cols-1 gap-2 text-sm mb-4">
          <div><span className="text-slate-400">綁定碼：</span><span>{code || '（未帶入）'}</span></div>
          <div><span className="text-slate-400">User Agent：</span><span className="break-all">{fingerprint.userAgent}</span></div>
          <div><span className="text-slate-400">平台：</span><span>{fingerprint.platform || '-'}</span></div>
          <div><span className="text-slate-400">瀏覽器：</span><span>{fingerprint.browser}</span></div>
          <div><span className="text-slate-400">語言：</span><span>{fingerprint.language || '-'}</span></div>
          <div><span className="text-slate-400">螢幕：</span><span>{fingerprint.screen || '-'}</span></div>
          <div><span className="text-slate-400">時區：</span><span>{fingerprint.timezone || '-'}</span></div>
          <div><span className="text-slate-400">綁定狀態：</span><span>{checkingStatus ? '查詢中...' : (bindingStatus?.is_bound ? '已綁定' : '未綁定')}</span></div>
          {bindingStatus?.is_bound && (
            <>
              <div><span className="text-slate-400">已綁定員工：</span><span>{bindingStatus.employee_name || '-'}</span></div>
              <div><span className="text-slate-400">已綁定案場：</span><span>{bindingStatus.site_name || '-'}</span></div>
              <div><span className="text-slate-400">密碼狀態：</span><span>{bindingStatus.password_set ? '已設定' : '未設定'}</span></div>
            </>
          )}
        </div>

        {!bindingStatus?.is_bound ? (
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
              <label className="block text-sm mb-1">密碼</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                placeholder="請設定綁定密碼"
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
              disabled={loading || !employeeName.trim() || !password.trim() || !siteName.trim()}
              className="w-full rounded bg-emerald-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
            >
              {loading ? '綁定中...' : '完成綁定'}
            </button>
          </form>
        ) : (
          <div className="space-y-3">
            <form onSubmit={onBoundLogin} className="space-y-3">
              <div>
                <label className="block text-sm mb-1">已綁定員工姓名</label>
                <input
                  value={loginEmployeeName}
                  onChange={(e) => setLoginEmployeeName(e.target.value)}
                  required
                  className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  placeholder="請輸入已綁定員工姓名"
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
                  placeholder="請輸入綁定密碼"
                />
              </div>
              {error && <p className="text-sm text-rose-300">{error}</p>}
              <button
                type="submit"
                disabled={loginLoading || !loginEmployeeName.trim() || !loginPassword.trim()}
                className="w-full rounded bg-sky-500 text-slate-950 font-semibold py-2 disabled:opacity-60"
              >
                {loginLoading ? '登入中...' : '已綁定開始巡邏'}
              </button>
            </form>
            <button
              type="button"
              onClick={() => void onUnbind()}
              disabled={unbindLoading || !loginPassword.trim()}
              className="w-full rounded bg-rose-500 text-white font-semibold py-2 disabled:opacity-60"
            >
              {unbindLoading ? '解除中...' : '解除綁定'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
