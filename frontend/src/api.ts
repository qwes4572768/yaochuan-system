import { translateError } from './utils/errorMsg'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const BASE = `${API_BASE}/api`
const AUTH_TOKEN_KEY = 'access_token'
const PATROL_DEVICE_TOKEN_KEY = 'patrol_device_token'

export class ApiError extends Error {
  status?: number
  rawDetail?: string
  /** 429/409 重複掃碼時，剩餘需等待秒數 */
  cooldown_seconds?: number
  /** 429/409 重複掃碼時，上次掃碼時間 ISO */
  last_scan_at?: string

  constructor(message: string, status?: number, rawDetail?: string, extra?: { cooldown_seconds?: number; last_scan_at?: string }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.rawDetail = rawDetail
    if (extra) {
      this.cooldown_seconds = extra.cooldown_seconds
      this.last_scan_at = extra.last_scan_at
    }
  }
}

export function formatApiError(error: unknown, fallback = '操作失敗'): string {
  if (error instanceof ApiError) {
    const status = error.status ?? 'unknown'
    return `status=${status}：${error.message || fallback}`
  }
  if (error instanceof Error) {
    return error.message || fallback
  }
  return fallback
}

export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export function setAuthToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function getPatrolDeviceToken(): string | null {
  return localStorage.getItem(PATROL_DEVICE_TOKEN_KEY)
}

export function setPatrolDeviceToken(token: string): void {
  localStorage.setItem(PATROL_DEVICE_TOKEN_KEY, token)
}

export function clearPatrolDeviceToken(): void {
  localStorage.removeItem(PATROL_DEVICE_TOKEN_KEY)
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(BASE + path, {
      ...options,
      headers,
    })
  } catch (e) {
    throw new ApiError(translateError(e instanceof Error ? e.message : '無法連線伺服器'), 0)
  }
  if (res.status === 204) return undefined as T
  const text = await res.text()
  if (!res.ok) {
    let err: unknown = res.statusText
    let rawDetail = res.statusText
    if (text) {
      try {
        const parsed = JSON.parse(text).detail || text
        err = parsed
        rawDetail = Array.isArray(parsed) ? parsed.map((e: { msg?: string }) => e?.msg || String(e)).join(', ') : String(parsed)
      } catch {
        err = text
        rawDetail = text
      }
    }
    const msg = Array.isArray(err) ? err.map((e: { msg?: string }) => e?.msg || e).join(', ') : err
    throw new ApiError(translateError(String(msg)), res.status, rawDetail)
  }
  try {
    return (text ? JSON.parse(text) : undefined) as T
  } catch {
    throw new ApiError('回應格式錯誤', res.status)
  }
}

export interface LoginResponse {
  access_token: string
}

export interface MeResponse {
  username: string
  role: string
}

export const authApi = {
  login: async (username: string, password: string) => {
    let response: Response
    try {
      response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })
    } catch (e) {
      throw new Error(translateError(e instanceof Error ? e.message : '無法連線伺服器'))
    }
    if (!response.ok) {
      const text = await response.text()
      const err = text ? JSON.parse(text).detail || text : response.statusText
      throw new Error(translateError(String(err)))
    }
    const data = (await response.json()) as { access_token?: string }
    const token = data.access_token
    if (!token) {
      throw new Error('Login failed: no token returned')
    }
    localStorage.setItem('access_token', token)
    return { access_token: token }
  },
  me: () => request<MeResponse>('/auth/me'),
}

