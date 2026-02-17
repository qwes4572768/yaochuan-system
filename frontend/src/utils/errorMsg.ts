/** 將常見英文錯誤訊息轉成中文（供畫面上顯示） */
export function translateError(msg: string): string {
  if (!msg || typeof msg !== 'string') return '發生錯誤'
  const m = msg.toLowerCase()
  if (
    m.includes('failed to fetch') ||
    m.includes('econnrefused') ||
    m.includes('network') ||
    m.includes('bad gateway') ||
    m.includes('502')
  ) {
    return '無法連線後端 (port 8000)，請先執行「啟動.bat」或 backend\\2_start_backend.bat 啟動後端。'
  }
  if (m.includes('internal server error') || m.includes('500')) {
    return '伺服器發生錯誤，請稍後再試。'
  }
  if (m.includes('not found') || m.includes('404')) return '找不到資源。'
  if (m.includes('forbidden') || m.includes('403')) return '沒有權限。'
  return msg
}
