import { useState } from 'react'
import { backupApi, type BackupHistoryItem } from '../api'
import { translateError } from '../utils/errorMsg'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function BackupRestore() {
  const [adminToken, setAdminToken] = useState('')
  const [backupLoading, setBackupLoading] = useState(false)
  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [restoreConfirm, setRestoreConfirm] = useState('')
  const [restoreLoading, setRestoreLoading] = useState(false)
  const [error, setError] = useState('')
  const [restoreResult, setRestoreResult] = useState<{ restored_employees: number; restored_dependents: number } | null>(null)
  const [historyList, setHistoryList] = useState<BackupHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null)

  const handleBackup = async () => {
    if (!adminToken.trim()) {
      setError('請輸入管理員憑證')
      return
    }
    setError('')
    setRestoreResult(null)
    setBackupLoading(true)
    try {
      await backupApi.exportExcel(adminToken.trim())
    } catch (e) {
      setError(translateError(e instanceof Error ? e.message : '備份失敗'))
    } finally {
      setBackupLoading(false)
    }
  }

  const loadHistory = async () => {
    if (!adminToken.trim()) {
      setError('請先輸入管理員憑證')
      return
    }
    setError('')
    setHistoryLoading(true)
    try {
      const list = await backupApi.history(adminToken.trim())
      setHistoryList(list)
    } catch (e) {
      setError(translateError(e instanceof Error ? e.message : '載入歷史備份失敗'))
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleDownloadHistory = async (filename: string) => {
    if (!adminToken.trim()) return
    setDownloadingFile(filename)
    setError('')
    try {
      await backupApi.downloadHistoryFile(adminToken.trim(), filename)
    } catch (e) {
      setError(translateError(e instanceof Error ? e.message : '下載失敗'))
    } finally {
      setDownloadingFile(null)
    }
  }

  const handleRestore = async () => {
    if (!adminToken.trim()) {
      setError('請輸入管理員憑證')
      return
    }
    if (!restoreFile) {
      setError('請選擇要還原的 Excel 檔案')
      return
    }
    if (restoreConfirm.trim().toLowerCase() !== 'yes') {
      setError('還原需二次確認，請在確認欄輸入 yes')
      return
    }
    setError('')
    setRestoreResult(null)
    setRestoreLoading(true)
    try {
      const result = await backupApi.restore(restoreFile, restoreConfirm.trim(), adminToken.trim())
      setRestoreResult(result)
      setRestoreFile(null)
      setRestoreConfirm('')
    } catch (e) {
      setError(translateError(e instanceof Error ? e.message : '還原失敗'))
    } finally {
      setRestoreLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">人事資料備份與還原</h2>
      <p className="text-slate-600">
        災難復原用：匯出完整人事資料為 Excel，或從先前匯出的檔案還原。僅管理員可使用，還原將覆蓋現有員工與眷屬資料。
      </p>

      <div className="card p-6 space-y-6">
        <section>
          <label className="block font-medium text-slate-700 mb-2">管理員憑證</label>
          <input
            type="password"
            className="input max-w-xs"
            placeholder="請輸入管理員憑證"
            value={adminToken}
            onChange={(e) => setAdminToken(e.target.value)}
            autoComplete="off"
          />
        </section>

        <section className="pt-4 border-t border-slate-200">
          <h3 className="font-semibold text-slate-700 mb-2">人事資料備份</h3>
          <p className="text-sm text-slate-500 mb-3">
            匯出所有員工與眷屬完整欄位為 Excel（檔名：hr_backup_YYYYMMDD_HHMMSS.xlsx），每個資料表一個 Sheet。
          </p>
          <button
            type="button"
            className="btn-primary"
            disabled={backupLoading}
            onClick={handleBackup}
          >
            {backupLoading ? '匯出中…' : '人事資料備份'}
          </button>
        </section>

        <section className="pt-4 border-t border-slate-200">
          <h3 className="font-semibold text-slate-700 mb-2">歷史備份（下載）</h3>
          <p className="text-sm text-slate-500 mb-3">
            系統每日自動備份至 server/backup/hr，僅保留最近 30 份。可在此下載歷史備份檔。
          </p>
          <button
            type="button"
            className="btn-secondary mb-3"
            disabled={historyLoading}
            onClick={loadHistory}
          >
            {historyLoading ? '載入中…' : '載入歷史備份列表'}
          </button>
          {historyList.length > 0 && (
            <div className="border border-slate-200 rounded overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="text-left p-2">檔名</th>
                    <th className="text-left p-2">建立時間</th>
                    <th className="text-right p-2">大小</th>
                    <th className="p-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {historyList.map((item) => (
                    <tr key={item.filename} className="border-t border-slate-200">
                      <td className="p-2 font-mono text-slate-700">{item.filename}</td>
                      <td className="p-2 text-slate-600">{new Date(item.created_at).toLocaleString('zh-TW')}</td>
                      <td className="p-2 text-right text-slate-600">{formatSize(item.size)}</td>
                      <td className="p-2">
                        <button
                          type="button"
                          className="btn-secondary text-sm"
                          disabled={downloadingFile === item.filename}
                          onClick={() => handleDownloadHistory(item.filename)}
                        >
                          {downloadingFile === item.filename ? '下載中…' : '下載'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="pt-4 border-t border-slate-200">
          <h3 className="font-semibold text-slate-700 mb-2">人事資料還原</h3>
          <p className="text-sm text-slate-500 mb-3">
            上傳本系統匯出的 Excel，將清空現有員工與眷屬後寫入檔案內容。請務必確認檔案來源正確，並輸入 yes 進行二次確認。
          </p>
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-sm text-slate-600 mb-1">選擇檔案（.xlsx）</label>
              <input
                type="file"
                accept=".xlsx"
                className="input"
                onChange={(e) => setRestoreFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <div>
              <label className="block text-sm text-slate-600 mb-1">輸入 yes 確認覆蓋</label>
              <input
                type="text"
                className="input w-32"
                placeholder="yes"
                value={restoreConfirm}
                onChange={(e) => setRestoreConfirm(e.target.value)}
              />
            </div>
            <button
              type="button"
              className="btn-secondary border-amber-600 text-amber-700 hover:bg-amber-50"
              disabled={restoreLoading || !restoreFile}
              onClick={handleRestore}
            >
              {restoreLoading ? '還原中…' : '人事資料還原'}
            </button>
          </div>
        </section>

        {error && <p className="text-red-600 text-sm">{error}</p>}
        {restoreResult && (
          <p className="text-green-700 text-sm">
            還原完成。員工 {restoreResult.restored_employees} 筆、眷屬 {restoreResult.restored_dependents} 筆。
          </p>
        )}
      </div>
    </div>
  )
}