export const employeesApi = {
  list: (params?: { skip?: number; limit?: number; search?: string; registration_type?: 'security' | 'property' | 'smith' | 'lixiang' }) => {
    const q = new URLSearchParams()
    if (params?.skip != null) q.set('skip', String(params.skip))
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.search != null && params.search.trim()) q.set('search', params.search.trim())
    if (params?.registration_type) q.set('registration_type', params.registration_type)
    return request<import('./types').Employee[]>(`/employees?${q}`)
  },
  get: (id: number) => request<import('./types').Employee>(`/employees/${id}`),
  create: (data: import('./types').Employee) =>
    request<import('./types').Employee>('/employees', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<import('./types').Employee>) =>
    request<import('./types').Employee>(`/employees/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/employees/${id}`, { method: 'DELETE' }),
  listDependents: (employeeId: number) =>
    request<import('./types').Dependent[]>(`/employees/${employeeId}/dependents`),
  createDependent: (employeeId: number, data: Omit<import('./types').Dependent, 'id' | 'employee_id'>) =>
    request<import('./types').Dependent>(`/employees/${employeeId}/dependents`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateDependent: (employeeId: number, dependentId: number, data: Partial<import('./types').Dependent>) =>
    request<import('./types').Dependent>(`/employees/${employeeId}/dependents/${dependentId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteDependent: (employeeId: number, dependentId: number) =>
    request<void>(`/employees/${employeeId}/dependents/${dependentId}`, { method: 'DELETE' }),
}

export const insuranceApi = {
  brackets: () => request<import('./types').SalaryBracketItem[]>('/insurance/brackets'),
  salaryToLevel: (salary: number) =>
    request<{ salary: number; insured_salary_level: number }>(`/insurance/salary-to-level?salary=${salary}`),
  estimate: (body: {
    employee_id?: number
    insured_salary_level?: number
    dependent_count?: number
    year?: number
    month?: number
    pension_self_6?: boolean
  }) =>
    request<import('./types').InsuranceEstimate>('/insurance/estimate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  /** 上傳 Excel 試算檔，回傳以 Excel 為準的公司負擔、員工負擔、合計（不再用系統內建計算） */
  estimateFromExcel: async (
    employeeId: number,
    year: number,
    month: number,
    file: File
  ): Promise<import('./types').InsuranceEstimate> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(
      `${BASE}/insurance/estimate-from-excel?employee_id=${employeeId}&year=${year}&month=${month}`,
      { method: 'POST', body: form }
    )
    if (!res.ok) {
      const t = await res.text()
      const err = t ? JSON.parse(t).detail || t : res.statusText
      throw new Error(translateError(String(err)))
    }
    return res.json()
  },
}

export interface BracketImportLatest {
  has_import: boolean
  message?: string
  id?: number
  file_name?: string
  row_count?: number
  version?: string
  imported_at?: string
  file_path?: string
}

export const insuranceBracketsApi = {
  /** 上傳級距表 Excel，解析後存入 DB（權威資料） */
  importExcel: async (file: File, version?: string): Promise<{ id: number; file_name: string; row_count: number; version?: string; imported_at: string; message: string }> => {
    const form = new FormData()
    form.append('file', file)
    let url = `${BASE}/insurance-brackets/import`
    if (version?.trim()) url += `?version=${encodeURIComponent(version.trim())}`
    const res = await fetch(url, { method: 'POST', body: form })
    if (!res.ok) {
      const t = await res.text()
      const err = t ? JSON.parse(t).detail || t : res.statusText
      throw new Error(translateError(String(err)))
    }
    return res.json()
  },
  /** 取得最近一次匯入資訊 */
  getLatest: () => request<BracketImportLatest>('/insurance-brackets/latest'),
  /** 下載最近一次匯入的 Excel 原檔 */
  downloadLatestUrl: () => `${BASE}/insurance-brackets/latest/file`,
}

export const rateTablesApi = {
  list: (type?: string) => {
    const q = type ? `?type=${encodeURIComponent(type)}` : ''
    return request<import('./types').RateTableRead[]>(`/rate-tables${q}`)
  },
  effective: (year: number, month: number) =>
    request<Record<string, import('./types').RateTableRead | null>>(
      `/rate-tables/effective?year=${year}&month=${month}`
    ),
  importFile: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/rate-tables/import`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const t = await res.text()
      let msg = res.statusText
      if (t) {
        try {
          const err = JSON.parse(t)
          const d = err.detail
          msg = Array.isArray(d) ? d.map((x: { msg?: string }) => x?.msg || String(x)).join(' ') : (d || t)
        } catch {
          msg = t
        }
      }
      throw new Error(translateError(msg))
    }
    return res.json() as Promise<import('./types').RateTableRead[]>
  },
  importJson: (body: { tables: unknown[] }) =>
    request<import('./types').RateTableRead[]>('/rate-tables/import', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}

