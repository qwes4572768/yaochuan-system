import { Link } from 'react-router-dom'

export default function PatrolPermanentEntryGuidePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900/80 p-5 space-y-4">
        <h1 className="text-xl font-semibold">永久裝置入口</h1>
        <p className="text-sm text-slate-300">
          請掃描「永久裝置入口 QR」進入指定裝置頁。此入口固定有效，可重複掃碼。
        </p>
        <div className="rounded border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
          若你目前只有一次性綁定碼，請改走舊版綁定頁。
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/patrol-admin/bindings/legacy" className="rounded bg-sky-500 px-3 py-2 text-slate-950 font-semibold">
            回到綁定 QR 管理頁
          </Link>
          <Link to="/patrol/bind" className="rounded border border-slate-500 px-3 py-2">
            前往一次性綁定入口
          </Link>
        </div>
      </div>
    </div>
  )
}
