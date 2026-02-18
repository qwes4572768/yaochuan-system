import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { patrolApi } from '../api'

/**
 * 永久裝置入口：掃碼後先進入此頁，依 GET /api/patrol/device/:id 綁定狀態分流。
 * - 已綁定（is_bound 且 employee_name/site_name 有值）→ 導向 /patrol/bind/permanent/:id（登入表單，登入後進巡邏）
 * - 未綁定或 404 → 導向 /patrol/bind/permanent/:id（綁定表單）
 * 避免已綁定者掃碼再次走綁定流程、產生重複綁定紀錄。
 */
export default function PermanentEntryPage() {
  const { devicePublicId = '' } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'bound' | 'unbound' | 'error'>('loading')

  const bindPagePath = `/patrol/bind/permanent/${encodeURIComponent(devicePublicId)}`

  useEffect(() => {
    if (!devicePublicId.trim()) {
      setStatus('unbound')
      return
    }

    let cancelled = false
    patrolApi
      .getDeviceByPublicId(devicePublicId.trim())
      .then((res) => {
        if (cancelled) return
        const hasBound =
          res.is_bound &&
          (res.employee_name ?? '').trim() !== '' &&
          (res.site_name ?? '').trim() !== ''
        setStatus(hasBound ? 'bound' : 'unbound')
      })
      .catch(() => {
        if (cancelled) return
        setStatus('unbound')
      })

    return () => {
      cancelled = true
    }
  }, [devicePublicId])

  useEffect(() => {
    if (status === 'bound' || status === 'unbound') {
      navigate(bindPagePath, { replace: true })
    }
  }, [status, bindPagePath, navigate])

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="rounded-xl border border-rose-500/40 bg-slate-900/80 p-5 text-center">
          <p className="text-rose-200 mb-3">無法取得裝置狀態</p>
          <a
            href={bindPagePath}
            className="rounded bg-sky-500 px-3 py-2 text-slate-950 font-semibold text-sm"
          >
            前往綁定／登入頁
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-5">
        <p className="text-slate-200">載入中…</p>
      </div>
    </div>
  )
}