/** 案場管理：列表（含篩選）、取得/新增/更新/刪除、軟刪除（移除） */
export const sitesApi = {
  list: (params?: {
    page?: number
    page_size?: number
    q?: string
    site_type?: string
    service_type?: string
    status?: string
    include_inactive?: boolean
  }) => {
    const q = new URLSearchParams()
    if (params?.page != null) q.set('page', String(params.page))
    if (params?.page_size != null) q.set('page_size', String(params.page_size))
    if (params?.q?.trim()) q.set('q', params.q.trim())
    if (params?.site_type?.trim()) q.set('site_type', params.site_type.trim())
    if (params?.service_type?.trim()) q.set('service_type', params.service_type.trim())
    if (params?.status?.trim()) q.set('status', params.status.trim())
    if (params?.include_inactive) q.set('include_inactive', '1')
    const query = q.toString()
    return request<import('./types').SiteListResponse>(`/sites${query ? `?${query}` : ''}`)
  },
  history: (params?: { page?: number; page_size?: number; q?: string; status?: string }) => {
    const q = new URLSearchParams()
    if (params?.page != null) q.set('page', String(params.page))
    if (params?.page_size != null) q.set('page_size', String(params.page_size))
    if (params?.q?.trim()) q.set('q', params.q.trim())
    if (params?.status?.trim()) q.set('status', params.status.trim())
    const query = q.toString()
    return request<import('./types').SiteListResponse>(`/sites/history${query ? `?${query}` : ''}`)
  },
  get: (id: number) => request<import('./types').Site>(`/sites/${id}`),
  create: (data: import('./types').Site) =>
    request<import('./types').Site>('/sites', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<import('./types').Site>) =>
    request<import('./types').Site>(`/sites/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/sites/${id}`, { method: 'DELETE' }),
  /** 移除案場（軟刪除），需管理員 Token */
  deactivate: async (id: number, adminToken: string): Promise<import('./types').Site> => {
    const res = await fetch(`${BASE}/sites/${id}/deactivate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken },
    })
    const text = await res.text()
    if (!res.ok) {
      const msg = text ? (JSON.parse(text).detail || text) : res.statusText
      throw new Error(translateError(String(msg)))
    }
    return (text ? JSON.parse(text) : undefined) as import('./types').Site
  },
  listRebates: (siteId: number) =>
    request<import('./types').SiteRebate[]>(`/sites/${siteId}/rebates`),
  createRebate: (siteId: number, data: import('./types').SiteRebateCreate) =>
    request<import('./types').SiteRebate>(`/sites/${siteId}/rebates`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  listMonthlyReceipts: (siteId: number, year?: number) => {
    const q = year != null ? `?year=${year}` : ''
    return request<import('./types').SiteMonthlyReceipt[]>(`/sites/${siteId}/monthly-receipts${q}`)
  },
  createMonthlyReceipt: (
    siteId: number,
    data: import('./types').SiteMonthlyReceiptCreate | import('./types').SiteMonthlyReceiptBatchCreate
  ) =>
    request<import('./types').SiteMonthlyReceipt[]>(`/sites/${siteId}/monthly-receipts`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

/** 案場回饋：更新、刪除、上傳/下載回饋依據 PDF */
export const rebatesApi = {
  update: (rebateId: number, data: Partial<import('./types').SiteRebate>) =>
    request<import('./types').SiteRebate>(`/rebates/${rebateId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: (rebateId: number) => request<void>(`/rebates/${rebateId}`, { method: 'DELETE' }),
  uploadReceipt: async (rebateId: number, file: File): Promise<import('./types').SiteRebate> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/rebates/${rebateId}/receipt`, { method: 'POST', body: form })
    if (!res.ok) {
      const t = await res.text()
      const msg = t ? (JSON.parse(t).detail || t) : res.statusText
      throw new Error(translateError(String(msg)))
    }
    return res.json()
  },
  receiptUrl: (rebateId: number) => `${BASE}/rebates/${rebateId}/receipt`,
}

/** 案場每月入帳：更新、上傳/下載匯款證明 PDF */
export const monthlyReceiptsApi = {
  update: (receiptId: number, data: Partial<import('./types').SiteMonthlyReceipt>) =>
    request<import('./types').SiteMonthlyReceipt>(`/monthly-receipts/${receiptId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  uploadProof: async (receiptId: number, file: File): Promise<import('./types').SiteMonthlyReceipt> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/monthly-receipts/${receiptId}/proof`, { method: 'POST', body: form })
    if (!res.ok) {
      const t = await res.text()
      const msg = t ? (JSON.parse(t).detail || t) : res.statusText
      throw new Error(translateError(String(msg)))
    }
    return res.json()
  },
  proofUrl: (receiptId: number) => `${BASE}/monthly-receipts/${receiptId}/proof`,
}

export const documentsApi = {
  list: (employeeId: number) =>
    request<import('./types').DocumentInfo[]>(`/documents/employee/${employeeId}`),
  upload: async (employeeId: number, documentType: 'security_check' | '84_1', file: File) => {
    const form = new FormData()
    form.append('document_type', documentType)
    form.append('file', file)
    const res = await fetch(`${BASE}/documents/employee/${employeeId}/upload`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const t = await res.text()
      throw new Error(t ? JSON.parse(t).detail || t : res.statusText)
    }
    return res.json()
  },
  downloadUrl: (docId: number) => `${BASE}/documents/${docId}/download`,
}

/** 從 Content-Disposition 取出檔名；支援 filename= 與 filename*=UTF-8''%encoded */
function getFilenameFromDisposition(header: string | null): string | null {
  if (!header) return null
  const star = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (star) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      // 解碼失敗則用 filename=
    }
  }
  const m = header.match(/filename=["']?([^"';]+)["']?/i)
  return m ? m[1].trim() : null
}

/** 用 fetch 下載 Excel，失敗時拋出中文錯誤（避免存成 .json） */
export async function downloadReportExcel(urlPath: string, defaultFilename: string, headers?: Record<string, string>): Promise<void> {
  let res: Response
  try {
    res = await fetch(urlPath, { headers })
  } catch (e) {
    throw new Error(translateError(e instanceof Error ? e.message : '無法連線伺服器'))
  }
  if (!res.ok) {
    const t = await res.text()
    let msg = res.statusText
    if (t) {
      try {
        const err = JSON.parse(t)
        msg = err.detail || t
      } catch {
        msg = t
      }
    }
    throw new Error(translateError(String(msg)))
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition')
  const filename = getFilenameFromDisposition(disposition) || defaultFilename
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

export const reportsApi = {
  employeesExcel: () => `${BASE}/reports/export/employees`,
  dependentsExcel: () => `${BASE}/reports/export/dependents`,
  monthlyBurdenExcel: (year: number, month: number) =>
    `${BASE}/reports/export/monthly-burden?${new URLSearchParams({ year: String(year), month: String(month) })}`,
  personalBurdenExcel: (year: number, month: number) =>
    `${BASE}/reports/export/personal-burden?${new URLSearchParams({ year: String(year), month: String(month) })}`,
}

export type BackupHistoryItem = { filename: string; created_at: string; size: number }

/** 人事資料備份與還原（僅管理員，須帶 X-Admin-Token） */
export const backupApi = {
  exportUrl: () => `${BASE}/backup/export`,
  async exportExcel(adminToken: string): Promise<void> {
    await downloadReportExcel(
      `${BASE}/backup/export`,
      `hr_backup_${new Date().toISOString().slice(0, 10)}.xlsx`,
      { 'X-Admin-Token': adminToken }
    )
  },
  async history(adminToken: string): Promise<BackupHistoryItem[]> {
    const res = await fetch(`${BASE}/backup/history`, {
      headers: { 'X-Admin-Token': adminToken },
    })
    const text = await res.text()
    if (!res.ok) {
      let msg = res.statusText
      if (text) {
        try {
          const err = JSON.parse(text)
          msg = err.detail || text
        } catch {
          msg = text
        }
      }
      throw new Error(translateError(String(msg)))
    }
    return JSON.parse(text || '[]')
  },
  async downloadHistoryFile(adminToken: string, filename: string): Promise<void> {
    await downloadReportExcel(
      `${BASE}/backup/download/${encodeURIComponent(filename)}`,
      filename,
      { 'X-Admin-Token': adminToken }
    )
  },
  async restore(file: File, confirm: string, adminToken: string): Promise<{ restored_employees: number; restored_dependents: number }> {
    const form = new FormData()
    form.append('file', file)
    form.append('confirm', confirm)
    const res = await fetch(`${BASE}/backup/restore`, {
      method: 'POST',
      headers: { 'X-Admin-Token': adminToken },
      body: form,
    })
    const text = await res.text()
    if (!res.ok) {
      let msg = res.statusText
      if (text) {
        try {
          const err = JSON.parse(text)
          msg = err.detail || text
        } catch {
          msg = text
        }
      }
      throw new Error(translateError(String(msg)))
    }
    return JSON.parse(text || '{}')
  },
}

export const patrolApi = {
  createBindingCode: (expireMinutes = 10) =>
    request<import('./types').PatrolBindingCode>('/patrol/binding-codes', {
      method: 'POST',
      body: JSON.stringify({ expire_minutes: expireMinutes }),
    }),
  createPermanentQr: () =>
    request<import('./types').PatrolPermanentQr>('/patrol/device/permanent-qr', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  bind: (data: import('./types').PatrolBindRequest) =>
    request<import('./types').PatrolBindResponse>('/patrol/bind', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getDeviceByPublicId: (devicePublicId: string) =>
    request<import('./types').PatrolDeviceStatus>(`/patrol/device/${encodeURIComponent(devicePublicId)}`),
  getDeviceStatus: (devicePublicId: string) =>
    request<import('./types').PatrolDeviceStatus>(`/patrol/device/${encodeURIComponent(devicePublicId)}`),
  bindByDevicePublicId: (devicePublicId: string, data: import('./types').PatrolDeviceBindRequest) =>
    request<import('./types').PatrolBindResponse>(`/patrol/device/${encodeURIComponent(devicePublicId)}/bind`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  loginByDevicePublicId: (devicePublicId: string, data: import('./types').PatrolDeviceLoginRequest) =>
    request<import('./types').PatrolBoundLoginResponse>(`/patrol/device/${encodeURIComponent(devicePublicId)}/login`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  startByDevicePublicId: (devicePublicId: string, data: import('./types').PatrolDeviceStartRequest) =>
    request<import('./types').PatrolBoundLoginResponse>(`/patrol/device/${encodeURIComponent(devicePublicId)}/start`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  unbindByDevicePublicId: (devicePublicId: string, data: import('./types').PatrolDeviceUnbindRequest) =>
    request<import('./types').PatrolUnbindResponse>(`/patrol/device/${encodeURIComponent(devicePublicId)}/unbind`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updatePasswordByDevicePublicId: (devicePublicId: string, data: import('./types').PatrolDevicePasswordUpdateRequest) =>
    request<import('./types').PatrolDevicePasswordUpdateResponse>(`/patrol/device/${encodeURIComponent(devicePublicId)}/password`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  bindingStatus: (deviceFingerprint: import('./types').DeviceFingerprint) =>
    request<import('./types').PatrolBindingStatus>(
      `/patrol/binding-status?device_fingerprint=${encodeURIComponent(JSON.stringify(deviceFingerprint))}`
    ),
  boundLogin: (data: import('./types').PatrolBoundLoginRequest) =>
    request<import('./types').PatrolBoundLoginResponse>('/patrol/bound-login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  unbind: (data: import('./types').PatrolUnbindRequest) =>
    request<import('./types').PatrolUnbindResponse>('/patrol/unbind', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  meDevice: async () => {
    const token = getPatrolDeviceToken()
    const headers: Record<string, string> = {}
    if (token) headers['X-Device-Token'] = token
    const res = await fetch(`${BASE}/patrol/me/device`, { headers })
    const text = await res.text()
    if (!res.ok) {
      const err = text ? JSON.parse(text).detail || text : res.statusText
      throw new Error(translateError(String(err)))
    }
    return (text ? JSON.parse(text) : undefined) as import('./types').PatrolDeviceInfo
  },
  listPoints: () => request<import('./types').PatrolPoint[]>('/patrol/points'),
  createPoint: (data: { point_code: string; point_name: string; name?: string; site_name?: string | null; site_id?: number | null; location?: string | null; is_active?: boolean }) =>
    request<import('./types').PatrolPoint>('/patrol/points', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updatePoint: (id: number, data: { point_code?: string; point_name?: string; site_name?: string | null; site_id?: number | null; location?: string | null; is_active?: boolean }) =>
    request<import('./types').PatrolPoint>(`/patrol/points/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deletePoint: (id: number) => request<void>(`/patrol/points/${id}`, { method: 'DELETE' }),
  getPointQr: (publicId: string) => request<import('./types').PatrolPointQr>(`/patrol/points/${publicId}/qr`),
  checkinByPublicId: async (publicId: string, payload: { employee_id?: number; employee_name?: string; device_info?: string }) => {
    const res = await fetch(`${BASE}/patrol/checkin/${encodeURIComponent(publicId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const text = await res.text()
    if (!res.ok) {
      let data: Record<string, unknown> = {}
      try { if (text) data = JSON.parse(text) as Record<string, unknown> } catch { data = { detail: text } }
      const detail = typeof data.detail === 'string' ? data.detail : String(data.detail ?? (text || res.statusText))
      if ((res.status === 429 || res.status === 409) && detail) {
        throw new ApiError(translateError(detail), res.status, detail, {
          cooldown_seconds: typeof data.cooldown_seconds === 'number' ? data.cooldown_seconds : undefined,
          last_scan_at: typeof data.last_scan_at === 'string' ? data.last_scan_at : undefined,
        })
      }
      throw new Error(translateError(detail))
    }
    return (text ? JSON.parse(text) : undefined) as import('./types').PatrolCheckinResponse
  },
  checkin: async (qrValue: string) => {
    const token = getPatrolDeviceToken()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['X-Device-Token'] = token
    const res = await fetch(`${BASE}/patrol/checkin`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ qr_value: qrValue }),
    })
    const text = await res.text()
    if (!res.ok) {
      let data: Record<string, unknown> = {}
      try { if (text) data = JSON.parse(text) as Record<string, unknown> } catch { data = { detail: text } }
      const detail = typeof data.detail === 'string' ? data.detail : String(data.detail ?? (text || res.statusText))
      if ((res.status === 429 || res.status === 409) && detail) {
        throw new ApiError(translateError(detail), res.status, detail, {
          cooldown_seconds: typeof data.cooldown_seconds === 'number' ? data.cooldown_seconds : undefined,
          last_scan_at: typeof data.last_scan_at === 'string' ? data.last_scan_at : undefined,
        })
      }
      throw new Error(translateError(detail))
    }
    return (text ? JSON.parse(text) : undefined) as import('./types').PatrolCheckinResponse
  },
  listLogs: (params?: { date_from?: string; date_to?: string; employee_name?: string; site_name?: string; point_code?: string; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.date_from) q.set('date_from', params.date_from)
    if (params?.date_to) q.set('date_to', params.date_to)
    if (params?.employee_name?.trim()) q.set('employee_name', params.employee_name.trim())
    if (params?.site_name?.trim()) q.set('site_name', params.site_name.trim())
    if (params?.point_code?.trim()) q.set('point_code', params.point_code.trim())
    if (params?.limit != null) q.set('limit', String(params.limit))
    return request<import('./types').PatrolLog[]>(`/patrol/logs${q.toString() ? `?${q.toString()}` : ''}`)
  },
  exportLogsUrl: (params?: { date_from?: string; date_to?: string; employee_name?: string; site_name?: string; point_code?: string }) => {
    const q = new URLSearchParams()
    if (params?.date_from) q.set('date_from', params.date_from)
    if (params?.date_to) q.set('date_to', params.date_to)
    if (params?.employee_name?.trim()) q.set('employee_name', params.employee_name.trim())
    if (params?.site_name?.trim()) q.set('site_name', params.site_name.trim())
    if (params?.point_code?.trim()) q.set('point_code', params.point_code.trim())
    return `${BASE}/patrol/logs/export/excel${q.toString() ? `?${q.toString()}` : ''}`
  },
  listDeviceBindings: (params?: { query?: string; employee_name?: string; site_name?: string; status?: 'active' | 'inactive' | 'all'; limit?: number; offset?: number }) => {
    const q = new URLSearchParams()
    if (params?.query?.trim()) q.set('query', params.query.trim())
    if (params?.employee_name?.trim()) q.set('employee_name', params.employee_name.trim())
    if (params?.site_name?.trim()) q.set('site_name', params.site_name.trim())
    if (params?.status) q.set('status', params.status)
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    return request<import('./types').PatrolDeviceBindingAdminListResponse>(`/patrol/device-bindings${q.toString() ? `?${q.toString()}` : ''}`)
  },
  resetDeviceBindingPassword: (id: number, password: string) =>
    request<import('./types').PatrolDeviceBindingAdminItem>(`/patrol/device-bindings/${id}/password`, {
      method: 'PATCH',
      body: JSON.stringify({ password }),
    }),
  adminUnbindDeviceBinding: (id: number) =>
    request<import('./types').PatrolUnbindResponse>(`/patrol/device-bindings/${id}/unbind`, {
      method: 'POST',
    }),
}

/** 傻瓜會計 - 保全核心計算（升級版：應發/扣款/實發） */
export type PayrollType = 'security' | 'property' | 'smith' | 'cleaning'
export type EmployeeLookupType = 'security' | 'property' | 'smith' | 'lixiang'

export interface SecurityPayrollResult {
  site: string
  employee: string
  pay_type?: string
  total_hours: number
  gross_salary?: number
  labor_insurance_employee?: number
  health_insurance_employee?: number
  group_insurance?: number
  self_pension_6?: number
  deductions_total?: number
  net_salary?: number
  total_salary: number
  status: string
  year?: number
  month?: number
  type?: string
  source_payroll_type?: string
  salary_type?: string
  bank_code?: string
  branch_code?: string
  account_number?: string
  conflict?: boolean
  matched_candidates_count?: number
}

export interface SecurityPayrollCalcError {
  type?: string
  message: string
  employee_id?: number
  employee_name?: string
  current_payroll_type?: string
  source_payroll_type?: string
}

export interface SecurityPayrollResponse {
  results: SecurityPayrollResult[]
  errors: SecurityPayrollCalcError[]
  deleted_before_insert?: number
  inserted?: number
}

export interface SecurityPayrollHistorySummary {
  total_gross: number
  total_net: number
  total_deductions: number
  row_count: number
}

export interface SecurityPayrollHistoryStats {
  cash: number
  sec_first: number
  apt_first: number
  smith_first: number
  other_bank: number
  unset: number
}

export interface SecurityPayrollHistoryResponse {
  year: number
  month: number
  payroll_type: string
  results: SecurityPayrollResult[]
  summary: SecurityPayrollHistorySummary
  stats: SecurityPayrollHistoryStats
}

export interface SecurityPayrollHistoryMonthsResponse {
  payroll_type: string
  months: { year: number; month: number }[]
}

export interface SecurityPayrollMonthsResponse {
  months: string[]
}

export const accountingApi = {
  /** 上傳保全時數檔（xlsx/xls/ods），需帶 year, month, type；回傳計算結果與錯誤清單；計算成功後自動入庫 */
  async securityPayrollUpload(
    file: File,
    year: number,
    month: number,
    type: PayrollType,
    extraPayrollTypes: EmployeeLookupType[] = []
  ): Promise<SecurityPayrollResponse> {
    const form = new FormData()
    form.append('file', file)
    form.append('year', String(year))
    form.append('month', String(month))
    form.append('type', type)
    form.append('payroll_type', type)
    form.append('extra_payroll_types', JSON.stringify(extraPayrollTypes))
    const res = await fetch(`${BASE}/accounting/security-payroll/upload`, {
      method: 'POST',
      body: form,
    })
    const text = await res.text()
    if (!res.ok) {
      let err: unknown = res.statusText
      if (text) {
        try {
          const j = JSON.parse(text)
          const d = j.detail
          err = Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).filter(Boolean).join('；') || d : d
        } catch {
          err = text
        }
      }
      throw new Error(translateError(String(err)))
    }
    return JSON.parse(text || '{"results":[],"errors":[]}')
  },

  /** 依年/月查詢已存檔薪資結果 */
  history: (year: number, month: number, payrollType: PayrollType = 'security') =>
    request<SecurityPayrollHistoryResponse>(
      `/accounting/security-payroll/history?year=${year}&month=${month}&payroll_type=${payrollType}`
    ),

  /** 已存檔年月列表（供歷史查詢下拉選單） */
  historyMonths: (payrollType: PayrollType = 'security') =>
    request<SecurityPayrollHistoryMonthsResponse>(
      `/accounting/security-payroll/history-months?payroll_type=${payrollType}`
    ),

  /** 已存檔年月（新路由，直接回傳陣列） */
  months: (payrollType: PayrollType = 'security') =>
    request<SecurityPayrollMonthsResponse>(
      `/accounting/security-payroll/months?payroll_type=${payrollType}`
    ),

  /** 安全刪除指定年月歷史 */
  deleteHistory: (year: number, month: number, payrollType: PayrollType = 'security') =>
    request<{ deleted_count: number }>(
      `/accounting/security-payroll/history?year=${year}&month=${month}&payroll_type=${payrollType}`,
      { method: 'DELETE' }
    ),

  /** 匯出當次計算結果為 Excel（POST，傳入 results） */
  async exportCurrent(
    year: number,
    month: number,
    payrollType: PayrollType,
    results: SecurityPayrollResult[]
  ): Promise<void> {
    const res = await fetch(`${BASE}/accounting/security-payroll/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        year,
        month,
        payroll_type: payrollType,
        results,
      }),
    })
    if (!res.ok) {
      const t = await res.text()
      const err = t ? JSON.parse(t).detail || t : res.statusText
      throw new Error(translateError(String(err)))
    }
    const blob = await res.blob()
    const disposition = res.headers.get('Content-Disposition')
    const filename =
      getFilenameFromDisposition(disposition) ||
      `保全核薪_${year}_${String(month).padStart(2, '0')}.xlsx`
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
  },

  /** 匯出歷史月份 Excel 的 URL（供 GET 下載）；檔名由伺服器 Content-Disposition 提供，fallback 保全核薪_Y_M.xlsx */
  exportHistoryUrl: (year: number, month: number, payrollType: PayrollType = 'security') =>
    `${BASE}/accounting/security-payroll/export?year=${year}&month=${month}&payroll_type=${payrollType}`,
}
