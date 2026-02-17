import { useState, useEffect } from 'react'
import { insuranceBracketsApi, type BracketImportLatest } from '../api'
import { translateError } from '../utils/errorMsg'

export default function BracketImport() {
  const [latest, setLatest] = useState<BracketImportLatest | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [version, setVersion] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const loadLatest = async () => {
    setLoading(true)
    try {
      const data = await insuranceBracketsApi.getLatest()
      setLatest(data)
    } catch {
      setLatest(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLatest()
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setUploadError('')
    setUploading(true)
    try {
      await insuranceBracketsApi.importExcel(file, version || undefined)
      setFile(null)
      setVersion('')
      await loadLatest()
    } catch (e: unknown) {
      setUploadError(translateError(e instanceof Error ? e.message : '匯入失敗'))
    } finally {
      setUploading(false)
    }
  }

  const formatDatetime = (s?: string) => {
    if (!s) return '—'
    try {
      const d = new Date(s)
      return isNaN(d.getTime()) ? s : d.toLocaleString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    } catch {
      return s
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">級距表匯入（權威資料）</h2>
      <p className="text-slate-600">
        上傳勞健保級距 Excel（.xlsx）後，系統將以本表為「唯一依據」進行費用試算。表頭需含：級距、勞保公司/員工、健保公司/員工、職災、勞退6%、團保。匯入後可下載原檔備查。
      </p>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">上傳級距表</h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-sm text-slate-600 mb-1">選擇 .xlsx 檔案</label>
            <input
              type="file"
              accept=".xlsx"
              className="input"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">版本／備註（選填）</label>
            <input
              type="text"
              className="input w-48"
              placeholder="例：2025-02"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            />
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={!file || uploading}
            onClick={handleUpload}
          >
            {uploading ? '匯入中...' : '上傳並匯入'}
          </button>
        </div>
        {uploadError && <p className="mt-2 text-red-600 text-sm">{uploadError}</p>}
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-700 border-b pb-2 mb-4">最近一次匯入</h3>
        {loading ? (
          <p className="text-slate-500">載入中...</p>
        ) : latest?.has_import ? (
          <div className="space-y-2">
            <p><span className="text-slate-600">檔名：</span>{latest.file_name ?? '—'}</p>
            <p><span className="text-slate-600">匯入時間：</span>{formatDatetime(latest.imported_at)}</p>
            <p><span className="text-slate-600">筆數：</span>{latest.row_count ?? 0} 筆級距</p>
            {latest.version && <p><span className="text-slate-600">版本／備註：</span>{latest.version}</p>}
            <a
              href={insuranceBracketsApi.downloadLatestUrl()}
              target="_blank"
              rel="noreferrer"
              className="inline-block mt-2 text-indigo-600 hover:underline"
            >
              下載原檔備查
            </a>
          </div>
        ) : (
          <p className="text-slate-500">{latest?.message ?? '尚未匯入級距表，請先上傳 Excel。'}</p>
        )}
      </div>
    </div>
  )
}
